"""X/Twitter provider — uses API v2 recent search with point_radius geo query."""

from datetime import datetime, timezone

import httpx

import config
from models import GeoPost, SearchParams
from providers.base import BaseProvider

SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"


class TwitterProvider(BaseProvider):
    name = "twitter"
    color = "#1DA1F2"

    def __init__(self):
        self.bearer_token = config.get("twitter", "bearer_token")

    def is_configured(self) -> bool:
        return bool(self.bearer_token)

    async def search(self, params: SearchParams) -> list[GeoPost]:
        headers = {"Authorization": f"Bearer {self.bearer_token}"}

        # Try geo query first (requires Elevated access)
        radius_mi = min(params.radius_km * 0.621371, 25)
        geo_part = f"point_radius:[{params.longitude} {params.latitude} {radius_mi:.1f}mi]"
        geo_query = f"{params.keyword} {geo_part}".strip() if params.keyword else geo_part

        data = await self._query(geo_query, params.max_results, headers)

        # Fall back to keyword-only search (free tier) when geo fails
        if data is None:
            from geo import reverse_geocode
            place_name = await reverse_geocode(params.latitude, params.longitude)
            fallback_query = f"{params.keyword} {place_name}".strip() if params.keyword else place_name
            data = await self._query(fallback_query, params.max_results, headers)

        if not data:
            return []

        return self._parse(data)

    async def _query(self, query: str, max_results: int, headers: dict) -> dict | None:
        """Run a search query, returning None if the tier doesn't support it."""
        query_params = {
            "query": query,
            "max_results": min(max(max_results, 10), 100),
            "tweet.fields": "created_at,geo,author_id,text",
            "expansions": "author_id,geo.place_id",
            "place.fields": "full_name,geo",
            "user.fields": "username",
        }
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    SEARCH_URL, params=query_params, headers=headers, timeout=15
                )
            if resp.status_code in (402, 403):
                return None  # Tier limitation
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return None

    def _parse(self, data: dict) -> list[GeoPost]:
        """Parse API response into GeoPosts."""
        # Build lookup maps for includes
        users = {}
        for u in data.get("includes", {}).get("users", []):
            users[u["id"]] = u.get("username", "")

        places = {}
        for p in data.get("includes", {}).get("places", []):
            places[p["id"]] = p

        posts = []
        for tweet in data.get("data", []):
            created = None
            if tweet.get("created_at"):
                created = datetime.fromisoformat(
                    tweet["created_at"].replace("Z", "+00:00")
                )

            # Try to extract coordinates from geo data
            lat, lon, loc_name = None, None, ""
            geo = tweet.get("geo", {})
            if geo.get("coordinates"):
                coords = geo["coordinates"].get("coordinates", [])
                if len(coords) == 2:
                    lon, lat = coords  # GeoJSON is [lon, lat]

            place_id = geo.get("place_id", "")
            if place_id and place_id in places:
                place = places[place_id]
                loc_name = place.get("full_name", "")
                if not lat:
                    # Use centroid of bounding box
                    bbox = place.get("geo", {}).get("bbox", [])
                    if len(bbox) == 4:
                        lon = (bbox[0] + bbox[2]) / 2
                        lat = (bbox[1] + bbox[3]) / 2

            post = GeoPost(
                platform="twitter",
                post_id=tweet["id"],
                url=f"https://x.com/i/status/{tweet['id']}",
                text=tweet.get("text", ""),
                author=users.get(tweet.get("author_id", ""), ""),
                latitude=lat,
                longitude=lon,
                location_name=loc_name,
                timestamp=created,
            )
            posts.append(post)

        return posts
