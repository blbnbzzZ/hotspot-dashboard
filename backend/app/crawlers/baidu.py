"""百度热搜爬虫 - HTML解析"""
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Any
import re


class BaiduCrawler:
    name = "baidu"
    display_name = "百度"
    base_url = "https://top.baidu.com/board?tab=realtime"

    async def fetch(self) -> List[Dict[str, Any]]:
        """获取百度实时热搜"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            try:
                resp = await client.get(self.base_url, headers=headers)
                resp.raise_for_status()

                # 百度热搜页面的数据可能通过JS渲染，尝试从内嵌数据提取
                html = resp.text

                # 方法1: 尝试从 JSON 数据中提取（百度热搜新版页面）
                json_match = re.search(r'window\.__PRELOADED_STATE__\s*=\s*({.+?});', html, re.DOTALL)
                if json_match:
                    import json
                    try:
                        state = json.loads(json_match.group(1))
                        return self._parse_state(state)
                    except json.JSONDecodeError:
                        pass

                # 方法2: HTML 解析（旧版备用）
                soup = BeautifulSoup(html, "lxml")
                return self._parse_html(soup)

            except Exception as e:
                print(f"[百度爬虫] 错误: {e}")
                return []

    def _parse_state(self, state: dict) -> List[Dict[str, Any]]:
        """解析新版百度热搜 JSON 数据"""
        items = []
        try:
            cards = state.get("data", {}).get("cards", [])
            for card in cards:
                content = card.get("content", [])
                for idx, item in enumerate(content[:50]):
                    title = (item.get("word") or item.get("query") or "").strip()
                    if not title:
                        continue

                    hot_score = item.get("hotScore", 0) or item.get("score", 0)
                    items.append({
                        "title": title,
                        "url": item.get("url", f"https://www.baidu.com/s?wd={title}"),
                        "rank": item.get("index", idx + 1),
                        "hot_score": float(hot_score) if hot_score else float(50 - idx),
                        "extra_data": {
                            "desc": item.get("desc", ""),
                            "hot_change": item.get("hotChange", ""),
                        }
                    })
        except Exception as e:
            print(f"[百度解析] JSON解析出错: {e}")

        return items

    def _parse_html(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """HTML回退解析"""
        items = []
        hot_items = soup.select(".category-wrap_iQLoo .content_1YWBm")
        if not hot_items:
            hot_items = soup.select("[class*='hot'] a, .list-item, .hot-item")

        for idx, item in enumerate(hot_items[:50]):
            title = item.get_text(strip=True)
            if not title or len(title) < 2:
                continue
            items.append({
                "title": title,
                "url": f"https://www.baidu.com/s?wd={title}",
                "rank": idx + 1,
                "hot_score": float(50 - min(idx, 49)),
                "extra_data": {}
            })

        return items
