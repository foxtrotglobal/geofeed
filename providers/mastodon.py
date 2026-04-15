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
        query = f"{params.keyword} {place_name}".strip() if params.keyword else place_name

        url = f"https://{self.instance}/api/v2/search"
        headers = {}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        query_params = {
            "q": query,
            "type": "statuses",
            "limit": min(params.max_results, 40),
            "resolve": "false",
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    url, params=query_params, headers=headers, timeout=15
                )
                if resp.status_code != 200:
                    return []
                data = resp.json()
        except Exception:
            return []

        posts = []
        for status in data.get("statuses", []):
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
                latitude=lat,
                longitude=lon,
                location_name=loc_name,
                media_url=thumb,
                timestamp=created_at,
            )
            posts.append(post)

        return posts
