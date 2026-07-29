"""爬虫模块 - 统一接口"""
from .weibo import WeiboCrawler
from .thepaper import ThePaperCrawler
from .baidu import BaiduCrawler
from .bilibili import BilibiliCrawler

# 所有爬虫注册表（只保留国内 4 个稳定源）
CRAWLERS = {
    "weibo": WeiboCrawler(),
    "thepaper": ThePaperCrawler(),
    "baidu": BaiduCrawler(),
    "bilibili": BilibiliCrawler(),
}

PLATFORM_NAMES = {
    "weibo": "微博",
    "thepaper": "澎湃",
    "baidu": "百度",
    "bilibili": "B站",
}
