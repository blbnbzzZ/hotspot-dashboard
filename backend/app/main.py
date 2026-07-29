"""FastAPI 主应用 - 热点聚合工作台 API"""
import asyncio
from fastapi import FastAPI, Depends, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, List
import httpx

from app.database import get_db, init_db
from app.models import HotItem, AggregatedHot, BatchRecord, Setting, GenerationRecord
from app.crawlers.scheduler import start_scheduler, stop_scheduler, run_crawl_job
from app.crawlers import PLATFORM_NAMES
from app import ai_service

# 存储主事件循环引用（供同步接口创建后台任务用）
_main_loop = None

def _run_async(coro):
    """在 FastAPI 主事件循环中启动协程（从同步函数调用）"""
    if _main_loop and _main_loop.is_running():
        return _main_loop.create_task(coro)
    # 兜底：如果主循环不可用，用当前线程的循环
    try:
        loop = asyncio.get_running_loop()
        return loop.create_task(coro)
    except RuntimeError:
        # 没有运行中的循环，创建新事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.create_task(coro)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global _main_loop
    _main_loop = asyncio.get_running_loop()

    init_db()
    start_scheduler()
    # 启动时立即执行一次爬取
    try:
        await run_crawl_job()
    except Exception as e:
        print(f"[启动] 首次爬取异常: {e}")

    # 自动把超过 3 小时的批次加入排除列表
    _auto_exclude_old_batches()

    yield
    stop_scheduler()


def _auto_exclude_old_batches():
    """超过 3 小时的批次自动加入排除（用户仍可手动恢复）"""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        cutoff = datetime.now() - timedelta(hours=3)
        old_batches = db.query(BatchRecord).filter(
            BatchRecord.created_at < cutoff
        ).all()
        if not old_batches:
            return

        setting = db.query(Setting).filter_by(key="excluded_batch_ids").first()
        existing = set(setting.value.split(",")) if setting and setting.value else set()
        for b in old_batches:
            existing.add(b.batch_id)
        new_value = ",".join([x for x in existing if x])
        if setting:
            setting.value = new_value
        else:
            db.add(Setting(key="excluded_batch_ids", value=new_value))
        db.commit()
        print(f"[启动] 自动排除 {len(old_batches)} 个超过 3h 的批次")
    except Exception as e:
        print(f"[启动] 自动排除失败: {e}")
    finally:
        db.close()


app = FastAPI(
    title="热点聚合工作台",
    description="多平台热点聚合、权重计算、趋势分析",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========================
# 热点相关 API
# ========================

@app.get("/api/hotspots")
def get_hotspots(
    db: Session = Depends(get_db),
    batch_id: Optional[str] = None,
    category: Optional[str] = None,
    is_common: Optional[int] = None,
    platform: Optional[str] = None,
    keyword: Optional[str] = None,
    sort_by: str = "weight",
    page: int = 1,
    page_size: int = 30,
):
    """获取聚合热点列表（默认聚合最近 3h 内的所有批次，可排除）"""
    # 显式指定 batch_id 时直接用
    if not batch_id:
        # 默认取最近 3 小时内的所有批次
        cutoff_3h = datetime.now() - timedelta(hours=3)
        recent_batches = db.query(BatchRecord).filter(
            BatchRecord.status == "completed",
            BatchRecord.created_at >= cutoff_3h,
        ).order_by(desc(BatchRecord.created_at)).all()

        # 排除用户勾选不要的批次
        excluded_setting = db.query(Setting).filter_by(key="excluded_batch_ids").first()
        excluded_ids = set()
        if excluded_setting and excluded_setting.value:
            excluded_ids = set(excluded_setting.value.split(","))

        usable_batches = [b for b in recent_batches if b.batch_id not in excluded_ids]
        if not usable_batches:
            return {"items": [], "total": 0, "page": page, "page_size": page_size}

        batch_ids = [b.batch_id for b in usable_batches]
    else:
        batch_ids = [batch_id]

    query = db.query(AggregatedHot).filter(AggregatedHot.batch_id.in_(batch_ids))

    if category:
        query = query.filter(AggregatedHot.category == category)
    if is_common is not None:
        query = query.filter(AggregatedHot.is_common == is_common)
    if keyword:
        query = query.filter(AggregatedHot.display_title.contains(keyword))
    if platform:
        query = query.filter(AggregatedHot.platforms.contains(platform))

    total = query.count()

    # 综合排序（只保留 weight）
    query = query.order_by(desc(AggregatedHot.total_weight))

    raw_items = query.offset((page - 1) * page_size).limit(page_size * 3).all()  # 多取一些，后面要去重

    # 去重：同一 display_title 的热点只保留一条（取 weight 最高的）
    seen = {}
    for h in raw_items:
        key = h.display_title.strip()
        if key not in seen or h.total_weight > seen[key].total_weight:
            seen[key] = h

    items = sorted(seen.values(), key=lambda x: x.total_weight, reverse=True)[:page_size]
    total_unique = len(seen)

    return {
        "items": [_serialize_aggregated(h) for h in items],
        "total": total_unique,
        "page": page,
        "page_size": page_size,
        "batch_ids": batch_ids,
    }


@app.get("/api/hotspots/common")
def get_common_hotspots(
    db: Session = Depends(get_db),
    min_platforms: int = 2,
    batch_id: Optional[str] = None,
):
    """获取跨平台共同热点（默认聚合最近 3 批次，排除用户勾掉的）"""
    if batch_id:
        batch_ids = [batch_id]
    else:
        cutoff = datetime.now() - timedelta(hours=3)
        recent = db.query(BatchRecord).filter(
            BatchRecord.status == "completed",
            BatchRecord.created_at >= cutoff,
        ).order_by(desc(BatchRecord.created_at)).all()

        excluded = db.query(Setting).filter_by(key="excluded_batch_ids").first()
        excluded_set = set()
        if excluded and excluded.value:
            excluded_set = set(excluded.value.split(","))
        usable = [b for b in recent if b.batch_id not in excluded_set]
        if not usable:
            return {"items": [], "batch_ids": []}
        batch_ids = [b.batch_id for b in usable]

    raw_items = db.query(AggregatedHot).filter(
        AggregatedHot.batch_id.in_(batch_ids),
        AggregatedHot.is_common == 1,
        AggregatedHot.platform_count >= min_platforms,
    ).order_by(desc(AggregatedHot.total_weight)).all()

    # 去重：同一 display_title 只保留 weight 最高的
    seen = {}
    for h in raw_items:
        key = h.display_title.strip()
        if key not in seen or h.total_weight > seen[key].total_weight:
            seen[key] = h
    items = sorted(seen.values(), key=lambda x: x.total_weight, reverse=True)

    return {
        "items": [_serialize_aggregated(h) for h in items],
        "batch_ids": batch_ids,
    }


@app.get("/api/hotspots/{hot_id}")
def get_hotspot_detail(hot_id: int, db: Session = Depends(get_db)):
    """获取热点详情"""
    hot = db.query(AggregatedHot).filter(AggregatedHot.id == hot_id).first()
    if not hot:
        raise HTTPException(status_code=404, detail="热点不存在")

    # 获取相关原始数据
    batch_id = hot.batch_id
    keyword = hot.keyword
    raw_items = db.query(HotItem).filter(
        HotItem.batch_id == batch_id,
        HotItem.title.contains(keyword),
    ).all()

    return {
        ** _serialize_aggregated(hot),
        "raw_items": [_serialize_hot_item(r) for r in raw_items],
    }


# ========================
# 趋势分析 API
# ========================

@app.get("/api/trends")
def get_trends(
    db: Session = Depends(get_db),
    hours: int = Query(default=24, ge=6, le=168),
    keyword: Optional[str] = None,
):
    """获取热点趋势数据"""
    since = datetime.now() - timedelta(hours=hours)

    batches = db.query(BatchRecord).filter(
        BatchRecord.status == "completed",
        BatchRecord.created_at >= since,
    ).order_by(BatchRecord.created_at).all()

    trends = []
    for batch in batches:
        query = db.query(AggregatedHot).filter(
            AggregatedHot.batch_id == batch.batch_id,
        )
        if keyword:
            query = query.filter(AggregatedHot.display_title.contains(keyword))

        items = query.order_by(desc(AggregatedHot.total_weight)).limit(20).all()

        trends.append({
            "batch_id": batch.batch_id,
            "time": batch.created_at.isoformat(),
            "total_items": batch.aggregated_items,
            "common_items": batch.common_items,
            "top_items": [_serialize_aggregated(h) for h in items[:10]],
        })

    return {"trends": trends, "hours": hours}


@app.get("/api/trends/keyword/{keyword}")
def get_keyword_trend(keyword: str, hours: int = 24, db: Session = Depends(get_db)):
    """追踪特定关键词的热度变化"""
    since = datetime.now() - timedelta(hours=hours)

    items = db.query(AggregatedHot).filter(
        AggregatedHot.keyword.contains(keyword),
        AggregatedHot.created_at >= since,
    ).order_by(AggregatedHot.created_at).all()

    # 按时间分组合并
    trend_points = []
    for item in items:
        trend_points.append({
            "time": item.created_at.isoformat(),
            "weight": item.total_weight,
            "platform_count": item.platform_count,
            "display_title": item.display_title,
        })

    return {
        "keyword": keyword,
        "trend_points": trend_points,
    }


# ========================
# 数据统计 API
# ========================

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    """获取概览统计数据"""
    total_batches = db.query(BatchRecord).count()
    total_raw = db.query(HotItem).count()
    total_aggregated = db.query(AggregatedHot).count()

    # 最新批次统计
    latest = db.query(BatchRecord).filter(
        BatchRecord.status == "completed"
    ).order_by(desc(BatchRecord.created_at)).first()

    # 各平台最新数据量
    platform_stats = {}
    if latest:
        for plat in PLATFORM_NAMES:
            count = db.query(HotItem).filter(
                HotItem.batch_id == latest.batch_id,
                HotItem.platform == plat,
            ).count()
            platform_stats[plat] = count

    # 分类统计
    category_stats = {}
    if latest:
        cats = db.query(
            AggregatedHot.category,
            func.count(AggregatedHot.id).label("count")
        ).filter(
            AggregatedHot.batch_id == latest.batch_id,
        ).group_by(AggregatedHot.category).all()
        category_stats = {c.category: c.count for c in cats}

    return {
        "total_batches": total_batches,
        "total_raw_items": total_raw,
        "total_aggregated": total_aggregated,
        "latest_batch": _serialize_batch(latest) if latest else None,
        "platform_stats": platform_stats,
        "category_stats": category_stats,
    }


@app.get("/api/stats/batches")
def get_batch_list(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
):
    """获取批次历史列表"""
    total = db.query(BatchRecord).count()
    items = db.query(BatchRecord).order_by(
        desc(BatchRecord.created_at)
    ).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "items": [_serialize_batch(b) for b in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@app.get("/api/stats/platforms")
def get_platform_overview(db: Session = Depends(get_db)):
    """各平台数据概览"""
    stats = []
    for plat_key, plat_name in PLATFORM_NAMES.items():
        total = db.query(HotItem).filter(HotItem.platform == plat_key).count()
        latest_batch = db.query(BatchRecord).filter(
            BatchRecord.status == "completed"
        ).order_by(desc(BatchRecord.created_at)).first()

        latest_count = 0
        if latest_batch:
            latest_count = db.query(HotItem).filter(
                HotItem.platform == plat_key,
                HotItem.batch_id == latest_batch.batch_id,
            ).count()

        stats.append({
            "platform_key": plat_key,
            "platform_name": plat_name,
            "total_items": total,
            "latest_count": latest_count,
            "latest_batch_id": latest_batch.batch_id if latest_batch else None,
        })

    return {"platforms": stats}


# ========================
# 数据管理 API
# ========================

@app.post("/api/crawl/trigger")
async def trigger_crawl():
    """手动触发一次爬取"""
    try:
        await run_crawl_job()
        return {"status": "success", "message": "爬取任务已完成"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ========================
# AI 生成 API
# ========================

@app.get("/api/ai/status")
def ai_status():
    """获取 AI 配置状态"""
    return ai_service.get_status()


@app.post("/api/ai/generate")
async def ai_generate(request: dict):
    """AI 内容生成"""
    prompt = request.get("prompt", "").strip()
    system = request.get("system", "你是一个专业的内容创作助手。")
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt 不能为空")

    if not ai_service.get_configured_provider():
        raise HTTPException(
            status_code=400,
            detail="未配置 AI API Key，请在「数据管理」页面的 AI 设置中添加",
        )

    try:
        content = await ai_service.ai_generate(prompt, system)
        return {"status": "success", "content": content, "provider": ai_service.get_configured_provider()}
    except httpx.HTTPStatusError as e:
        return {"status": "error", "message": f"API 返回错误: {e.response.status_code} - 请检查 Key 是否正确"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/settings/ai/save")
def save_ai_key(request: dict):
    """保存 AI API Key 到本地数据库"""
    env_key = request.get("env_key", "").strip()
    value = request.get("value", "").strip()
    if not env_key or not value:
        raise HTTPException(status_code=400, detail="参数不完整")
    if env_key not in [cfg["env_key"] for cfg in ai_service.PROVIDER_CONFIG.values()]:
        raise HTTPException(status_code=400, detail="未知的 provider")
    try:
        ai_service.save_key(env_key, value)
        return {"status": "success", "message": "保存成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/settings/ai/delete")
def delete_ai_key(request: dict):
    """删除 AI API Key"""
    env_key = request.get("env_key", "").strip()
    if not env_key:
        raise HTTPException(status_code=400, detail="参数不完整")
    try:
        ai_service.delete_key(env_key)
        return {"status": "success", "message": "已删除"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/data/clear")
def clear_all_data(db: Session = Depends(get_db)):
    """清除所有数据"""
    try:
        db.query(HotItem).delete()
        db.query(AggregatedHot).delete()
        db.query(BatchRecord).delete()
        db.commit()
        return {"status": "success", "message": "所有数据已清除"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/data/batches/{batch_id}")
def delete_batch(batch_id: str, db: Session = Depends(get_db)):
    """删除指定批次的数据"""
    try:
        db.query(HotItem).filter(HotItem.batch_id == batch_id).delete()
        db.query(AggregatedHot).filter(AggregatedHot.batch_id == batch_id).delete()
        db.query(BatchRecord).filter(BatchRecord.batch_id == batch_id).delete()
        db.commit()
        return {"status": "success", "message": f"批次 {batch_id} 已删除"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/data/export")
def export_data(format: str = "json", db: Session = Depends(get_db)):
    """导出数据"""
    latest = db.query(BatchRecord).filter(
        BatchRecord.status == "completed"
    ).order_by(desc(BatchRecord.created_at)).first()

    if not latest:
        return {"items": []}

    items = db.query(AggregatedHot).filter(
        AggregatedHot.batch_id == latest.batch_id
    ).order_by(desc(AggregatedHot.total_weight)).all()

    return {
        "batch_id": latest.batch_id,
        "export_time": datetime.now().isoformat(),
        "items": [_serialize_aggregated(h) for h in items],
    }


# ========================
# 生成记录 API
# ========================

@app.get("/api/generations")
def list_generations(db: Session = Depends(get_db), page: int = 1, page_size: int = 50):
    """获取生成记录列表"""
    total = db.query(GenerationRecord).count()
    items = db.query(GenerationRecord).order_by(
        desc(GenerationRecord.created_at)
    ).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "items": [_serialize_generation(g) for g in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@app.get("/api/generations/{gen_id}")
def get_generation(gen_id: int, db: Session = Depends(get_db)):
    """获取单条生成记录"""
    g = db.query(GenerationRecord).filter(GenerationRecord.id == gen_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="记录不存在")
    return _serialize_generation(g)


@app.post("/api/generations/create")
async def create_generation(request: dict, db: Session = Depends(get_db)):
    """创建并启动后台生成任务，立即返回记录 ID"""
    prompt = request.get("prompt", "").strip()
    hotspot_title = request.get("hotspot_title", "")
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt 不能为空")

    if not ai_service.get_configured_provider():
        raise HTTPException(status_code=400, detail="未配置 AI API Key")

    # 创建记录
    record = GenerationRecord(
        prompt=prompt,
        content="",
        content_type="custom",
        provider=ai_service.get_configured_provider(),
        status="generating",
        hotspot_title=hotspot_title or None,
    )
    db.add(record)
    db.commit()
    gen_id = record.id

    # 后台运行生成（不 await，防火箭发送即返回）
    _run_async(_run_generation(gen_id, prompt))

    return {"id": gen_id, "status": "generating"}


async def _run_generation(gen_id: int, prompt: str):
    """后台真正的 AI 调用"""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        result = await ai_service.ai_generate(prompt)
        content = result["content"] if isinstance(result, dict) else result
        record = db.query(GenerationRecord).filter(GenerationRecord.id == gen_id).first()
        if record:
            record.content = content
            record.status = "completed"
            record.completed_at = datetime.now()
            db.commit()
    except Exception as e:
        record = db.query(GenerationRecord).filter(GenerationRecord.id == gen_id).first()
        if record:
            record.status = "failed"
            record.error_msg = str(e)
            record.completed_at = datetime.now()
            db.commit()
    finally:
        db.close()


@app.delete("/api/generations/{gen_id}")
def delete_generation(gen_id: int, db: Session = Depends(get_db)):
    """删除生成记录"""
    record = db.query(GenerationRecord).filter(GenerationRecord.id == gen_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.delete(record)
    db.commit()
    return {"status": "success"}


@app.post("/api/generations/{gen_id}/cancel")
def cancel_generation(gen_id: int, db: Session = Depends(get_db)):
    """取消进行中的生成（无法真正取消，只标记状态）"""
    record = db.query(GenerationRecord).filter(GenerationRecord.id == gen_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    if record.status == "generating":
        record.status = "failed"
        record.error_msg = "用户取消"
        record.completed_at = datetime.now()
        db.commit()
    return {"status": "success"}


# ========================
# 对话历史 API
# ========================

from app.models import Conversation, Message

@app.get("/api/conversations")
def list_conversations(db: Session = Depends(get_db), page: int = 1, page_size: int = 30):
    """对话列表"""
    total = db.query(Conversation).count()
    items = db.query(Conversation).order_by(
        desc(Conversation.updated_at)
    ).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "items": [_serialize_conv(c) for c in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@app.get("/api/conversations/{conv_id}")
def get_conversation(conv_id: int, db: Session = Depends(get_db)):
    """获取单个对话（含消息）"""
    c = db.query(Conversation).filter(Conversation.id == conv_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="对话不存在")
    messages = db.query(Message).filter(Message.conversation_id == conv_id).order_by(Message.created_at).all()
    return {
        **_serialize_conv(c),
        "messages": [_serialize_msg(m) for m in messages],
    }


@app.post("/api/conversations")
def create_conversation(request: dict, db: Session = Depends(get_db)):
    """创建新对话（带首条用户消息），后台生成首条助手回复"""
    prompt = request.get("prompt", "").strip()
    hotspot_title = request.get("hotspot_title", "")
    hotspot_id = request.get("hotspot_id")
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt 不能为空")

    conv = Conversation(
        title=prompt[:80],
        hotspot_title=hotspot_title or None,
        hotspot_id=hotspot_id,
        provider=ai_service.get_configured_provider(),
    )
    db.add(conv)
    db.commit()
    conv_id = conv.id

    # 保存用户消息
    user_msg = Message(conversation_id=conv_id, role="user", content=prompt)
    db.add(user_msg)

    # 创建助手消息占位
    ai_msg = Message(conversation_id=conv_id, role="assistant", content="", status="generating")
    db.add(ai_msg)
    db.commit()
    ai_msg_id = ai_msg.id
    conv.message_count = 2
    db.commit()

    # 后台异步生成助手回复
    _run_async(_run_chat_reply(conv_id, ai_msg_id, prompt))

    return {"id": conv_id, "ai_msg_id": ai_msg_id}


@app.post("/api/conversations/{conv_id}/message")
def add_message(conv_id: int, request: dict, db: Session = Depends(get_db)):
    """向对话追加消息（用户消息），后台调用 AI 生成助手回复"""
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")

    prompt = request.get("prompt", "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt 不能为空")

    # 保存用户消息
    user_msg = Message(conversation_id=conv_id, role="user", content=prompt, status="completed")
    db.add(user_msg)
    conv.message_count += 1
    db.commit()

    # 创建助手消息占位（生成中）
    ai_msg = Message(conversation_id=conv_id, role="assistant", content="", status="generating")
    db.add(ai_msg)
    db.commit()
    ai_msg_id = ai_msg.id

    # 后台异步生成助手回复
    _run_async(_run_chat_reply(conv_id, ai_msg_id, prompt))

    return {"user_msg_id": user_msg.id, "ai_msg_id": ai_msg_id}


async def _run_chat_reply(conv_id: int, ai_msg_id: int, last_user_prompt: str):
    """后台生成助手回复（含历史上下文）"""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        # 取全部历史
        msgs = db.query(Message).filter(Message.conversation_id == conv_id).order_by(Message.created_at).all()
        history = [{"role": m.role, "content": m.content} for m in msgs if m.content]

        result = await ai_service.ai_chat(history)
        content = result["content"]
        tokens = result["tokens"]

        ai_msg = db.query(Message).filter(Message.id == ai_msg_id).first()
        if ai_msg:
            ai_msg.content = content
            ai_msg.tokens = tokens
            ai_msg.status = "completed"

        conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
        if conv:
            conv.total_tokens = (conv.total_tokens or 0) + tokens
            conv.updated_at = datetime.now()

        db.commit()
    except Exception as e:
        ai_msg = db.query(Message).filter(Message.id == ai_msg_id).first()
        if ai_msg:
            ai_msg.status = "failed"
            ai_msg.content = f"[生成失败] {e}"
        db.commit()
    finally:
        db.close()


@app.get("/api/conversations/{conv_id}/status")
def get_conv_status(conv_id: int, db: Session = Depends(get_db)):
    """获取对话当前消息状态（用于轮询）"""
    msgs = db.query(Message).filter(
        Message.conversation_id == conv_id,
        Message.status == "generating"
    ).first()
    return {"generating": msgs is not None}


@app.delete("/api/conversations/{conv_id}")
def delete_conversation(conv_id: int, db: Session = Depends(get_db)):
    """删除对话"""
    db.query(Message).filter(Message.conversation_id == conv_id).delete()
    db.query(Conversation).filter(Conversation.id == conv_id).delete()
    db.commit()
    return {"status": "success"}


def _serialize_conv(c: Conversation) -> dict:
    return {
        "id": c.id,
        "title": c.title,
        "hotspot_title": c.hotspot_title,
        "hotspot_id": c.hotspot_id,
        "provider": c.provider,
        "total_tokens": c.total_tokens,
        "message_count": c.message_count,
        "status": c.status,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


def _serialize_msg(m: Message) -> dict:
    return {
        "id": m.id,
        "conversation_id": m.conversation_id,
        "role": m.role,
        "content": m.content,
        "tokens": m.tokens,
        "status": m.status,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


# ========================
# 系统 API
# ========================

@app.get("/api/health")
def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "time": datetime.now().isoformat(),
        "platforms": list(PLATFORM_NAMES.values()),
    }


@app.get("/api/system/logs")
def get_backend_logs(lines: int = 100):
    """获取最近 N 行后端日志"""
    log_file = Path(__file__).parent.parent / "data" / "backend.log"
    if not log_file.exists():
        return {"lines": [], "file": str(log_file), "size": 0}
    try:
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            all_lines = f.readlines()
        return {
            "lines": all_lines[-lines:],
            "file": str(log_file),
            "size": log_file.stat().st_size,
        }
    except Exception as e:
        return {"lines": [], "error": str(e)}


@app.delete("/api/system/logs")
def clear_backend_logs():
    """清空日志"""
    log_file = Path(__file__).parent.parent / "data" / "backend.log"
    try:
        if log_file.exists():
            log_file.write_text("", encoding="utf-8")
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ========================
# 网页内容提取 API
# ========================

@app.post("/api/content/fetch")
def fetch_page_content(request: dict):
    """抓取网页内容并提取正文（免费：纯提取）；
       如已配 AI Key 则额外生成 AI 摘要"""
    url = request.get("url", "").strip()
    if not url or not url.startswith("http"):
        raise HTTPException(status_code=400, detail="无效的 URL")

    try:
        # 抓取网页
        resp = httpx.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }, timeout=15, follow_redirects=True)

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")

        # 移除无用标签
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
            tag.decompose()

        # 提取标题
        title = ""
        if soup.title:
            title = soup.title.get_text(strip=True)

        # 提取正文 text（获取 body 中的所有文本，保留段落结构）
        body = soup.find("body")
        if body:
            # 提取段落文本
            paragraphs = []
            for p in body.find_all(["p", "h1", "h2", "h3", "h4", "li", "blockquote"]):
                text = p.get_text(strip=True)
                if len(text) > 15:  # 过滤过短的片段
                    paragraphs.append(text)
            text = "\n".join(paragraphs)
        else:
            text = soup.get_text("\n", strip=True)

        # 限制长度
        if len(text) > 8000:
            text = text[:8000] + "..."

        result = {
            "title": title,
            "text": text,
            "url": url,
            "summary": None,
        }

        # 如果有 AI Key，尝试生成摘要
        try:
            provider_key = ai_service.get_configured_provider()
            if provider_key and text:
                import asyncio
                summary_result = asyncio.run(ai_service.ai_chat([
                    {"role": "user", "content": f"请用 3-5 句话总结下面这篇文章的核心内容，不要加多余的话：\n\n{text[:4000]}"}
                ]))
                result["summary"] = summary_result["content"]
        except Exception:
            pass  # AI 摘要失败不影响纯文本提取

        return result

    except httpx.ConnectTimeout:
        raise HTTPException(status_code=504, detail="页面加载超时（可能无法访问）")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])


@app.post("/api/conversations/export")
def export_conversation(request: dict, db: Session = Depends(get_db)):
    """导出对话为文件（仅在首次生成时创建目录）"""
    content = request.get("content", "")
    filename = request.get("filename", f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
    custom_path = request.get("path", "").strip()

    # 决定保存路径
    from pathlib import Path
    if custom_path and os.path.isdir(custom_path):
        save_dir = custom_path
    else:
        # 默认：用户文档目录下的 hothistory（首次保存时自动创建）
        save_dir = str(Path.home() / "Documents" / "hothistory")

    # 自动创建目录（仅在不存在时）
    try:
        os.makedirs(save_dir, exist_ok=True)
    except Exception as e:
        return {"status": "error", "message": f"创建目录失败: {e}"}

    full_path = os.path.join(save_dir, filename)

    try:
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return {"status": "success", "full_path": full_path, "save_dir": save_dir}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/my/unseen")
def unseen_conversations(db: Session = Depends(get_db)):
    """获取用户上次访问我的页面之后的新对话更新数（用于红点）"""
    setting = db.query(Setting).filter_by(key="last_visit_my").first()
    last_visit = None
    if setting and setting.value:
        try:
            from datetime import datetime as dt
            last_visit = dt.fromisoformat(setting.value)
        except Exception:
            last_visit = None

    q = db.query(Conversation)
    if last_visit:
        q = q.filter(Conversation.updated_at > last_visit)
    count = q.count()

    latest = None
    if count > 0:
        latest_conv = q.order_by(Conversation.updated_at.desc()).first()
        if latest_conv:
            latest = {
                "id": latest_conv.id,
                "title": latest_conv.title,
                "hotspot_title": latest_conv.hotspot_title,
                "updated_at": latest_conv.updated_at.isoformat() if latest_conv.updated_at else None,
            }

    return {"unseen": count, "latest": latest}


@app.post("/api/my/seen")
def mark_conversations_seen(db: Session = Depends(get_db)):
    """标记我的页面已访问（清除红点）"""
    setting = db.query(Setting).filter_by(key="last_visit_my").first()
    if setting:
        setting.value = datetime.now().isoformat()
    else:
        setting = Setting(key="last_visit_my", value=datetime.now().isoformat())
        db.add(setting)
    db.commit()
    return {"status": "success"}


@app.post("/api/system/exit")
def exit_program():
    """退出程序 - 关闭所有相关进程（后端/前端/启动器/CMD窗口）"""
    import os, sys, subprocess
    print("[系统] 收到退出请求，正在关闭所有服务...")

    def kill_all():
        import time
        time.sleep(0.3)

        if sys.platform == "win32":
            # 1. 关闭通过 launcher 启动的 CMD 窗口（按标题）
            for title in ["Backend-8000", "Frontend-5173", "Hotspot Dashboard", "Hotspot Launcher"]:
                try:
                    subprocess.run(
                        f'taskkill /F /FI "WINDOWTITLE eq {title}*" /T',
                        shell=True, capture_output=True, timeout=5
                    )
                except Exception:
                    pass

            # 2. 关闭所有 node.exe（前端 dev server，可能多个）
            try:
                subprocess.run("taskkill /F /IM node.exe /T", shell=True, capture_output=True, timeout=5)
            except Exception:
                pass

            # 3. 关闭 launcher.py 进程（保留自己退出）
            try:
                subprocess.run(
                    'wmic process where "name=\'python.exe\' and commandline like \'%%launcher.py%%\'" delete',
                    shell=True, capture_output=True, timeout=5
                )
            except Exception:
                pass

        # 最后关闭自己
        time.sleep(0.2)
        os._exit(0)

    import threading
    threading.Thread(target=kill_all, daemon=True).start()
    return {"status": "exiting"}


@app.get("/api/settings/storage")
def get_storage_path(db: Session = Depends(get_db)):
    """获取文件保存路径设置"""
    setting = db.query(Setting).filter_by(key="storage_path").first()
    user_path = setting.value if setting and setting.value else ""
    return {
        "path": user_path,
        "default_path": str(Path.home() / "Documents" / "hothistory")
    }


@app.post("/api/settings/storage")
def set_storage_path(request: dict, db: Session = Depends(get_db)):
    """设置文件保存路径"""
    path = request.get("path", "").strip()
    setting = db.query(Setting).filter_by(key="storage_path").first()
    if setting:
        setting.value = path
    else:
        setting = Setting(key="storage_path", value=path)
        db.add(setting)
    db.commit()
    return {"status": "success", "path": path}


# ========================
# 批次选择 API
# ========================

@app.get("/api/batches/excluded")
def get_excluded_batches(db: Session = Depends(get_db)):
    """获取用户已排除的批次 ID 列表"""
    setting = db.query(Setting).filter_by(key="excluded_batch_ids").first()
    excluded = []
    if setting and setting.value:
        excluded = setting.value.split(",")
    return {"excluded": excluded}


@app.post("/api/batches/excluded")
def set_excluded_batches(request: dict, db: Session = Depends(get_db)):
    """批量设置排除的批次 ID 列表"""
    excluded = request.get("excluded", [])
    if not isinstance(excluded, list):
        raise HTTPException(status_code=400, detail="excluded 必须是数组")
    # 验证每个 batch_id 都存在
    valid_ids = []
    for bid in excluded:
        if not bid:
            continue
        batch = db.query(BatchRecord).filter_by(batch_id=bid).first()
        if batch:
            valid_ids.append(bid)

    setting = db.query(Setting).filter_by(key="excluded_batch_ids").first()
    new_value = ",".join(valid_ids)
    if setting:
        setting.value = new_value
    else:
        setting = Setting(key="excluded_batch_ids", value=new_value)
        db.add(setting)
    db.commit()
    return {"status": "success", "excluded": valid_ids}


@app.post("/api/batches/excluded/toggle")
def toggle_excluded_batch(request: dict, db: Session = Depends(get_db)):
    """切换某批次是否被排除"""
    batch_id = request.get("batch_id", "").strip()
    if not batch_id:
        raise HTTPException(status_code=400, detail="batch_id 不能为空")
    batch = db.query(BatchRecord).filter_by(batch_id=batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="批次不存在")

    setting = db.query(Setting).filter_by(key="excluded_batch_ids").first()
    excluded_list = setting.value.split(",") if setting and setting.value else []

    if batch_id in excluded_list:
        excluded_list.remove(batch_id)
        action = "included"
    else:
        excluded_list.append(batch_id)
        action = "excluded"

    new_value = ",".join([x for x in excluded_list if x])
    if setting:
        setting.value = new_value
    else:
        setting = Setting(key="excluded_batch_ids", value=new_value)
        db.add(setting)
    db.commit()
    return {"status": "success", "batch_id": batch_id, "action": action, "excluded": excluded_list}


@app.post("/api/settings/storage/pick")
def pick_storage_path():
    """弹出系统文件夹选择器，让用户可视化选择目录"""
    import threading
    result = {"path": ""}

    def _pick():
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            initial_path = Path.home() / "Documents"
            initial_str = str(initial_path) if initial_path.exists() else str(Path.home())
            path = filedialog.askdirectory(
                title="选择文件保存目录",
                initialdir=initial_str,
            )
            result["path"] = path or ""
            root.destroy()
        except Exception as e:
            result["error"] = str(e)

    t = threading.Thread(target=_pick, daemon=False)
    t.start()
    t.join(timeout=120)  # 最多等 2 分钟
    if result.get("error"):
        return {"status": "error", "message": result["error"]}
    return {"status": "success", "path": result["path"]}


# ========================
# 序列化辅助
# ========================

def _serialize_aggregated(h: AggregatedHot) -> dict:
    return {
        "id": h.id,
        "keyword": h.keyword,
        "display_title": h.display_title,
        "category": h.category,
        "platforms": h.platforms,
        "total_weight": h.total_weight,
        "platform_count": h.platform_count,
        "max_hot_score": h.max_hot_score,
        "is_common": h.is_common,
        "summary": h.summary,
        "batch_id": h.batch_id,
        "created_at": h.created_at.isoformat() if h.created_at else None,
    }


def _serialize_hot_item(h: HotItem) -> dict:
    return {
        "id": h.id,
        "platform": h.platform,
        "title": h.title,
        "url": h.url,
        "rank": h.rank,
        "hot_score": h.hot_score,
        "extra_data": h.extra_data,
        "created_at": h.created_at.isoformat() if h.created_at else None,
    }


def _serialize_batch(b: BatchRecord) -> dict:
    return {
        "id": b.id,
        "batch_id": b.batch_id,
        "status": b.status,
        "platforms_success": b.platforms_success,
        "platforms_failed": b.platforms_failed,
        "total_items": b.total_items,
        "aggregated_items": b.aggregated_items,
        "common_items": b.common_items,
        "started_at": b.started_at.isoformat() if b.started_at else None,
        "completed_at": b.completed_at.isoformat() if b.completed_at else None,
        "created_at": b.created_at.isoformat() if b.created_at else None,
    }


def _serialize_generation(g: GenerationRecord) -> dict:
    return {
        "id": g.id,
        "prompt": g.prompt,
        "content": g.content,
        "content_type": g.content_type,
        "provider": g.provider,
        "status": g.status,
        "error_msg": g.error_msg,
        "hotspot_title": g.hotspot_title,
        "created_at": g.created_at.isoformat() if g.created_at else None,
        "completed_at": g.completed_at.isoformat() if g.completed_at else None,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
