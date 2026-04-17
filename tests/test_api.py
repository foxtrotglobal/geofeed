"""Tests for Flask API endpoints (/api/search, /api/providers, /api/stream)."""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import GeoPost


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_post(platform: str, idx: int = 0, ts: str | None = None) -> GeoPost:
    return GeoPost(
        platform=platform,
        post_id=f"{platform}_{idx}",
        url=f"https://{platform}.com/{idx}",
        text=f"Test post {idx} from {platform}",
        author=f"user_{idx}",
        latitude=40.7128,
        longitude=-74.006,
        location_name="New York",
        timestamp=datetime.fromisoformat(ts) if ts else datetime(2024, 6, 15, 12, idx, tzinfo=timezone.utc),
    )


def _fake_posts(*platforms) -> list[dict]:
    posts = []
    for i, p in enumerate(platforms):
        posts.append(_fake_post(p, i).to_dict())
    return posts


# ---------------------------------------------------------------------------
# Flask test client fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """Create a Flask test client with config loaded."""
    import config as cfg
    cfg._config = {}  # Reset config to avoid stale state
    from server import app
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------

class TestIndexRoute:
    def test_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_returns_html(self, client):
        resp = client.get("/")
        assert b"GeoFeed" in resp.data or b"<!DOCTYPE" in resp.data

    def test_content_type_html(self, client):
        resp = client.get("/")
        assert "text/html" in resp.content_type


# ---------------------------------------------------------------------------
# GET /api/providers
# ---------------------------------------------------------------------------

class TestProvidersRoute:
    def test_returns_200(self, client):
        resp = client.get("/api/providers")
        assert resp.status_code == 200

    def test_returns_json(self, client):
        resp = client.get("/api/providers")
        data = json.loads(resp.data)
        assert isinstance(data, dict)

    def test_includes_all_expected_platforms(self, client):
        resp = client.get("/api/providers")
        data = json.loads(resp.data)
        expected = {"youtube", "flickr", "instagram", "twitter", "tiktok",
                    "bluesky", "mastodon", "snapchat", "facebook",
                    "telegram", "aparat", "rubika", "reddit"}
        assert expected.issubset(set(data.keys()))

    def test_each_provider_has_configured_and_color(self, client):
        resp = client.get("/api/providers")
        data = json.loads(resp.data)
        for name, info in data.items():
            assert "configured" in info, f"{name} missing 'configured'"
            assert "color" in info, f"{name} missing 'color'"

    def test_color_is_hex(self, client):
        resp = client.get("/api/providers")
        data = json.loads(resp.data)
        for name, info in data.items():
            color = info["color"]
            assert color.startswith("#"), f"{name} color not a hex: {color}"
            assert len(color) == 7, f"{name} color wrong length: {color}"


# ---------------------------------------------------------------------------
# POST /api/search
# ---------------------------------------------------------------------------

class TestSearchRoute:
    def test_returns_200_with_valid_payload(self, client):
        fake = _fake_posts("youtube", "reddit")
        with patch("server.run_search", new=AsyncMock(return_value=fake)):
            resp = client.post("/api/search",
                data=json.dumps({"latitude": 40.71, "longitude": -74.0, "radius_km": 5}),
                content_type="application/json")
        assert resp.status_code == 200

    def test_returns_posts_and_count(self, client):
        fake = _fake_posts("youtube", "bluesky")
        with patch("server.run_search", new=AsyncMock(return_value=fake)):
            resp = client.post("/api/search",
                data=json.dumps({"latitude": 40.71, "longitude": -74.0}),
                content_type="application/json")
        data = json.loads(resp.data)
        assert "posts" in data
        assert "count" in data
        assert data["count"] == 2
        assert len(data["posts"]) == 2

    def test_returns_400_on_empty_body(self, client):
        resp = client.post("/api/search", data="", content_type="application/json")
        assert resp.status_code == 400

    def test_returns_400_missing_latitude(self, client):
        resp = client.post("/api/search",
            data=json.dumps({"longitude": -74.0}),
            content_type="application/json")
        assert resp.status_code == 400

    def test_returns_400_missing_longitude(self, client):
        resp = client.post("/api/search",
            data=json.dumps({"latitude": 40.71}),
            content_type="application/json")
        assert resp.status_code == 400

    def test_returns_400_invalid_type(self, client):
        resp = client.post("/api/search",
            data=json.dumps({"latitude": "not_a_float", "longitude": -74.0}),
            content_type="application/json")
        assert resp.status_code == 400

    def test_default_radius_applied(self, client):
        captured_params = []

        async def fake_search(params, platforms):
            captured_params.append(params)
            return []

        with patch("server.run_search", side_effect=fake_search):
            client.post("/api/search",
                data=json.dumps({"latitude": 40.71, "longitude": -74.0}),
                content_type="application/json")
        assert captured_params[0].radius_km == 10.0

    def test_platform_filter_passed_to_run_search(self, client):
        captured = {}

        async def fake_search(params, platforms):
            captured["platforms"] = platforms
            return []

        with patch("server.run_search", side_effect=fake_search):
            client.post("/api/search",
                data=json.dumps({
                    "latitude": 40.71,
                    "longitude": -74.0,
                    "platforms": ["youtube", "reddit"],
                }),
                content_type="application/json")
        assert captured["platforms"] == ["youtube", "reddit"]

    def test_keyword_passed_to_search(self, client):
        captured = {}

        async def fake_search(params, platforms):
            captured["keyword"] = params.keyword
            return []

        with patch("server.run_search", side_effect=fake_search):
            client.post("/api/search",
                data=json.dumps({
                    "latitude": 40.71, "longitude": -74.0,
                    "keyword": "protest",
                }),
                content_type="application/json")
        assert captured["keyword"] == "protest"

    def test_results_sorted_newest_first(self, client):
        posts = [
            _fake_post("youtube", 0, "2024-01-01T00:00:00+00:00").to_dict(),
            _fake_post("reddit",  1, "2024-06-15T00:00:00+00:00").to_dict(),
            _fake_post("twitter", 2, "2024-03-10T00:00:00+00:00").to_dict(),
        ]
        # run_search already sorts; pass pre-sorted to verify API preserves order
        sorted_posts = sorted(posts, key=lambda p: p.get("timestamp") or "", reverse=True)
        with patch("server.run_search", new=AsyncMock(return_value=sorted_posts)):
            resp = client.post("/api/search",
                data=json.dumps({"latitude": 40.71, "longitude": -74.0}),
                content_type="application/json")
        data = json.loads(resp.data)
        timestamps = [p["timestamp"] for p in data["posts"]]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_empty_results_returns_zero_count(self, client):
        with patch("server.run_search", new=AsyncMock(return_value=[])):
            resp = client.post("/api/search",
                data=json.dumps({"latitude": 40.71, "longitude": -74.0}),
                content_type="application/json")
        data = json.loads(resp.data)
        assert data["count"] == 0
        assert data["posts"] == []


# ---------------------------------------------------------------------------
# GET /api/stream
# ---------------------------------------------------------------------------

class TestStreamRoute:
    def test_stream_route_exists(self, client):
        # Just check it responds, not blocking forever
        # We can't fully test SSE in unit tests, but we verify the route exists
        resp = client.get(
            "/api/stream?latitude=40.71&longitude=-74.0",
            buffered=False,
        )
        # Either 200 (streaming) or error about missing params — not 404
        assert resp.status_code != 404

    def test_stream_returns_400_without_coords(self, client):
        resp = client.get("/api/stream")
        assert resp.status_code in (400, 500)  # Missing required params
