"""B站热门爬虫 - 获取搜索框热搜榜数据"""
import httpx
from typing import List, Dict, Any


class BilibiliCrawler:
    name = "bilibili"
    display_name = "B站"
    # B站搜索框热搜API（与用户在搜索框看到的热搜一致）
    search_square_url = "https://api.bilibili.com/x/web-interface/search/square"

    async def fetch(self) -> List[Dict[str, Any]]:
        """获取B站搜索框热搜榜"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.bilibili.com/",
            "Origin": "https://www.bilibili.com",
            "Accept": "application/json, text/plain, */*",
        }

        params = {
            "limit": 50,
            "platform": "pc",
            "highlight": 0,
            "single_column": 0,
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.get(self.search_square_url, headers=headers, params=params)
                resp.raise_for_status()
                data = resp.json()

                if data.get("code") != 0:
                    print(f"[B站爬虫] API返回错误: {data.get('message')}")
                    return []

                items = []
                trending = data.get("data", {}).get("trending", {})
                hot_list = trending.get("list", [])

                for idx, entry in enumerate(hot_list[:50]):
                    # 优先使用 show_name（更友好的展示名），fallback 到 keyword
                    title = (entry.get("show_name") or entry.get("keyword", "")).strip()
                    if not title:
                        continue

                    hot_score = float(entry.get("heat_score", 0) or (50 - idx))

                    # 跳转链接：goto=av 或 search 等，uri 包含具体路径
                    goto = entry.get("goto", "")
                    uri = entry.get("uri", "")
                    if uri and uri.startswith("http"):
                        url = uri
                    elif goto and uri:
                        url = f"https://www.bilibili.com/{uri}"
                    else:
                        url = f"https://search.bilibili.com/all?keyword={title}"

                    items.append({
                        "title": title,
                        "url": url,
                        "rank": idx + 1,
                        "hot_score": round(hot_score, 1),
                        "extra_data": {
                            "keyword": entry.get("keyword", ""),
                            "show_name": entry.get("show_name", ""),
                            "icon": entry.get("icon", ""),
                            "heat_score": entry.get("heat_score", 0),
                            "goto": goto,
                        }
                    })

                return items

            except Exception as e:
                print(f"[B站爬虫] 错误: {e}")
                return []