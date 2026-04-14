"""Unified data model for social media geo posts."""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


@dataclass
class GeoPost:
    """A single social media post with geographic information."""

    platform: str
    post_id: str
    url: str
    text: str = ""
    author: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_name: str = ""
    media_url: str = ""
    timestamp: Optional[datetime] = None
    distance_km: Optional[float] = None
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to a JSON-friendly dict."""
        d = asdict(self)
        if self.timestamp:
            d["timestamp"] = self.timestamp.isoformat()
        return d


@dataclass
class SearchParams:
    """Parameters for a geo search."""

    latitude: float
    longitude: float
    radius_km: float = 10.0
    keyword: str = ""
    max_results: int = 50
