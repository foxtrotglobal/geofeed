"""Abstract base class for geo search providers."""

from abc import ABC, abstractmethod

from models import GeoPost, SearchParams


class BaseProvider(ABC):
    """Every platform provider must implement this interface."""

    name: str = "base"
    color: str = "#888888"  # Marker color on the map

    @abstractmethod
    async def search(self, params: SearchParams) -> list[GeoPost]:
        """Search for posts near the given coordinates.

        Returns a list of GeoPost objects.
        """
        ...

    def is_configured(self) -> bool:
        """Return True if this provider has the credentials it needs."""
        return True
