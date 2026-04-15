"""Facebook provider — searches nearby places via Graph API and fetches tagged posts.

IMPORTANT LIMITATIONS:
  - Facebook removed public post search in Graph API v2.0 (2015).
  - This provider finds nearby Places and fetches their public feed.
  - Fetching place feeds requires a Page Access Token or User Access Token
    with pages_read_engagement permission.
  - For most pages, only public posts are returned.
  - Requires a Facebook App with an App Access Token (app_id|app_secret).
"""

from datetime import datetime, timezone

import httpx

import config
from geo import haversine
from models import GeoPost, SearchParams
from providers.base import BaseProvider

GRAPH_URL = "https://graph.facebook.com/v19.0"


class FacebookProvider(BaseProvider):
    name = "facebook"
    color = "#1877F2"

    def __init__(self):
        self.app_id = config.get("facebook", "app_id")
        self.app_secret = config.get("facebook", "app_secret")
        self._access_token: str = ""

    def is_configured(self) -> bool:
        return bool(self.app_id and self.app_secret)

    def _app_token(self) -> str:
        if not self._access_token:
            self._access_token = f"{self.app_id}|{self.app_secret}"
        return self._access_token

    async def search(self, params: SearchParams) -> list[GeoPost]:
        # Step 1: Find nearby places
        places = await self._find_places(params)
        if not places:
            return []

        # Step 2: For each place, fetch recent posts (up to 3 places)
        posts = []
        for place in places[:3]:
            place_posts = await self._get_place_posts(place, params)
            posts.extend(place_posts)
            if len(posts) >= params.max_results:
                break

        return posts[: params.max_results]

    async def _find_places(self, params: SearchParams) -> list[dict]:
        """Search for Facebook Places near the given coordinates."""
        q = params.keyword or "place"
        query_params = {
            "type": "place",
            "q": q,
            "center": f"{params.latitude},{params.longitude}",
            "distance": int(params.radius_km * 1000),  # meters
            "fields": "id,name,location",
            "access_token": self._app_token(),
            "limit": 10,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{GRAPH_URL}/search", params=query_params, timeout=15
            )
            if resp.status_code != 200:
                return []
            data = resp.json()

        places = []
        for item in data.get("data", []):
            loc = item.get("location", {})
            lat = loc.get("latitude")
            lon = loc.get("longitude")
            if lat and lon:
                item["_dist"] = haversine(params.latitude, params.longitude, lat, lon)
            else:
                item["_dist"] = float("inf")
            places.append(item)

        places.sort(key=lambda p: p["_dist"])
        return places

    async def _get_place_posts(self, place: dict, params: SearchParams) -> list[GeoPost]:
        """Fetch recent posts from a Facebook Place's feed."""
        place_id = place.get("id")
        place_name = place.get("name", "")
        loc = place.get("location", {})
        lat = loc.get("latitude", params.latitude)
        lon = loc.get("longitude", params.longitude)
        dist = place.get("_dist")

        query_params = {
            "fields": "id,message,created_time,story,attachments{media}",
            "access_token": self._app_token(),
            "limit": 10,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{GRAPH_URL}/{place_id}/posts",
                params=query_params,
                timeout=15,
            )
            if resp.status_code != 200:
                return []
            data = resp.json()

        posts = []
        for item in data.get("data", []):
            created_at = None
            if item.get("created_time"):
                try:
                    created_at = datetime.fromisoformat(
                        item["created_time"].replace("+0000", "+00:00")
                    )
                except ValueError:
                    pass

            thumb = ""
            attachments = item.get("attachments", {}).get("data", [])
            for att in attachments:
                media = att.get("media", {})
                img = media.get("image", {})
                if img.get("src"):
                    thumb = img["src"]
                    break

            text = item.get("message", "") or item.get("story", "")
            post_id = item.get("id", "")

            post = GeoPost(
                platform="facebook",
                post_id=post_id,
                url=f"https://www.facebook.com/{post_id.replace('_', '/posts/')}",
                text=text[:200],
                author=place_name,
                latitude=lat,
                longitude=lon,
                location_name=place_name,
                media_url=thumb,
                timestamp=created_at,
                distance_km=dist,
            )
            posts.append(post)

        return posts
