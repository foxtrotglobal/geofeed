"""Snapchat provider — fetches public Snap Map stories near GPS coordinates."""

from datetime import datetime, timezone

import httpx

import config
from models import GeoPost, SearchParams
from providers.base import BaseProvider

# Snap Map public tile endpoint — returns public "Our Story" snaps near a location
SNAP_MAP_URL = "https://ms.sc-cdn.net/v2/slide/map"


class SnapchatProvider(BaseProvider):
    name = "snapchat"
    color = "#FFFC00"

    def __init__(self):
        pass

    def is_configured(self) -> bool:
        return True  # Uses public Snap Map — no credentials required

    async def search(self, params: SearchParams) -> list[GeoPost]:
        # Snap Map uses a zoom level — map radius to approximate zoom
        # zoom 14 ≈ 2km, zoom 12 ≈ 8km, zoom 10 ≈ 30km
        if params.radius_km <= 2:
            zoom = 14
        elif params.radius_km <= 10:
            zoom = 12
        else:
            zoom = 10

        query_params = {
            "lat": params.latitude,
            "lng": params.longitude,
            "zoom": zoom,
        }
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
            ),
            "Referer": "https://map.snapchat.com/",
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    SNAP_MAP_URL,
                    params=query_params,
                    headers=headers,
                    timeout=15,
                    follow_redirects=True,
                )
                if resp.status_code != 200:
                    return []
                data = resp.json()
        except Exception:
            return []

        posts = []
        elements = data.get("elements", data.get("liveSnaps", []))
        for element in elements:
            snap_id = element.get("id", "")
            media = element.get("snapInfo", element.get("snapPreviewMedia", {}))
            thumb = ""
            if isinstance(media, dict):
                thumb = (
                    media.get("overlayImageMediaInfo", {}).get("mediaUrl", "")
                    or media.get("previewImageMediaInfo", {}).get("mediaUrl", "")
                )

            # Location
            loc = element.get("lat_lng_source", element.get("location", {}))
            lat = float(loc.get("lat", params.latitude)) if isinstance(loc, dict) else params.latitude
            lon = float(loc.get("lon", loc.get("lng", params.longitude))) if isinstance(loc, dict) else params.longitude

            place = element.get("placeInfo", {})
            loc_name = place.get("name", "") if isinstance(place, dict) else ""

            created_at = None
            ts = element.get("timestamp", element.get("captureTimeSecs"))
            if ts:
                try:
                    created_at = datetime.fromtimestamp(int(ts) / 1000, tz=timezone.utc)
                except (ValueError, TypeError, OSError):
                    pass

            url = f"https://www.snapchat.com/add/story/{snap_id}" if snap_id else ""

            post = GeoPost(
                platform="snapchat",
                post_id=snap_id,
                url=url,
                text=element.get("title", ""),
                author="",
                latitude=lat,
                longitude=lon,
                location_name=loc_name,
                media_url=thumb,
                timestamp=created_at,
            )
            posts.append(post)

        return posts[: params.max_results]
