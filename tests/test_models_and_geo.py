"""Tests for models.py and geo.py."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from geo import haversine, reverse_geocode
from models import GeoPost, SearchParams


# --- GeoPost ---


class TestGeoPost:
    def test_minimal_creation(self):
        post = GeoPost(platform="test", post_id="1", url="https://example.com")
        assert post.platform == "test"
        assert post.post_id == "1"
        assert post.text == ""
        assert post.latitude is None
        assert post.extra == {}

    def test_full_creation(self):
        ts = datetime(2024, 6, 15, 12, 0, tzinfo=timezone.utc)
        post = GeoPost(
            platform="youtube",
            post_id="abc123",
            url="https://youtube.com/watch?v=abc123",
            text="Test video",
            author="TestChannel",
            latitude=40.7128,
            longitude=-74.006,
            location_name="New York",
            media_url="https://img.youtube.com/vi/abc123/0.jpg",
            timestamp=ts,
            distance_km=1.5,
            extra={"views": 1000},
        )
        assert post.platform == "youtube"
        assert post.latitude == 40.7128
        assert post.distance_km == 1.5
        assert post.extra["views"] == 1000

    def test_to_dict_without_timestamp(self):
        post = GeoPost(platform="flickr", post_id="2", url="https://flickr.com/2")
        d = post.to_dict()
        assert d["platform"] == "flickr"
        assert d["post_id"] == "2"
        assert d["timestamp"] is None

    def test_to_dict_with_timestamp(self):
        ts = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
        post = GeoPost(platform="twitter", post_id="3", url="https://x.com/3", timestamp=ts)
        d = post.to_dict()
        assert d["timestamp"] == "2024-01-01T00:00:00+00:00"

    def test_extra_defaults_to_empty_dict(self):
        """Ensure each instance gets its own dict (no shared mutable default)."""
        a = GeoPost(platform="a", post_id="1", url="")
        b = GeoPost(platform="b", post_id="2", url="")
        a.extra["key"] = "val"
        assert "key" not in b.extra


# --- SearchParams ---


class TestSearchParams:
    def test_defaults(self):
        p = SearchParams(latitude=51.5, longitude=-0.12)
        assert p.radius_km == 10.0
        assert p.keyword == ""
        assert p.max_results == 50

    def test_custom_values(self):
        p = SearchParams(latitude=48.85, longitude=2.35, radius_km=25, keyword="eiffel", max_results=10)
        assert p.radius_km == 25
        assert p.keyword == "eiffel"
        assert p.max_results == 10


# --- Haversine ---


class TestHaversine:
    def test_same_point_is_zero(self):
        assert haversine(40.0, -74.0, 40.0, -74.0) == 0.0

    def test_known_distance(self):
        # New York to London ≈ 5,570 km
        dist = haversine(40.7128, -74.006, 51.5074, -0.1278)
        assert 5500 < dist < 5650

    def test_short_distance(self):
        # ~1.1 km apart in Manhattan
        dist = haversine(40.7580, -73.9855, 40.7484, -73.9856)
        assert 1.0 < dist < 1.2

    def test_symmetry(self):
        d1 = haversine(40.0, -74.0, 51.5, -0.1)
        d2 = haversine(51.5, -0.1, 40.0, -74.0)
        assert abs(d1 - d2) < 0.001


# --- Reverse Geocode ---


class TestReverseGeocode:
    @staticmethod
    def _mock_geocode_client(json_data):
        """Build a mock httpx.AsyncClient whose get() returns a sync-json response."""
        from unittest.mock import MagicMock

        resp = MagicMock()
        resp.json.return_value = json_data

        client = AsyncMock()
        client.get.return_value = resp
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        return client

    @pytest.mark.asyncio
    async def test_reverse_geocode_city(self):
        mock_client = self._mock_geocode_client({
            "address": {"city": "Paris", "country": "France"},
            "display_name": "Paris, France",
        })
        with patch("geo.httpx.AsyncClient", return_value=mock_client):
            result = await reverse_geocode(48.8566, 2.3522)
            assert result == "Paris"

    @pytest.mark.asyncio
    async def test_reverse_geocode_falls_back_to_town(self):
        mock_client = self._mock_geocode_client({
            "address": {"town": "Smallville", "country": "US"},
            "display_name": "Smallville, Kansas, US",
        })
        with patch("geo.httpx.AsyncClient", return_value=mock_client):
            result = await reverse_geocode(39.0, -95.0)
            assert result == "Smallville"

    @pytest.mark.asyncio
    async def test_reverse_geocode_falls_back_to_display_name(self):
        mock_client = self._mock_geocode_client({
            "address": {},
            "display_name": "Middle of Nowhere",
        })
        with patch("geo.httpx.AsyncClient", return_value=mock_client):
            result = await reverse_geocode(0.0, 0.0)
            assert result == "Middle of Nowhere"
