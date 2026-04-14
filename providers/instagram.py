"""Instagram provider — location search via internal API (requires session cookie)."""

from datetime import datetime, timezone

import httpx

import config
from geo import haversine
from models import GeoPost, SearchParams
from providers.base import BaseProvider

LOCATION_SEARCH_URL = "https://www.instagram.com/api/v1/location_search/"
LOCATION_FEED_URL = "https://www.instagram.com/api/v1/locations/{location_id}/sections/"


class InstagramProvider(BaseProvider):
    name = "instagram"
    color = "#E1306C"

    def __init__(self):
        self.cookie = config.get("instagram", "session_cookie")

    def is_configured(self) -> bool:
        return bool(self.cookie)

    def _headers(self) -> dict:
        return {
            "Cookie": self.cookie,
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/16.0 Mobile/15E148 Safari/604.1"
            ),
            "X-Ig-App-Id": "936619743392459",
            "X-Requested-With": "XMLHttpRequest",
        }

    async def search(self, params: SearchParams) -> list[GeoPost]:
        # Step 1: Find Instagram location IDs near the coordinates
        locations = await self._find_locations(params)
        if not locations:
            return []

        # Step 2: Fetch recent posts from the top locations (limit to 5)
        posts = []
        for loc in locations[: 5]:
            loc_posts = await self._get_location_posts(loc, params)
            posts.extend(loc_posts)
            if len(posts) >= params.max_results:
                break

        return posts[: params.max_results]

    async def _find_locations(self, params: SearchParams) -> list[dict]:
        """Find Instagram locations near the given coordinates."""
        query_params = {
            "latitude": params.latitude,
            "longitude": params.longitude,
            "search_query": params.keyword or "",
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                LOCATION_SEARCH_URL,
                params=query_params,
                headers=self._headers(),
                timeout=15,
            )
            if resp.status_code != 200:
                return []
            data = resp.json()

        venues = data.get("venues", [])
        # Attach distance
        for v in venues:
            lat = v.get("lat", 0)
            lng = v.get("lng", 0)
            v["_dist"] = haversine(params.latitude, params.longitude, lat, lng)

        # Filter by radius and sort by distance
        venues = [v for v in venues if v["_dist"] <= params.radius_km]
        venues.sort(key=lambda v: v["_dist"])
        return venues

    async def _get_location_posts(self, location: dict, params: SearchParams) -> list[GeoPost]:
        """Fetch recent posts from a specific Instagram location."""
        loc_id = location.get("external_id") or location.get("pk")
        loc_name = location.get("name", "")
        loc_lat = location.get("lat")
        loc_lng = location.get("lng")
        dist = location.get("_dist")

        url = LOCATION_FEED_URL.format(location_id=loc_id)
        body = {"tab": "recent"}

        async with httpx.AsyncClient() as client:
            resp = await client.post(url, data=body, headers=self._headers(), timeout=15)
            if resp.status_code != 200:
                return []
            data = resp.json()

        posts = []
        sections = data.get("sections", [])
        for section in sections:
            medias = section.get("layout_content", {}).get("medias", [])
            for m in medias:
                media = m.get("media", {})
                user = media.get("user", {})
                caption = media.get("caption") or {}

                taken_at = media.get("taken_at")
                ts = datetime.fromtimestamp(taken_at, tz=timezone.utc) if taken_at else None

                code = media.get("code", "")
                thumb = ""
                candidates = media.get("image_versions2", {}).get("candidates", [])
                if candidates:
                    thumb = candidates[0].get("url", "")

                post = GeoPost(
                    platform="instagram",
                    post_id=str(media.get("pk", "")),
                    url=f"https://www.instagram.com/p/{code}/" if code else "",
                    text=caption.get("text", "")[:200],
                    author=user.get("username", ""),
                    latitude=loc_lat,
                    longitude=loc_lng,
                    location_name=loc_name,
                    media_url=thumb,
                    timestamp=ts,
                    distance_km=dist,
                )
                posts.append(post)

        return posts
