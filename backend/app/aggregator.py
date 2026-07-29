"""热点聚合引擎 - 跨平台匹配、去重、权重计算"""
import re
import jieba
from typing import List, Dict, Any, Set, Tuple
from collections import defaultdict


# 分类关键词映射
CATEGORY_KEYWORDS = {
    "科技": ["AI", "人工智能", "芯片", "手机", "苹果", "华为", "小米", "特斯拉", "大模型",
             "GPT", "机器人", "自动驾驶", "新能源", "5G", "6G", "卫星", "航天"],
    "娱乐": ["电影", "电视剧", "综艺", "演唱会", "明星", "艺人", "粉丝", "票房",
             "上映", "播出", "MV", "新歌", "专辑", "直播"],
    "社会": ["政策", "通报", "通报批评", "官方", "回应", "事故", "地震", "台风",
             "暴雨", "救援", "法律", "法院", "警方"],
    "财经": ["股市", "A股", "美股", "基金", "比特币", "房价", "利率", "央行",
             "IPO", "上市", "融资", "收购", "财报", "经济"],
    "体育": ["足球", "篮球", "世界杯", "奥运会", "NBA", "CBA", "欧冠", "英超",
             "游泳", "田径", "金牌", "冠军", "比赛"],
    "教育": ["高考", "考研", "留学", "大学", "学校", "录取", "专业", "考试"],
    "国际": ["美国", "日本", "韩国", "俄罗斯", "乌克兰", "欧盟", "联合国", "制裁", "外交"],
}


class HotAggregator:
    """热点聚合器"""

    def aggregate(self, all_items: Dict[str, List[Dict]], batch_id: str) -> List[Dict]:
        """
        聚合多个平台的热点数据
        :param all_items: {"weibo": [...], "zhihu": [...], ...}
        :param batch_id: 批次ID
        :return: 聚合后的热点列表
        """
        # 第一步：提取所有热点的关键词
        item_keywords = []
        for platform, items in all_items.items():
            for item in items:
                keywords = self._extract_keywords(item["title"])
                item_keywords.append({
                    "platform": platform,
                    "title": item["title"],
                    "url": item.get("url", ""),
                    "rank": item["rank"],
                    "hot_score": item.get("hot_score", 0),
                    "extra_data": item.get("extra_data", {}),
                    "keywords": keywords,
                })

        # 第二步：基于关键词相似度进行聚类
        clusters = self._cluster_by_similarity(item_keywords)

        # 第三步：为每个聚类计算综合权重
        aggregated = []
        for cluster_id, cluster_items in enumerate(clusters):
            result = self._build_aggregated_item(cluster_items, cluster_id, batch_id)
            aggregated.append(result)

        # 第四步：按权重降序排列
        aggregated.sort(key=lambda x: x["total_weight"], reverse=True)

        return aggregated

    def _extract_keywords(self, title: str) -> Set[str]:
        """提取标题中的关键词"""
        # 清洗文本
        title = re.sub(r'[#【】\[\]「」\s]', '', title)

        # jieba 分词
        words = jieba.cut(title)
        keywords = set()

        for word in words:
            word = word.strip()
            # 过滤单字和纯数字/符号
            if len(word) >= 2 and not word.isdigit() and not re.match(r'^[^\w]+$', word):
                keywords.add(word)

        # 保留原始标题中的重要片段
        if len(title) <= 10 and title not in keywords:
            keywords.add(title)

        return keywords

    def _cluster_by_similarity(self, items: List[Dict]) -> List[List[Dict]]:
        """
        基于关键词Jaccard相似度进行聚类
        相似度阈值: >= 0.3 认为是同一热点
        """
        n = len(items)
        parent = list(range(n))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py

        # 计算每对之间的相似度
        for i in range(n):
            for j in range(i + 1, n):
                sim = self._jaccard_similarity(items[i]["keywords"], items[j]["keywords"])
                # 如果标题包含关系也合并
                title_i = items[i]["title"]
                title_j = items[j]["title"]
                if title_i in title_j or title_j in title_i:
                    sim = max(sim, 0.5)
                if sim >= 0.3:
                    union(i, j)

        # 分组
        clusters = defaultdict(list)
        for i in range(n):
            clusters[find(i)].append(items[i])

        return list(clusters.values())

    @staticmethod
    def _jaccard_similarity(set_a: Set, set_b: Set) -> float:
        """Jaccard相似度"""
        if not set_a or not set_b:
            return 0.0
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        return intersection / union if union > 0 else 0.0

    def _build_aggregated_item(self, cluster_items: List[Dict], cluster_id: int,
                                batch_id: str) -> Dict:
        """构建聚合热点项"""
        n_platforms = len(cluster_items)
        platforms_set = set(item["platform"] for item in cluster_items)

        # 平台详情
        platform_details = {}
        for item in cluster_items:
            plat = item["platform"]
            if plat not in platform_details:
                platform_details[plat] = {
                    "rank": item["rank"],
                    "hot_score": item.get("hot_score", 0),
                    "title": item["title"],
                    "url": item["url"],
                }
            else:
                # 保留排名更靠前的
                if item["rank"] < platform_details[plat]["rank"]:
                    platform_details[plat] = {
                        "rank": item["rank"],
                        "hot_score": item.get("hot_score", 0),
                        "title": item["title"],
                        "url": item["url"],
                    }

        # 选展示标题（取最短且有代表性的）
        titles = [item["title"] for item in cluster_items]
        display_title = min(titles, key=len)

        # ===== 权重计算模型 =====
        platform_weights = {
            "weibo": 1.2,   # 微博热搜权重最高（实时性强）
            "thepaper": 1.0,   # 澎湃新闻
            "baidu": 0.9,   # 百度热搜
            "bilibili": 0.8, # B站热门
        }

        # 因子1: 覆盖平台数权重 (20-50分)
        platform_factor = min(n_platforms * 15, 50)

        # 因子2: 排名分 (各平台排名越靠前分越高)
        rank_scores = []
        for item in cluster_items:
            rank = item["rank"]
            plat = item["platform"]
            # 排名1=100分, 排名50=2分
            rank_score = max(100 - rank * 2, 1)
            rank_scores.append(rank_score * platform_weights.get(plat, 1.0))
        rank_factor = sum(rank_scores) / len(rank_scores) if rank_scores else 0

        # 因子3: 跨平台共识加成
        common_bonus = 0
        if len(platforms_set) >= 3:
            common_bonus = 30  # 三平台共识
        elif len(platforms_set) >= 2:
            common_bonus = 15  # 两平台共识

        # 因子4: 平台原始热度归一化
        max_raw = max((item.get("hot_score", 0) for item in cluster_items), default=0)
        hot_factor = min(max_raw / 10000, 20) if max_raw > 0 else 5

        # 综合权重 (0-100分)
        total_weight = round(platform_factor * 0.4 + rank_factor * 0.4 + common_bonus + hot_factor, 1)
        total_weight = min(total_weight, 100)

        # 分类识别
        category = self._classify(display_title)

        # 生成摘要
        summary = self._generate_summary(cluster_items, platforms_set)

        return {
            "keyword": self._find_core_keyword(cluster_items),
            "display_title": display_title,
            "category": category,
            "platforms": platform_details,
            "total_weight": total_weight,
            "platform_count": n_platforms,
            "max_hot_score": max_raw,
            "is_common": 1 if len(platforms_set) >= 2 else 0,
            "summary": summary,
            "batch_id": batch_id,
        }

    def _classify(self, title: str) -> str:
        """基于标题关键词分类"""
        title_lower = title.lower()
        for cat, keywords in CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in title_lower:
                    return cat
        return "综合"

    @staticmethod
    def _find_core_keyword(items: List[Dict]) -> str:
        """找出核心关键词"""
        word_count = defaultdict(int)
        for item in items:
            for word in item["keywords"]:
                word_count[word] += 1
        if word_count:
            return max(word_count, key=word_count.get)
        return items[0]["title"][:10]

    @staticmethod
    def _generate_summary(items: List[Dict], platforms: Set[str]) -> str:
        """生成热点摘要"""
        n = len(items)
        plat_names = {"weibo": "微博", "thepaper": "澎湃", "baidu": "百度", "bilibili": "B站"}
        plat_list = "、".join(plat_names.get(p, p) for p in platforms)

        if n <= 1:
            return f"仅在{plat_list}上出现"
        return f"在{plat_list}共{n}个平台出现，为{'跨平台共同热点' if len(platforms) >= 2 else '单平台热点'}"
