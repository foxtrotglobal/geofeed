"""Flickr provider — uses flickr.photos.search with geo params."""

from datetime import datetime, timezone

import httpx

import config
from geo import haversine
from models import GeoPost, SearchParams
from providers.base import BaseProvider

API_URL = "https://www.flickr.com/services/rest/"


class FlickrProvider(BaseProvider):
    name = "flickr"
    color = "#0063DC"

    def __init__(self):
        self.api_key = config.get("flickr", "api_key")

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def search(self, params: SearchParams) -> list[GeoPost]:
        # Flickr uses a bounding box or lat/lon + radius (max 32km)
        query_params = {
            "method": "flickr.photos.search",
            "api_key": self.api_key,
            "lat": params.latitude,
            "lon": params.longitude,
            "radius": min(params.radius_km, 32),
            "radius_units": "km",
            "has_geo": 1,
            "extras": "geo,url_m,date_taken,owner_name,description",
            "per_page": min(params.max_results, 100),
            "sort": "date-posted-desc",
            "format": "json",
            "nojsoncallback": 1,
        }
        if params.keyword:
            query_params["text"] = params.keyword

        async with httpx.AsyncClient() as client:
            resp = await client.get(API_URL, params=query_params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

        posts = []
        for photo in data.get("photos", {}).get("photo", []):
            lat = float(photo.get("latitude", 0))
            lon = float(photo.get("longitude", 0))
            dist = haversine(params.latitude, params.longitude, lat, lon) if lat else None

            taken = None
            if photo.get("datetaken"):
                try:
                    taken = datetime.strptime(photo["datetaken"], "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    pass

            desc_raw = photo.get("description", {})
            desc = desc_raw.get("_content", "") if isinstance(desc_raw, dict) else str(desc_raw)

            post = GeoPost(
                platform="flickr",
                post_id=photo["id"],
                url=f"https://www.flickr.com/photos/{photo['owner']}/{photo['id']}",
                text=photo.get("title", ""),
                author=photo.get("ownername", photo.get("owner", "")),
                latitude=lat or None,
                longitude=lon or None,
                location_name=desc[:100],
                media_url=photo.get("url_m", ""),
                timestamp=taken,
                distance_km=dist,
            )
            posts.append(post)

        return posts
