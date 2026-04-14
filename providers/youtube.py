"""YouTube provider — uses Data API v3 geo search."""

from datetime import datetime, timezone

import httpx

import config
from geo import haversine
from models import GeoPost, SearchParams
from providers.base import BaseProvider

API_URL = "https://www.googleapis.com/youtube/v3/search"


class YouTubeProvider(BaseProvider):
    name = "youtube"
    color = "#FF0000"

    def __init__(self):
        self.api_key = config.get("youtube", "api_key")

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def search(self, params: SearchParams) -> list[GeoPost]:
        query_params = {
            "part": "snippet",
            "type": "video",
            "location": f"{params.latitude},{params.longitude}",
            "locationRadius": f"{params.radius_km}km",
            "maxResults": min(params.max_results, 50),
            "order": "date",
            "key": self.api_key,
        }
        if params.keyword:
            query_params["q"] = params.keyword

        async with httpx.AsyncClient() as client:
            resp = await client.get(API_URL, params=query_params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

        posts = []
        for item in data.get("items", []):
            snippet = item["snippet"]
            video_id = item["id"]["videoId"]
            published = datetime.fromisoformat(
                snippet["publishedAt"].replace("Z", "+00:00")
            )
            post = GeoPost(
                platform="youtube",
                post_id=video_id,
                url=f"https://www.youtube.com/watch?v={video_id}",
                text=snippet.get("title", ""),
                author=snippet.get("channelTitle", ""),
                latitude=params.latitude,
                longitude=params.longitude,
                location_name=snippet.get("description", "")[:100],
                media_url=snippet.get("thumbnails", {}).get("medium", {}).get("url", ""),
                timestamp=published,
            )
            posts.append(post)

        return posts
