"""Mastodon provider — uses public instance search API with reverse-geocoded keywords."""

from datetime import datetime, timezone

import httpx

import config
from geo import reverse_geocode
from models import GeoPost, SearchParams
from providers.base import BaseProvider


class MastodonProvider(BaseProvider):
    name = "mastodon"
    color = "#6364FF"

    def __init__(self):
        # Default to mastodon.social; configurable for other instances
        self.instance = config.get("mastodon", "instance") or "mastodon.social"
        self.access_token = config.get("mastodon", "access_token")

    def is_configured(self) -> bool:
        return True  # Public search works without credentials

    async def search(self, params: SearchParams) -> list[GeoPost]:
        place_name = await reverse_geocode(params.latitude, params.longitude)
        # Use place name as a hashtag (most reliable public endpoint without auth)
        hashtag = place_name.replace(" ", "").lower()

        headers = {"User-Agent": "GeoFeed/1.2"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        # Try hashtag timeline first (public, no auth required)
        posts = await self._hashtag_timeline(hashtag, place_name, params, headers)

        # If keyword given, also try public timeline filtered by keyword
        if not posts and params.keyword:
            posts = await self._public_timeline(params.keyword, place_name, params, headers)

        return posts

    async def _hashtag_timeline(
        self, hashtag: str, place_name: str, params: SearchParams, headers: dict
    ) -> list[GeoPost]:
        url = f"https://{self.instance}/api/v1/timelines/tag/{hashtag}"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    url,
                    params={"limit": min(params.max_results, 40), "local": "false"},
                    headers=headers,
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []
                data = resp.json()
        except Exception:
            return []

        return self._parse_statuses(data, place_name, params)

    async def _public_timeline(
        self, keyword: str, place_name: str, params: SearchParams, headers: dict
    ) -> list[GeoPost]:
        """Authenticated search fallback when token is available."""
        if not self.access_token:
            return []
        url = f"https://{self.instance}/api/v2/search"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    url,
                    params={"q": keyword, "type": "statuses", "limit": 20, "resolve": "false"},
                    headers=headers,
                    timeout=15,
                )
                if resp.status_code != 200:
                    return []
                data = resp.json()
        except Exception:
            return []
        return self._parse_statuses(data.get("statuses", []), place_name, params)

    def _parse_statuses(self, statuses: list, place_name: str, params: SearchParams) -> list[GeoPost]:
        """Shared status parser."""
        posts = []
        for status in statuses:
            account = status.get("account", {})

            created_at = None
            if status.get("created_at"):
                try:
                    created_at = datetime.fromisoformat(
                        status["created_at"].replace("Z", "+00:00")
                    )
                except ValueError:
                    pass

            # Strip HTML tags from content
            content = status.get("content", "")
            import re
            text = re.sub(r"<[^>]+>", "", content).strip()[:200]

            thumb = ""
            for att in status.get("media_attachments", []):
                if att.get("type") in ("image", "video"):
                    thumb = att.get("preview_url", "") or att.get("url", "")
                    break

            # Extract geo from status if available
            lat, lon = params.latitude, params.longitude
            loc_name = place_name
            if status.get("place"):
                place = status["place"]
                loc_name = place.get("full_name", place_name)

            post = GeoPost(
                platform="mastodon",
                post_id=status.get("id", ""),
                url=status.get("url", ""),
                text=text,
                author=account.get("acct", ""),
                latitude=params.latitude,
                longitude=params.longitude,
                location_name=place_name,
                media_url=thumb,
                timestamp=created_at,
            )
            posts.append(post)

        return posts
