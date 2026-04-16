"""TikTok provider — reverse-geocodes coordinates to a place name, then searches TikTok."""

from datetime import datetime, timezone

import httpx

import config
from geo import reverse_geocode
from models import GeoPost, SearchParams
from providers.base import BaseProvider

# TikTok search endpoints to try in order
SEARCH_URLS = [
    "https://www.tiktok.com/api/search/item/full/",
    "https://www.tiktok.com/api/search/general/full/",
]


class TikTokProvider(BaseProvider):
    name = "tiktok"
    color = "#000000"

    def __init__(self):
        self.ms_token = config.get("tiktok", "ms_token")
        self.ttwid = config.get("tiktok", "ttwid")

    def is_configured(self) -> bool:
        # TikTok works without credentials (but may be rate-limited)
        return True

    async def search(self, params: SearchParams) -> list[GeoPost]:
        # Step 1: Reverse-geocode the coordinates to a place name
        place_name = await reverse_geocode(params.latitude, params.longitude)
        keyword = f"{params.keyword} {place_name}".strip() if params.keyword else place_name

        # Step 2: Search TikTok for that place name
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": "https://www.tiktok.com/",
        }
        cookies = {}
        if self.ms_token:
            cookies["msToken"] = self.ms_token
        if self.ttwid:
            cookies["ttwid"] = self.ttwid

        query_params = {
            "keyword": keyword,
            "offset": 0,
            "count": min(params.max_results, 20),
            "search_id": "",
            "type": 1,
        }

        data = None
        async with httpx.AsyncClient() as client:
            for url in SEARCH_URLS:
                try:
                    resp = await client.get(
                        url,
                        params=query_params,
                        headers=headers,
                        cookies=cookies,
                        timeout=12,
                        follow_redirects=True,
                    )
                    if resp.status_code == 200 and resp.content:
                        data = resp.json()
                        if data.get("data"):
                            break
                except Exception:
                    continue
        if not data:
            return []

        posts = []
        for item in data.get("data", []):
            video = item.get("item", item)
            if not isinstance(video, dict):
                continue

            desc = video.get("desc", "")
            author_info = video.get("author", {})
            video_id = video.get("id", "")
            username = author_info.get("uniqueId", "") if isinstance(author_info, dict) else ""

            created = None
            ts = video.get("createTime")
            if ts:
                try:
                    created = datetime.fromtimestamp(int(ts), tz=timezone.utc)
                except (ValueError, TypeError):
                    pass

            cover = ""
            video_data = video.get("video", {})
            if isinstance(video_data, dict):
                cover = video_data.get("cover", "") or video_data.get("dynamicCover", "")

            post = GeoPost(
                platform="tiktok",
                post_id=video_id,
                url=f"https://www.tiktok.com/@{username}/video/{video_id}" if username else "",
                text=desc[:200],
                author=username,
                latitude=params.latitude,
                longitude=params.longitude,
                location_name=place_name,
                media_url=cover,
                timestamp=created,
            )
            posts.append(post)

        return posts
