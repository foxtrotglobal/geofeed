"""Reddit provider — searches Reddit posts by reverse-geocoded location keyword.

Uses Reddit's public JSON search API. No API key required.
Optionally restrict to specific subreddits via config.

Default subreddits include general and Middle East / Iran focused communities.
"""

from datetime import datetime, timezone

import httpx

import config
from geo import reverse_geocode
from models import GeoPost, SearchParams
from providers.base import BaseProvider

SEARCH_URL = "https://www.reddit.com/search.json"
SUBREDDIT_URL = "https://www.reddit.com/r/{sub}/search.json"

# Default subreddits for Middle East / Iran context (plus general geo search)
DEFAULT_SUBREDDITS = [
    "iran",
    "tehran",
    "middleeast",
    "worldnews",
    "news",
]


class RedditProvider(BaseProvider):
    name = "reddit"
    color = "#FF4500"

    def __init__(self):
        custom_subs = config.get("reddit", "subreddits")
        if custom_subs:
            self.subreddits = [s.strip() for s in custom_subs.split(",") if s.strip()]
        else:
            self.subreddits = list(DEFAULT_SUBREDDITS)
        self.client_id = config.get("reddit", "client_id")
        self.client_secret = config.get("reddit", "client_secret")

    def is_configured(self) -> bool:
        return True  # Public JSON search requires no credentials

    async def search(self, params: SearchParams) -> list[GeoPost]:
        place_name = await reverse_geocode(params.latitude, params.longitude)
        query = f"{params.keyword} {place_name}".strip() if params.keyword else place_name

        headers = {
            "User-Agent": "GeoFeed/1.2 (open source geo search tool)",
            "Accept": "application/json",
        }

        posts = []

        async with httpx.AsyncClient() as client:
            # Global search first
            global_posts = await self._search(
                client, SEARCH_URL, query, params, place_name, headers
            )
            posts.extend(global_posts)

            # Subreddit-specific searches (top 3 most relevant subs)
            for sub in self.subreddits[:3]:
                sub_posts = await self._search(
                    client,
                    SUBREDDIT_URL.format(sub=sub),
                    query,
                    params,
                    place_name,
                    headers,
                    restrict_sr=True,
                )
                posts.extend(sub_posts)

        # Deduplicate by post_id, sort newest first
        seen = set()
        unique = []
        for p in sorted(
            posts,
            key=lambda x: x.timestamp or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        ):
            if p.post_id not in seen:
                seen.add(p.post_id)
                unique.append(p)

        return unique[: params.max_results]

    async def _search(
        self,
        client: httpx.AsyncClient,
        url: str,
        query: str,
        params: SearchParams,
        place_name: str,
        headers: dict,
        restrict_sr: bool = False,
    ) -> list[GeoPost]:
        query_params = {
            "q": query,
            "sort": "new",
            "limit": min(params.max_results, 25),
            "type": "link",
            "t": "month",
        }
        if restrict_sr:
            query_params["restrict_sr"] = "1"

        try:
            resp = await client.get(url, params=query_params, headers=headers, timeout=15)
            if resp.status_code == 429:
                return []  # Rate limited
            if resp.status_code != 200:
                return []
            data = resp.json()
        except Exception:
            return []

        posts = []
        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})
            post_id = post.get("id", "")
            title = post.get("title", "")
            selftext = post.get("selftext", "")[:150]
            text = f"{title} — {selftext}".strip(" —") if selftext else title
            author = post.get("author", "")
            subreddit = post.get("subreddit", "")
            thumb = post.get("thumbnail", "")
            if thumb in ("self", "default", "nsfw", "spoiler", ""):
                thumb = post.get("url_overridden_by_dest", "") if post.get("post_hint") == "image" else ""
            url_val = f"https://www.reddit.com{post.get('permalink', '')}"

            created_at = None
            ts = post.get("created_utc")
            if ts:
                try:
                    created_at = datetime.fromtimestamp(float(ts), tz=timezone.utc)
                except (ValueError, TypeError):
                    pass

            posts.append(GeoPost(
                platform="reddit",
                post_id=post_id,
                url=url_val,
                text=text[:200],
                author=f"u/{author}" if author else "",
                latitude=params.latitude,
                longitude=params.longitude,
                location_name=place_name,
                media_url=thumb,
                timestamp=created_at,
                extra={"subreddit": subreddit},
            ))

        return posts
