"""Aparat provider — searches Iran's dominant video platform by location keyword.

Aparat (aparat.com) is the most popular video hosting platform in Iran,
equivalent to YouTube. This provider searches by reverse-geocoded place name.
No API key required.
"""

from datetime import datetime, timezone

import httpx

import config
from geo import reverse_geocode
from models import GeoPost, SearchParams
from providers.base import BaseProvider

SEARCH_URL = "https://www.aparat.com/api/fa/v1/video/video/list/videosearch/text/{query}"
FALLBACK_URL = "https://www.aparat.com/etc/api/search/video"


class AparatProvider(BaseProvider):
    name = "aparat"
    color = "#D72323"

    def __init__(self):
        pass

    def is_configured(self) -> bool:
        return True  # No credentials needed

    async def search(self, params: SearchParams) -> list[GeoPost]:
        place_name = await reverse_geocode(params.latitude, params.longitude)
        query = f"{params.keyword} {place_name}".strip() if params.keyword else place_name

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8",
            "Referer": "https://www.aparat.com/",
        }

        data = None
        async with httpx.AsyncClient() as client:
            # Try primary endpoint
            try:
                resp = await client.get(
                    SEARCH_URL.format(query=query),
                    headers=headers,
                    timeout=15,
                )
                if resp.status_code == 200:
                    data = resp.json()
            except Exception:
                pass

            # Fallback endpoint
            if data is None:
                try:
                    resp = await client.get(
                        FALLBACK_URL,
                        params={"q": query, "perpage": min(params.max_results, 20)},
                        headers=headers,
                        timeout=15,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                except Exception:
                    pass

        if not data:
            return []

        posts = []
        # Handle multiple response shapes from Aparat's API
        raw_data = data.get("data", [])
        if isinstance(raw_data, list):
            items = raw_data
        elif isinstance(raw_data, dict):
            items = (
                raw_data.get("attributes", {}).get("videos", [])
                or raw_data.get("videos", [])
                or []
            )
        else:
            items = data.get("included", []) or []

        for item in items:
            attrs = item.get("attributes", item)  # Normalise both formats
            video_id = str(item.get("id", "") or attrs.get("uid", ""))
            title = attrs.get("title", "")
            username = attrs.get("username", "") or attrs.get("cnt_id", "")
            thumb = attrs.get("big_poster", "") or attrs.get("poster", "")
            url = f"https://www.aparat.com/v/{video_id}" if video_id else ""

            created_at = None
            ts = attrs.get("create_date") or attrs.get("sdate")
            if ts:
                try:
                    created_at = datetime.fromisoformat(str(ts).replace(" ", "T"))
                except ValueError:
                    pass

            if not title:
                continue

            posts.append(GeoPost(
                platform="aparat",
                post_id=video_id,
                url=url,
                text=title[:200],
                author=str(username),
                latitude=params.latitude,
                longitude=params.longitude,
                location_name=place_name,
                media_url=thumb,
                timestamp=created_at,
            ))

        return posts[: params.max_results]
