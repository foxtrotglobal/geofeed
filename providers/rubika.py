"""Rubika provider — searches Iran's Rubika social network.

Rubika (rubika.ir) is one of Iran's largest home-grown social networks.
Public content is searchable via their web interface.
No API key required for public search.
"""

import re
from datetime import datetime, timezone
from html import unescape

import httpx

import config
from geo import reverse_geocode
from models import GeoPost, SearchParams
from providers.base import BaseProvider

SEARCH_URL = "https://rubika.ir/search"
API_SEARCH_URL = "https://rubika.ir/api/search"
_TAG_RE = re.compile(r"<[^>]+>")


class RubikaProvider(BaseProvider):
    name = "rubika"
    color = "#00B259"

    def __init__(self):
        pass

    def is_configured(self) -> bool:
        return True

    async def search(self, params: SearchParams) -> list[GeoPost]:
        place_name = await reverse_geocode(params.latitude, params.longitude)
        query = f"{params.keyword} {place_name}".strip() if params.keyword else place_name

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/html",
            "Accept-Language": "fa-IR,fa;q=0.9",
            "Referer": "https://rubika.ir/",
        }

        # Try JSON API first
        posts = await self._try_api(query, place_name, params, headers)
        if posts:
            return posts

        # Fallback: try web search scrape
        return await self._try_web(query, place_name, params, headers)

    async def _try_api(self, query: str, place_name: str, params: SearchParams, headers: dict) -> list[GeoPost]:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    API_SEARCH_URL,
                    params={"q": query, "type": "post", "limit": min(params.max_results, 20)},
                    headers=headers,
                    timeout=12,
                    follow_redirects=True,
                )
                if resp.status_code != 200:
                    return []
                data = resp.json()
        except Exception:
            return []

        posts = []
        items = data.get("posts", data.get("results", data.get("data", [])))
        for item in items:
            text = item.get("text", "") or item.get("content", "") or item.get("caption", "")
            post_id = str(item.get("id", "") or item.get("post_id", ""))
            author = item.get("author", {})
            username = (
                author.get("username", "") if isinstance(author, dict)
                else str(author)
            )
            thumb = item.get("thumbnail", "") or item.get("image", "")
            url = item.get("url", "") or (f"https://rubika.ir/post/{post_id}" if post_id else "")

            created_at = None
            ts = item.get("created_at") or item.get("date")
            if ts:
                try:
                    created_at = datetime.fromisoformat(str(ts).replace(" ", "T"))
                except ValueError:
                    pass

            posts.append(GeoPost(
                platform="rubika",
                post_id=post_id,
                url=url,
                text=str(text)[:200],
                author=username,
                latitude=params.latitude,
                longitude=params.longitude,
                location_name=place_name,
                media_url=thumb,
                timestamp=created_at,
            ))

        return posts

    async def _try_web(self, query: str, place_name: str, params: SearchParams, headers: dict) -> list[GeoPost]:
        """Last-resort: scrape web search page."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    SEARCH_URL,
                    params={"q": query},
                    headers=headers,
                    timeout=12,
                    follow_redirects=True,
                )
                if resp.status_code != 200:
                    return []
                html = resp.text
        except Exception:
            return []

        # Extract basic post content with regex
        text_blocks = re.findall(r'class="[^"]*post[^"]*"[^>]*>(.*?)</(?:div|article)>', html, re.DOTALL)
        posts = []
        for i, block in enumerate(text_blocks[:params.max_results]):
            text = unescape(_TAG_RE.sub("", block)).strip()
            if len(text) < 10:
                continue
            posts.append(GeoPost(
                platform="rubika",
                post_id=f"rubika_web_{i}",
                url=SEARCH_URL + f"?q={query}",
                text=text[:200],
                author="",
                latitude=params.latitude,
                longitude=params.longitude,
                location_name=place_name,
            ))

        return posts
