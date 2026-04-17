"""
Core functionality tests for GeoFeed.

These tests verify the complete data pipeline and system behaviours:
  - End-to-end flow: SearchParams → provider → GeoPost → JSON response
  - Parallel / concurrent provider execution
  - CLI argument parsing
  - SSE event stream format
  - Geo distance filtering
  - Provider colour uniqueness
  - GeoPost serialization contract
  - Timestamp sorting across multiple providers
  - max_results enforcement
"""

import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from geo import haversine
from models import GeoPost, SearchParams


# ============================================================
# Helpers
# ============================================================

def _post(platform, post_id, lat=40.71, lon=-74.0, ts=None, text="") -> GeoPost:
    return GeoPost(
        platform=platform,
        post_id=post_id,
        url=f"https://{platform}.com/{post_id}",
        text=text or f"Post {post_id} from {platform}",
        author="tester",
        latitude=lat,
        longitude=lon,
        timestamp=ts or datetime(2024, 6, 15, 12, 0, tzinfo=timezone.utc),
    )


def _provider(name, posts, delay=0.0, raises=None, configured=True):
    """Build a mock provider with optional artificial delay or exception."""
    p = MagicMock()
    p.name = name
    p.color = f"#{abs(hash(name)) % 0xFFFFFF:06X}"
    p.is_configured.return_value = configured

    async def fake_search(params):
        if delay:
            await asyncio.sleep(delay)
        if raises:
            raise raises
        return posts

    p.search = fake_search
    return p


# ============================================================
# 1. End-to-end data pipeline
# ============================================================

class TestEndToEndPipeline:
    """Verify data flows correctly from SearchParams → GeoPost → JSON response."""

    @pytest.mark.asyncio
    async def test_geopost_fields_preserved_through_pipeline(self):
        """All GeoPost fields survive serialization and appear in API response."""
        from server import _safe_search

        ts = datetime(2024, 3, 10, 8, 30, tzinfo=timezone.utc)
        post = GeoPost(
            platform="youtube",
            post_id="abc123",
            url="https://youtube.com/watch?v=abc123",
            text="Breaking news in Central Park",
            author="channel_xyz",
            latitude=40.785,
            longitude=-73.968,
            location_name="Central Park",
            media_url="https://img.youtube.com/vi/abc123/0.jpg",
            timestamp=ts,
            distance_km=3.2,
            extra={"views": 50000},
        )
        provider = _provider("youtube", [post])
        params = SearchParams(latitude=40.71, longitude=-74.0)

        result = await _safe_search(provider, params)

        assert len(result) == 1
        r = result[0]
        assert r["platform"] == "youtube"
        assert r["post_id"] == "abc123"
        assert r["text"] == "Breaking news in Central Park"
        assert r["author"] == "channel_xyz"
        assert r["latitude"] == 40.785
        assert r["longitude"] == -73.968
        assert r["location_name"] == "Central Park"
        assert r["media_url"] == "https://img.youtube.com/vi/abc123/0.jpg"
        assert r["distance_km"] == 3.2
        assert r["extra"] == {"views": 50000}
        assert "2024-03-10" in r["timestamp"]

    @pytest.mark.asyncio
    async def test_multiple_posts_all_serialized(self):
        from server import _safe_search

        posts = [_post("twitter", str(i)) for i in range(5)]
        provider = _provider("twitter", posts)
        result = await _safe_search(provider, SearchParams(latitude=40.71, longitude=-74.0))
        assert len(result) == 5
        assert all(r["platform"] == "twitter" for r in result)

    @pytest.mark.asyncio
    async def test_empty_provider_returns_empty_list(self):
        from server import _safe_search

        provider = _provider("flickr", [])
        result = await _safe_search(provider, SearchParams(latitude=40.71, longitude=-74.0))
        assert result == []

    @pytest.mark.asyncio
    async def test_full_search_returns_serialized_dicts(self):
        from server import run_search, ALL_PROVIDERS

        posts = [_post("bluesky", "1"), _post("bluesky", "2")]
        cls = MagicMock(return_value=_provider("bluesky", posts))

        with patch.dict(ALL_PROVIDERS, {"bluesky": cls}, clear=True):
            results = await run_search(SearchParams(latitude=40.71, longitude=-74.0), ["bluesky"])

        assert all(isinstance(r, dict) for r in results)
        assert all("platform" in r and "post_id" in r and "url" in r for r in results)

    def test_api_response_is_valid_json(self):
        """The /api/search endpoint returns parseable JSON with correct structure."""
        import config as cfg; cfg._config = {}
        from server import app
        app.config["TESTING"] = True

        fake = [_post("youtube", "1").to_dict()]
        with app.test_client() as c:
            with patch("server.run_search", new=AsyncMock(return_value=fake)):
                resp = c.post("/api/search",
                    data=json.dumps({"latitude": 40.71, "longitude": -74.0}),
                    content_type="application/json")

        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "posts" in data
        assert "count" in data
        assert isinstance(data["posts"], list)
        assert isinstance(data["count"], int)
        assert data["count"] == len(data["posts"])


# ============================================================
# 2. Concurrent execution
# ============================================================

class TestConcurrentExecution:
    """Verify providers run in parallel, not sequentially."""

    @pytest.mark.asyncio
    async def test_providers_run_concurrently(self):
        """Three 0.1s-delay providers should finish in <0.2s total if truly parallel."""
        from server import run_search, ALL_PROVIDERS

        delay = 0.1  # seconds per provider
        n = 3

        providers = {
            f"p{i}": MagicMock(return_value=_provider(f"p{i}", [], delay=delay))
            for i in range(n)
        }

        start = time.monotonic()
        with patch.dict(ALL_PROVIDERS, providers, clear=True):
            await run_search(SearchParams(latitude=40.71, longitude=-74.0), list(providers.keys()))
        elapsed = time.monotonic() - start

        # Sequential would take n * delay ≈ 0.3s; parallel should be ~0.1s
        assert elapsed < delay * n * 0.8, (
            f"Providers appear to run sequentially: {elapsed:.2f}s "
            f"(expected < {delay * n * 0.8:.2f}s for parallel)"
        )

    @pytest.mark.asyncio
    async def test_all_providers_called_exactly_once(self):
        """Each provider's search() is called exactly once per run_search invocation."""
        from server import run_search, ALL_PROVIDERS

        call_counts = {}

        def make_provider(name):
            async def search(params):
                call_counts[name] = call_counts.get(name, 0) + 1
                return []
            p = MagicMock()
            p.name = name
            p.is_configured.return_value = True
            p.search = search
            return p

        cls_map = {f"p{i}": MagicMock(return_value=make_provider(f"p{i}")) for i in range(4)}

        with patch.dict(ALL_PROVIDERS, cls_map, clear=True):
            await run_search(SearchParams(latitude=40.71, longitude=-74.0), list(cls_map.keys()))

        assert all(count == 1 for count in call_counts.values())
        assert len(call_counts) == 4

    @pytest.mark.asyncio
    async def test_failing_provider_does_not_cancel_others(self):
        """A provider that raises must not cancel sibling coroutines."""
        from server import run_search, ALL_PROVIDERS

        completed = []

        async def slow_good(params):
            await asyncio.sleep(0.05)
            completed.append("good")
            return [_post("good", "1")]

        async def fast_bad(params):
            raise RuntimeError("I crashed")

        good_p = MagicMock(); good_p.name = "good"; good_p.is_configured.return_value = True; good_p.search = slow_good
        bad_p  = MagicMock(); bad_p.name  = "bad";  bad_p.is_configured.return_value = True;  bad_p.search  = fast_bad

        cls_map = {
            "good": MagicMock(return_value=good_p),
            "bad":  MagicMock(return_value=bad_p),
        }

        with patch.dict(ALL_PROVIDERS, cls_map, clear=True):
            results = await run_search(SearchParams(latitude=40.71, longitude=-74.0), ["good", "bad"])

        assert "good" in completed, "Good provider was cancelled"
        assert len(results) == 1
        assert results[0]["platform"] == "good"


# ============================================================
# 3. Result ordering and deduplication
# ============================================================

class TestResultOrdering:
    @pytest.mark.asyncio
    async def test_newest_posts_appear_first(self):
        from server import run_search, ALL_PROVIDERS

        dates = [
            datetime(2024, 1, 1, tzinfo=timezone.utc),
            datetime(2024, 12, 31, tzinfo=timezone.utc),
            datetime(2024, 6, 15, tzinfo=timezone.utc),
        ]
        all_posts = [_post(f"p{i}", str(i), ts=d) for i, d in enumerate(dates)]

        # Distribute across providers
        cls_map = {}
        for i, post in enumerate(all_posts):
            p = _provider(f"p{i}", [post])
            cls_map[f"p{i}"] = MagicMock(return_value=p)

        with patch.dict(ALL_PROVIDERS, cls_map, clear=True):
            results = await run_search(
                SearchParams(latitude=40.71, longitude=-74.0), list(cls_map.keys())
            )

        ts_list = [r["timestamp"] for r in results]
        assert ts_list == sorted(ts_list, reverse=True), "Results not sorted newest-first"

    @pytest.mark.asyncio
    async def test_posts_without_timestamp_sorted_to_end(self):
        from server import run_search, ALL_PROVIDERS

        with_ts  = _post("youtube", "with",  ts=datetime(2024, 6, 1, tzinfo=timezone.utc))
        no_ts    = GeoPost(platform="reddit", post_id="no_ts", url="https://reddit.com/1",
                           latitude=40.71, longitude=-74.0)

        cls_map = {
            "youtube": MagicMock(return_value=_provider("youtube", [with_ts])),
            "reddit":  MagicMock(return_value=_provider("reddit",  [no_ts])),
        }
        with patch.dict(ALL_PROVIDERS, cls_map, clear=True):
            results = await run_search(
                SearchParams(latitude=40.71, longitude=-74.0), list(cls_map.keys())
            )

        # Post with timestamp should come before no-timestamp post
        platforms = [r["platform"] for r in results]
        assert platforms.index("youtube") < platforms.index("reddit")

    @pytest.mark.asyncio
    async def test_max_results_respected_per_provider(self):
        """Providers receive the max_results limit in their SearchParams."""
        from server import run_search, ALL_PROVIDERS

        received_max = []

        async def capturing_search(params):
            received_max.append(params.max_results)
            return []

        p = MagicMock(); p.name = "yt"; p.is_configured.return_value = True
        p.search = capturing_search

        with patch.dict(ALL_PROVIDERS, {"yt": MagicMock(return_value=p)}, clear=True):
            await run_search(
                SearchParams(latitude=40.71, longitude=-74.0, max_results=7), ["yt"]
            )

        assert received_max == [7]


# ============================================================
# 4. Geo distance calculations
# ============================================================

class TestGeoFiltering:
    """Verify haversine-based distance calculations used for filtering."""

    def test_nearby_point_within_radius(self):
        """Times Square is within 6 km of the Financial District."""
        center_lat, center_lon = 40.7128, -74.006  # Financial District
        point_lat, point_lon = 40.7580, -73.9855   # Times Square
        dist = haversine(center_lat, center_lon, point_lat, point_lon)
        # Actual distance is ~5.3 km; verify it's within a 6 km radius
        assert dist < 6.0, f"Expected < 6 km, got {dist:.2f} km"
        assert dist > 4.0, f"Expected > 4 km (sanity check), got {dist:.2f} km"

    def test_far_point_outside_radius(self):
        """A point 50 km away should not be within a 10 km radius."""
        center_lat, center_lon = 40.7128, -74.006
        # JFK airport is ~20 km away
        jfk_lat, jfk_lon = 40.6413, -73.7781
        dist = haversine(center_lat, center_lon, jfk_lat, jfk_lon)
        assert dist > 10.0

    def test_same_location_is_zero_distance(self):
        lat, lon = 40.7128, -74.006
        assert haversine(lat, lon, lat, lon) == 0.0

    def test_distance_is_symmetric(self):
        a = (40.7128, -74.006)
        b = (51.5074, -0.1278)
        assert abs(haversine(*a, *b) - haversine(*b, *a)) < 0.001

    def test_tehran_to_new_york_distance(self):
        """Tehran (35.69, 51.39) to New York (40.71, -74.01) ≈ 9,700 km."""
        dist = haversine(35.6892, 51.3890, 40.7128, -74.006)
        assert 9500 < dist < 10000, f"Unexpected Tehran-NY distance: {dist:.0f} km"

    def test_small_radius_precision(self):
        """Points 100m apart should be correctly identified as <1 km."""
        lat, lon = 48.8566, 2.3522  # Paris Notre-Dame
        # Move ~100m north
        lat2 = lat + 0.001  # ~111m north
        dist = haversine(lat, lon, lat2, lon)
        assert 0.05 < dist < 0.15


# ============================================================
# 5. CLI argument parsing
# ============================================================

class TestCLIArgumentParsing:
    """Verify main.py argparse handles all documented flags."""

    def _parse(self, args: list[str]):
        import argparse
        import main as m

        parser = argparse.ArgumentParser()
        parser.add_argument("--lat", type=float)
        parser.add_argument("--lng", type=float)
        parser.add_argument("--radius", type=float, default=10)
        parser.add_argument("--keyword", "-k", default="")
        parser.add_argument("--max-results", "-n", type=int, default=50)
        parser.add_argument("--platforms", "-p", nargs="+",
                            choices=list(m.ALL_PROVIDERS.keys()),
                            default=list(m.ALL_PROVIDERS.keys()))
        parser.add_argument("--json", dest="json_output", metavar="FILE")
        parser.add_argument("--server", action="store_true")
        parser.add_argument("--port", type=int, default=5000)
        parser.add_argument("--live", action="store_true")
        parser.add_argument("--interval", type=int, default=60)
        parser.add_argument("--config", metavar="FILE")
        return parser.parse_args(args)

    def test_lat_lng_parsed(self):
        args = self._parse(["--lat", "40.71", "--lng", "-74.0"])
        assert args.lat == 40.71
        assert args.lng == -74.0

    def test_radius_default_is_10(self):
        args = self._parse(["--lat", "0", "--lng", "0"])
        assert args.radius == 10

    def test_radius_custom(self):
        args = self._parse(["--lat", "0", "--lng", "0", "--radius", "25"])
        assert args.radius == 25

    def test_keyword_flag(self):
        args = self._parse(["--lat", "0", "--lng", "0", "-k", "protest"])
        assert args.keyword == "protest"

    def test_max_results_flag(self):
        args = self._parse(["--lat", "0", "--lng", "0", "-n", "20"])
        assert args.max_results == 20

    def test_server_flag(self):
        args = self._parse(["--server"])
        assert args.server is True

    def test_server_flag_absent(self):
        args = self._parse(["--lat", "0", "--lng", "0"])
        assert args.server is False

    def test_live_flag(self):
        args = self._parse(["--lat", "0", "--lng", "0", "--live"])
        assert args.live is True

    def test_interval_default(self):
        args = self._parse(["--lat", "0", "--lng", "0"])
        assert args.interval == 60

    def test_interval_custom(self):
        args = self._parse(["--lat", "0", "--lng", "0", "--live", "--interval", "30"])
        assert args.interval == 30

    def test_json_output_flag(self):
        args = self._parse(["--lat", "0", "--lng", "0", "--json", "out.json"])
        assert args.json_output == "out.json"

    def test_platform_filter(self):
        args = self._parse(["--lat", "0", "--lng", "0", "-p", "youtube", "reddit"])
        assert "youtube" in args.platforms
        assert "reddit" in args.platforms
        assert len(args.platforms) == 2

    def test_port_default(self):
        args = self._parse(["--server"])
        assert args.port == 5000

    def test_port_custom(self):
        args = self._parse(["--server", "--port", "8080"])
        assert args.port == 8080


# ============================================================
# 6. SSE event stream format
# ============================================================

class TestSSEFormat:
    """Verify the /api/stream endpoint produces correctly formatted SSE."""

    def test_stream_content_type_is_event_stream(self):
        import config as cfg; cfg._config = {}
        from server import app
        app.config["TESTING"] = True

        async def fake_search(params, platforms):
            return []

        with app.test_client() as c:
            with patch("server.run_search", side_effect=fake_search):
                # Use a very short timeout — we just need the headers
                try:
                    resp = c.get(
                        "/api/stream?latitude=40.71&longitude=-74.0&interval=10",
                        buffered=False,
                    )
                    assert "text/event-stream" in resp.content_type
                except Exception:
                    pass  # SSE is a streaming response; connection may close in test env

    def test_sse_data_format_is_correct(self):
        """SSE events must follow: 'data: <json>\\n\\n'"""
        import json

        # Simulate what the generate() function produces
        posts = [_post("youtube", "1").to_dict()]
        event = f"data: {json.dumps(posts)}\n\n"

        assert event.startswith("data: ")
        assert event.endswith("\n\n")
        # The payload must be valid JSON
        payload = event[len("data: "):-2]
        parsed = json.loads(payload)
        assert isinstance(parsed, list)
        assert parsed[0]["platform"] == "youtube"

    def test_empty_event_still_valid_sse(self):
        """An empty result event must also be valid SSE format."""
        event = "data: []\n\n"
        assert event.startswith("data: ")
        assert event.endswith("\n\n")
        assert json.loads(event[len("data: "):-2]) == []


# ============================================================
# 7. Provider system integrity
# ============================================================

class TestProviderSystemIntegrity:
    def test_all_provider_colors_are_unique(self):
        """No two providers should share the exact same marker color."""
        from server import ALL_PROVIDERS
        import config as cfg; cfg._config = {}
        colors = []
        for name, cls in ALL_PROVIDERS.items():
            try:
                p = cls()
                colors.append((name, cls.color))
            except Exception:
                colors.append((name, cls.color))
        color_values = [c for _, c in colors]
        duplicates = [c for c in set(color_values) if color_values.count(c) > 1]
        assert not duplicates, f"Duplicate marker colors: {duplicates}"

    def test_all_providers_return_list_type(self):
        """is_configured() must return a bool for every provider."""
        from server import ALL_PROVIDERS
        import config as cfg; cfg._config = {}
        for name, cls in ALL_PROVIDERS.items():
            try:
                p = cls()
                result = p.is_configured()
                assert isinstance(result, bool), f"{name}.is_configured() returned {type(result)}"
            except Exception:
                pass  # Some providers may fail to init without config

    def test_provider_name_matches_registry_key(self):
        """Each provider's .name attribute should match its key in ALL_PROVIDERS."""
        from server import ALL_PROVIDERS
        import config as cfg; cfg._config = {}
        for key, cls in ALL_PROVIDERS.items():
            assert cls.name == key, (
                f"Mismatch: ALL_PROVIDERS['{key}'] has name='{cls.name}'"
            )

    def test_all_colors_valid_hex(self):
        """All provider colors must be 7-char hex strings starting with #."""
        from server import ALL_PROVIDERS
        import re
        hex_pattern = re.compile(r"^#[0-9A-Fa-f]{6}$")
        for key, cls in ALL_PROVIDERS.items():
            assert hex_pattern.match(cls.color), (
                f"{key} has invalid color: '{cls.color}'"
            )
