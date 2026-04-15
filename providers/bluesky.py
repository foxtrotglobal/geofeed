"""Bluesky provider — uses AT Protocol feed search with reverse-geocoded keywords."""

from datetime import datetime, timezone

import httpx

import config
from geo import reverse_geocode
from models import GeoPost, SearchParams
from providers.base import BaseProvider

# Try endpoints in order — public.api.bsky.app is Cloudflare-protected
SEARCH_URLS = [
    "https://api.bsky.app/xrpc/app.bsky.feed.searchPosts",
    "https://bsky.social/xrpc/app.bsky.feed.searchPosts",
    "https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts",
]


class BlueskyProvider(BaseProvider):
    name = "bluesky"
    color = "#0085FF"

    def __init__(self):
        # Optional: authenticated requests allow higher rate limits
        self.identifier = config.get("bluesky", "identifier")
        self.app_password = config.get("bluesky", "app_password")

    def is_configured(self) -> bool:
        # Public search requires no credentials
        return True

    async def search(self, params: SearchParams) -> list[GeoPost]:
        place_name = await reverse_geocode(params.latitude, params.longitude)
        query = f"{params.keyword} {place_name}".strip() if params.keyword else place_name

        headers = {
            "Accept": "application/json",
            "User-Agent": "GeoFeed/1.2 (https://github.com/foxtrotglobal/geofeed)",
            "atproto-proxy": "did:web:api.bsky.app#bsky_appview",
        }
        query_params = {
            "q": query,
            "limit": min(params.max_results, 25),
            "sort": "latest",
            "lang": "en",
        }

        data = None
        async with httpx.AsyncClient() as client:
            for url in SEARCH_URLS:
                try:
                    resp = await client.get(
                        url, params=query_params, headers=headers, timeout=10
                    )
                    if resp.status_code == 200 and resp.content:
                        data = resp.json()
                        break
                except Exception:
                    continue
        if not data:
            return []

        posts = []
        for post_data in data.get("posts", []):
            record = post_data.get("record", {})
            author = post_data.get("author", {})
            uri = post_data.get("uri", "")

            # Convert at://did.../app.bsky.feed.post/rkey → profile URL
            handle = author.get("handle", "")
            rkey = uri.split("/")[-1] if uri else ""
            url = f"https://bsky.app/profile/{handle}/post/{rkey}" if handle and rkey else ""

            created_at = None
            indexed = post_data.get("indexedAt") or record.get("createdAt", "")
            if indexed:
                try:
                    created_at = datetime.fromisoformat(indexed.replace("Z", "+00:00"))
                except ValueError:
                    pass

            thumb = ""
            embed = post_data.get("embed", {})
            images = embed.get("images", [])
            if images:
                thumb = images[0].get("thumb", "")

            post = GeoPost(
                platform="bluesky",
                post_id=uri,
                url=url,
                text=record.get("text", "")[:200],
                author=handle,
                latitude=params.latitude,
                longitude=params.longitude,
                location_name=place_name,
                media_url=thumb,
                timestamp=created_at,
            )
            posts.append(post)

        return posts
