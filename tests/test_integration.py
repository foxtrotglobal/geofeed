"""Integration tests for provider orchestration and search aggregation."""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import GeoPost, SearchParams

PARAMS = SearchParams(latitude=40.7128, longitude=-74.006, radius_km=10)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_post(platform: str, idx: int = 0, ts=None) -> GeoPost:
    return GeoPost(
        platform=platform,
        post_id=f"{platform}_{idx}",
        url=f"https://{platform}.com/{idx}",
        text=f"Post {idx}",
        author="tester",
        latitude=40.7,
        longitude=-74.0,
        timestamp=ts or datetime(2024, 6, idx + 1, tzinfo=timezone.utc),
    )


def _make_provider(name: str, posts: list[GeoPost], configured: bool = True):
    """Create a mock provider that returns given posts."""
    p = MagicMock()
    p.name = name
    p.is_configured.return_value = configured
    p.search = AsyncMock(return_value=posts)
    return p


# ---------------------------------------------------------------------------
# run_search — orchestration
# ---------------------------------------------------------------------------

class TestRunSearch:
    @pytest.mark.asyncio
    async def test_returns_posts_from_all_providers(self):
        from server import run_search, ALL_PROVIDERS

        yt_posts = [_make_post("youtube", 0)]
        rd_posts = [_make_post("reddit", 1)]

        yt_cls = MagicMock(return_value=_make_provider("youtube", yt_posts))
        rd_cls = MagicMock(return_value=_make_provider("reddit", rd_posts))

        with patch.dict(ALL_PROVIDERS, {"youtube": yt_cls, "reddit": rd_cls}, clear=True):
            results = await run_search(PARAMS, ["youtube", "reddit"])

        assert len(results) == 2
        platforms = {r["platform"] for r in results}
        assert platforms == {"youtube", "reddit"}

    @pytest.mark.asyncio
    async def test_skips_unconfigured_providers(self):
        from server import run_search, ALL_PROVIDERS

        configured = _make_provider("youtube", [_make_post("youtube")])
        unconfigured = _make_provider("twitter", [], configured=False)

        yt_cls = MagicMock(return_value=configured)
        tw_cls = MagicMock(return_value=unconfigured)

        with patch.dict(ALL_PROVIDERS, {"youtube": yt_cls, "twitter": tw_cls}, clear=True):
            results = await run_search(PARAMS, ["youtube", "twitter"])

        # Only youtube results — twitter was unconfigured
        assert all(r["platform"] == "youtube" for r in results)

    @pytest.mark.asyncio
    async def test_skips_unknown_platform_names(self):
        from server import run_search, ALL_PROVIDERS

        yt_cls = MagicMock(return_value=_make_provider("youtube", [_make_post("youtube")]))

        with patch.dict(ALL_PROVIDERS, {"youtube": yt_cls}, clear=True):
            results = await run_search(PARAMS, ["youtube", "NOTAPLATFORM"])

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_results_sorted_newest_first(self):
        from server import run_search, ALL_PROVIDERS

        old = _make_post("youtube", 0, datetime(2024, 1, 1, tzinfo=timezone.utc))
        new = _make_post("reddit", 1, datetime(2024, 6, 15, tzinfo=timezone.utc))
        mid = _make_post("bluesky", 2, datetime(2024, 3, 10, tzinfo=timezone.utc))

        cls_map = {
            "youtube": MagicMock(return_value=_make_provider("youtube", [old])),
            "reddit": MagicMock(return_value=_make_provider("reddit", [new])),
            "bluesky": MagicMock(return_value=_make_provider("bluesky", [mid])),
        }

        with patch.dict(ALL_PROVIDERS, cls_map, clear=True):
            results = await run_search(PARAMS, list(cls_map.keys()))

        timestamps = [r["timestamp"] for r in results]
        assert timestamps == sorted(timestamps, reverse=True)

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_providers_configured(self):
        from server import run_search, ALL_PROVIDERS

        unconfigured = _make_provider("youtube", [], configured=False)
        cls = MagicMock(return_value=unconfigured)

        with patch.dict(ALL_PROVIDERS, {"youtube": cls}, clear=True):
            results = await run_search(PARAMS, ["youtube"])

        assert results == []

    @pytest.mark.asyncio
    async def test_empty_platform_list_returns_no_results(self):
        from server import run_search, ALL_PROVIDERS

        with patch.dict(ALL_PROVIDERS, {}, clear=True):
            results = await run_search(PARAMS, [])

        assert results == []


# ---------------------------------------------------------------------------
# _safe_search — error isolation
# ---------------------------------------------------------------------------

class TestSafeSearch:
    @pytest.mark.asyncio
    async def test_returns_empty_on_provider_exception(self):
        from server import _safe_search

        broken = MagicMock()
        broken.name = "broken"
        broken.search = AsyncMock(side_effect=RuntimeError("API down"))

        result = await _safe_search(broken, PARAMS)
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_on_network_error(self):
        from server import _safe_search
        import httpx

        p = MagicMock()
        p.name = "netfail"
        p.search = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))

        result = await _safe_search(p, PARAMS)
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_serialized_posts_on_success(self):
        from server import _safe_search

        posts = [_make_post("youtube", 0), _make_post("youtube", 1)]
        p = _make_provider("youtube", posts)

        result = await _safe_search(p, PARAMS)
        assert len(result) == 2
        assert all(isinstance(r, dict) for r in result)
        assert all(r["platform"] == "youtube" for r in result)

    @pytest.mark.asyncio
    async def test_one_failing_provider_does_not_affect_others(self):
        from server import run_search, ALL_PROVIDERS

        good_posts = [_make_post("reddit", 0)]
        good = _make_provider("reddit", good_posts)
        broken = MagicMock()
        broken.name = "youtube"
        broken.is_configured.return_value = True
        broken.search = AsyncMock(side_effect=Exception("Boom"))

        cls_map = {
            "youtube": MagicMock(return_value=broken),
            "reddit": MagicMock(return_value=good),
        }

        with patch.dict(ALL_PROVIDERS, cls_map, clear=True):
            results = await run_search(PARAMS, ["youtube", "reddit"])

        # Reddit results should still come through
        assert len(results) == 1
        assert results[0]["platform"] == "reddit"


# ---------------------------------------------------------------------------
# Provider registration — ALL_PROVIDERS completeness
# ---------------------------------------------------------------------------

class TestProviderRegistration:
    def test_all_providers_registered_in_server(self):
        from server import ALL_PROVIDERS
        expected = {
            "youtube", "flickr", "instagram", "twitter", "tiktok",
            "bluesky", "mastodon", "snapchat", "facebook",
            "telegram", "aparat", "rubika", "reddit",
        }
        assert expected == set(ALL_PROVIDERS.keys())

    def test_all_providers_registered_in_main(self):
        import main
        expected = {
            "youtube", "flickr", "instagram", "twitter", "tiktok",
            "bluesky", "mastodon", "snapchat", "facebook",
            "telegram", "aparat", "rubika", "reddit",
        }
        assert expected == set(main.ALL_PROVIDERS.keys())

    def test_server_and_main_have_same_providers(self):
        from server import ALL_PROVIDERS as server_providers
        import main
        assert set(server_providers.keys()) == set(main.ALL_PROVIDERS.keys())

    def test_all_provider_classes_have_name_attribute(self):
        from server import ALL_PROVIDERS
        import config as cfg; cfg._config = {}
        for key, cls in ALL_PROVIDERS.items():
            with patch.object(cls, "__init__", lambda self: None):
                instance = cls.__new__(cls)
                assert hasattr(cls, "name"), f"{key} missing class-level 'name'"

    def test_all_provider_classes_have_color_attribute(self):
        from server import ALL_PROVIDERS
        for key, cls in ALL_PROVIDERS.items():
            assert hasattr(cls, "color"), f"{key} missing class-level 'color'"
            assert cls.color.startswith("#"), f"{key} color not a hex"

    def test_all_provider_classes_are_subclasses_of_base(self):
        from server import ALL_PROVIDERS
        from providers.base import BaseProvider
        for key, cls in ALL_PROVIDERS.items():
            assert issubclass(cls, BaseProvider), f"{key} is not a BaseProvider subclass"


# ---------------------------------------------------------------------------
# SearchParams construction and validation
# ---------------------------------------------------------------------------

class TestSearchParamsEdgeCases:
    def test_zero_radius_is_allowed(self):
        p = SearchParams(latitude=0.0, longitude=0.0, radius_km=0.0)
        assert p.radius_km == 0.0

    def test_negative_radius_stored_as_is(self):
        p = SearchParams(latitude=0.0, longitude=0.0, radius_km=-5.0)
        assert p.radius_km == -5.0

    def test_poles_latitude(self):
        north = SearchParams(latitude=90.0, longitude=0.0)
        south = SearchParams(latitude=-90.0, longitude=0.0)
        assert north.latitude == 90.0
        assert south.latitude == -90.0

    def test_international_date_line_longitude(self):
        east = SearchParams(latitude=0.0, longitude=180.0)
        west = SearchParams(latitude=0.0, longitude=-180.0)
        assert east.longitude == 180.0
        assert west.longitude == -180.0

    def test_max_results_default(self):
        p = SearchParams(latitude=40.0, longitude=-74.0)
        assert p.max_results == 50

    def test_large_max_results(self):
        p = SearchParams(latitude=40.0, longitude=-74.0, max_results=10000)
        assert p.max_results == 10000
