"""澎湃新闻爬虫 - 解析新闻头条"""
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Any
import re


class ThePaperCrawler:
    name = "thepaper"
    display_name = "澎湃"
    base_url = "https://m.thepaper.cn/"

    async def fetch(self) -> List[Dict[str, Any]]:
        """获取澎湃新闻头条热点"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            try:
                resp = await client.get(self.base_url, headers=headers)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "lxml")

                items = []
                seen = set()

                # 从各种标题标签中提取新闻标题
                headlines = []
                for tag in soup.find_all(["h1", "h2", "h3", "h4"]):
                    text = tag.get_text(strip=True)
                    # 过滤短文本和无意义的标题
                    if text and len(text) >= 6 and text not in seen:
                        seen.add(text)
                        headlines.append(text)

                # 也搜索 class 包含 title/news/headline 的元素
                for el in soup.select("[class*='title' i], [class*='headline' i], [class*='news' i], a"):
                    text = el.get_text(strip=True)
                    if text and len(text) >= 6 and text not in seen and len(text) < 100:
                        seen.add(text)
                        headlines.append(text)

                # 去重后按顺序排列
                for idx, title in enumerate(headlines[:50]):
                    # 热度：澎湃无公开热度值，按排名递减模拟
                    hot_score = float(50 - min(idx, 40))

                    items.append({
                        "title": title,
                        "url": f"https://m.thepaper.cn/search?keyword={title}",
                        "rank": idx + 1,
                        "hot_score": hot_score,
                        "extra_data": {},
                    })

                # 尝试解析真实文章链接
                items = await self._resolve_real_urls(items, client)

                return items

            except Exception as e:
                print(f"[澎湃爬虫] 错误: {e}")
                return []

    async def _resolve_real_urls(self, items, client):
        """从搜索页解析第一条真实文章链接"""
        import urllib.parse
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.thepaper.cn/",
        }
        from bs4 import BeautifulSoup
        for item in items[:10]:
            try:
                keyword = urllib.parse.quote(item["title"])
                resp = await client.get(
                    f"https://m.thepaper.cn/search?keyword={keyword}",
                    headers=headers, timeout=8, follow_redirects=True
                )
                soup = BeautifulSoup(resp.text, "html.parser")
                # 澎湃搜索结果链接包含 newsDetail_forward
                link = soup.select_one("a[href*='newsDetail_forward']")
                if link:
                    href = link.get("href", "")
                    if href.startswith("//"):
                        href = "https:" + href
                    elif href.startswith("/"):
                        href = "https://m.thepaper.cn" + href
                    item["url"] = href
            except Exception:
                pass
        return items
