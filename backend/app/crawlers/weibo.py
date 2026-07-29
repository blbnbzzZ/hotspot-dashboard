"""微博热搜爬虫 - 使用官方AJAX接口"""
import httpx
from typing import List, Dict, Any


class WeiboCrawler:
    name = "weibo"
    display_name = "微博"
    base_url = "https://weibo.com/ajax/side/hotSearch"

    async def fetch(self) -> List[Dict[str, Any]]:
        """获取微博热搜榜"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://weibo.com/",
            "Accept": "application/json, text/plain, */*",
            "X-Requested-With": "XMLHttpRequest",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.get(self.base_url, headers=headers)
                resp.raise_for_status()
                data = resp.json()

                items = []
                realtime = data.get("data", {}).get("realtime", [])

                for idx, item in enumerate(realtime[:50]):  # 取前50条
                    word = item.get("word", "").strip()
                    if not word:
                        continue

                    raw_hot = item.get("raw_hot", 0) or item.get("num", 0) or 0
                    hot_score = float(raw_hot) if raw_hot else float(50 - idx)

                    items.append({
                        "title": word,
                        "url": f"https://s.weibo.com/weibo?q={word}",
                        "rank": idx + 1,
                        "hot_score": round(hot_score, 1),
                        "extra_data": {
                            "category": item.get("category", ""),
                            "label": item.get("label_name", ""),
                        }
                    })

                return items

            except Exception as e:
                print(f"[微博爬虫] 错误: {e}")
                return []
