"""定时调度器 - 每6小时自动爬取"""
import uuid
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.crawlers import CRAWLERS, PLATFORM_NAMES
from app.aggregator import HotAggregator
from app.database import SessionLocal, init_db
from app.models import HotItem, AggregatedHot, BatchRecord


scheduler = AsyncIOScheduler()
aggregator = HotAggregator()


async def run_crawl_job():
    """执行一次完整的爬取+聚合任务"""
    batch_id = uuid.uuid4().hex[:12]
    started_at = datetime.now()

    print(f"\n{'='*50}")
    print(f"[调度器] 开始爬取批次: {batch_id}")
    print(f"[调度器] 时间: {started_at.strftime('%Y-%m-%d %H:%M:%S')}")

    # 创建批次记录
    db = SessionLocal()
    try:
        batch = BatchRecord(
            batch_id=batch_id,
            status="running",
            platforms_success=[],
            platforms_failed=[],
            started_at=started_at,
        )
        db.add(batch)
        db.commit()
    except Exception as e:
        print(f"[调度器] 创建批次记录失败: {e}")
        db.rollback()
    finally:
        db.close()

    # 爬取所有平台
    all_items = {}
    success_platforms = []
    failed_platforms = []

    for plat_key, crawler in CRAWLERS.items():
        print(f"[调度器] 正在爬取: {PLATFORM_NAMES[plat_key]}...")
        try:
            items = await crawler.fetch()
            all_items[plat_key] = items
            success_platforms.append(plat_key)
            print(f"[调度器] {PLATFORM_NAMES[plat_key]}: 获取 {len(items)} 条")
        except Exception as e:
            failed_platforms.append(plat_key)
            print(f"[调度器] {PLATFORM_NAMES[plat_key]}: 失败 - {e}")

    # 保存原始数据
    db = SessionLocal()
    try:
        total_raw = 0
        for plat_key, items in all_items.items():
            for item in items:
                hot = HotItem(
                    platform=plat_key,
                    title=item["title"],
                    url=item.get("url", ""),
                    rank=item["rank"],
                    hot_score=item.get("hot_score"),
                    extra_data=item.get("extra_data", {}),
                    batch_id=batch_id,
                )
                db.add(hot)
                total_raw += 1

        # 聚合
        print(f"[调度器] 开始聚合 {total_raw} 条原始数据...")
        aggregated = aggregator.aggregate(all_items, batch_id)
        common_count = sum(1 for a in aggregated if a["is_common"])

        for agg in aggregated:
            agg_hot = AggregatedHot(
                keyword=agg["keyword"],
                display_title=agg["display_title"],
                category=agg["category"],
                platforms=agg["platforms"],
                total_weight=agg["total_weight"],
                platform_count=agg["platform_count"],
                max_hot_score=agg["max_hot_score"],
                is_common=agg["is_common"],
                summary=agg["summary"],
                batch_id=batch_id,
            )
            db.add(agg_hot)

        # 更新批次记录
        batch = db.query(BatchRecord).filter_by(batch_id=batch_id).first()
        if batch:
            batch.status = "completed"
            batch.platforms_success = success_platforms
            batch.platforms_failed = failed_platforms
            batch.total_items = total_raw
            batch.aggregated_items = len(aggregated)
            batch.common_items = common_count
            batch.completed_at = datetime.now()

        db.commit()

        print(f"[调度器] 批次完成: 原始{total_raw}条, 聚合{len(aggregated)}条, 共同热点{common_count}个")

    except Exception as e:
        print(f"[调度器] 保存数据失败: {e}")
        db.rollback()
    finally:
        db.close()


def start_scheduler():
    """启动定时调度器"""
    init_db()

    # 每30分钟执行一次（用户嫌6小时太久，缩短）
    scheduler.add_job(
        run_crawl_job,
        trigger="interval",
        minutes=30,
        id="crawl_hotspots",
        name="爬取热点数据",
        replace_existing=True,
    )

    scheduler.start()
    print("[调度器] 已启动，每30分钟爬取一次")
    print("[调度器] 平台: 微博、澎湃、百度、B站")


def stop_scheduler():
    """停止调度器"""
    if scheduler.running:
        scheduler.shutdown(wait=False)
