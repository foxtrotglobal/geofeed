"""Tests for all platform providers using mocked HTTP responses."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models import SearchParams

PARAMS = SearchParams(latitude=40.7128, longitude=-74.006, radius_km=10, keyword="test")


# ============================================================
# Helpers
# ============================================================


def _mock_http_response(json_data: dict, status_code: int = 200):
    """Create a mock httpx response (json() and raise_for_status() are sync in httpx)."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    return resp


def _mock_async_client(response):
    """Create a mock httpx.AsyncClient that returns `response` for get/post."""
    client = AsyncMock()
    client.get.return_value = response
    client.post.return_value = response
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return client


# ============================================================
# YouTube
# ============================================================


class TestYouTubeProvider:
    @pytest.mark.asyncio
    async def test_search_returns_posts(self):
        from providers.youtube import YouTubeProvider

        api_response = {
            "items": [
                {
                    "id": {"videoId": "vid123"},
                    "snippet": {
                        "title": "NYC Street View",
                        "channelTitle": "TestChannel",
                        "publishedAt": "2024-06-15T10:30:00Z",
                        "description": "A walk through NYC",
                        "thumbnails": {"medium": {"url": "https://img.youtube.com/thumb.jpg"}},
                    },
                }
            ]
        }

        mock_client = _mock_async_client(_mock_http_response(api_response))
        with patch("providers.youtube.config") as mock_config, \
             patch("providers.youtube.httpx.AsyncClient", return_value=mock_client):
            mock_config.get.return_value = "fake_api_key"
            provider = YouTubeProvider()
            posts = await provider.search(PARAMS)

        assert len(posts) == 1
        assert posts[0].platform == "youtube"
        assert posts[0].post_id == "vid123"
        assert posts[0].text == "NYC Street View"
        assert posts[0].author == "TestChannel"
        assert posts[0].url == "https://www.youtube.com/watch?v=vid123"
        assert posts[0].media_url == "https://img.youtube.com/thumb.jpg"
        assert posts[0].timestamp == datetime(2024, 6, 15, 10, 30, tzinfo=timezone.utc)

    @pytest.mark.asyncio
    async def test_search_empty_results(self):
        from providers.youtube import YouTubeProvider

        mock_client = _mock_async_client(_mock_http_response({"items": []}))
        with patch("providers.youtube.config") as mock_config, \
             patch("providers.youtube.httpx.AsyncClient", return_value=mock_client):
            mock_config.get.return_value = "fake_key"
            provider = YouTubeProvider()
            posts = await provider.search(PARAMS)

        assert posts == []

    def test_not_configured_without_key(self):
        from providers.youtube import YouTubeProvider

        with patch("providers.youtube.config") as mock_config:
            mock_config.get.return_value = ""
            provider = YouTubeProvider()
            assert provider.is_configured() is False

    def test_configured_with_key(self):
        from providers.youtube import YouTubeProvider

        with patch("providers.youtube.config") as mock_config:
            mock_config.get.return_value = "some_key"
            provider = YouTubeProvider()
            assert provider.is_configured() is True


# ============================================================
# Flickr
# ============================================================


class TestFlickrProvider:
    @pytest.mark.asyncio
    async def test_search_returns_posts(self):
        from providers.flickr import FlickrProvider

        api_response = {
            "photos": {
                "photo": [
                    {
                        "id": "photo456",
                        "owner": "user1",
                        "title": "Sunset in Manhattan",
                        "ownername": "PhotoUser",
                        "latitude": "40.7128",
                        "longitude": "-74.006",
                        "url_m": "https://flickr.com/photo.jpg",
                        "datetaken": "2024-03-10 18:45:00",
                        "description": {"_content": "Beautiful sunset"},
                    }
                ]
            }
        }

        mock_client = _mock_async_client(_mock_http_response(api_response))
        with patch("providers.flickr.config") as mock_config, \
             patch("providers.flickr.httpx.AsyncClient", return_value=mock_client):
            mock_config.get.return_value = "fake_flickr_key"
            provider = FlickrProvider()
            posts = await provider.search(PARAMS)

        assert len(posts) == 1
        assert posts[0].platform == "flickr"
        assert posts[0].post_id == "photo456"
        assert posts[0].text == "Sunset in Manhattan"
        assert posts[0].author == "PhotoUser"
        assert posts[0].latitude == 40.7128
        assert posts[0].media_url == "https://flickr.com/photo.jpg"
        assert posts[0].distance_km is not None
        assert posts[0].distance_km < 0.01  # Same point

    @pytest.mark.asyncio
    async def test_search_handles_missing_geo(self):
        from providers.flickr import FlickrProvider

        api_response = {
            "photos": {
                "photo": [
                    {
                        "id": "photo789",
                        "owner": "user2",
                        "title": "No location",
                        "latitude": "0",
                        "longitude": "0",
                        "description": {"_content": ""},
                    }
                ]
            }
        }

        mock_client = _mock_async_client(_mock_http_response(api_response))
        with patch("providers.flickr.config") as mock_config, \
             patch("providers.flickr.httpx.AsyncClient", return_value=mock_client):
            mock_config.get.return_value = "key"
            provider = FlickrProvider()
            posts = await provider.search(PARAMS)

        assert len(posts) == 1
        assert posts[0].latitude is None  # 0 → None
        assert posts[0].distance_km is None


# ============================================================
# Instagram
# ============================================================


class TestInstagramProvider:
    @pytest.mark.asyncio
    async def test_search_finds_locations_and_posts(self):
        from providers.instagram import InstagramProvider

        location_response = _mock_http_response({
            "venues": [
                {
                    "external_id": "loc100",
                    "name": "Times Square",
                    "lat": 40.758,
                    "lng": -73.9855,
                }
            ]
        })

        post_response = _mock_http_response({
            "sections": [
                {
                    "layout_content": {
                        "medias": [
                            {
                                "media": {
                                    "pk": "m1",
                                    "code": "ABC123",
                                    "taken_at": 1718450000,
                                    "user": {"username": "insta_user"},
                                    "caption": {"text": "Times Square vibes"},
                                    "image_versions2": {
                                        "candidates": [{"url": "https://instagram.com/thumb.jpg"}]
                                    },
                                }
                            }
                        ]
                    }
                }
            ]
        })

        # First call = location search (GET), second call = location feed (POST)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=location_response)
        mock_client.post = AsyncMock(return_value=post_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("providers.instagram.config") as mock_config, \
             patch("providers.instagram.httpx.AsyncClient", return_value=mock_client):
            mock_config.get.return_value = "fake_cookie=abc123"
            provider = InstagramProvider()
            posts = await provider.search(PARAMS)

        assert len(posts) == 1
        assert posts[0].platform == "instagram"
        assert posts[0].author == "insta_user"
        assert posts[0].location_name == "Times Square"
        assert "ABC123" in posts[0].url

    @pytest.mark.asyncio
    async def test_search_returns_empty_on_no_locations(self):
        from providers.instagram import InstagramProvider

        mock_client = _mock_async_client(_mock_http_response({"venues": []}))
        with patch("providers.instagram.config") as mock_config, \
             patch("providers.instagram.httpx.AsyncClient", return_value=mock_client):
            mock_config.get.return_value = "cookie=val"
            provider = InstagramProvider()
            posts = await provider.search(PARAMS)

        assert posts == []

    @pytest.mark.asyncio
    async def test_search_returns_empty_on_api_error(self):
        from providers.instagram import InstagramProvider

        error_resp = _mock_http_response({}, status_code=401)
        mock_client = _mock_async_client(error_resp)

        with patch("providers.instagram.config") as mock_config, \
             patch("providers.instagram.httpx.AsyncClient", return_value=mock_client):
            mock_config.get.return_value = "expired_cookie"
            provider = InstagramProvider()
            posts = await provider.search(PARAMS)

        assert posts == []

    def test_not_configured_without_cookie(self):
        from providers.instagram import InstagramProvider

        with patch("providers.instagram.config") as mock_config:
            mock_config.get.return_value = ""
            assert InstagramProvider().is_configured() is False


# ============================================================
# Twitter
# ============================================================


class TestTwitterProvider:
    @pytest.mark.asyncio
    async def test_search_returns_posts(self):
        from providers.twitter import TwitterProvider

        api_response = {
            "data": [
                {
                    "id": "tw001",
                    "text": "Hello from NYC!",
                    "author_id": "u1",
                    "created_at": "2024-06-15T12:00:00Z",
                    "geo": {
                        "place_id": "p1",
                        "coordinates": {"coordinates": [-74.006, 40.7128]},
                    },
                }
            ],
            "includes": {
                "users": [{"id": "u1", "username": "nycperson"}],
                "places": [
                    {
                        "id": "p1",
                        "full_name": "Manhattan, NY",
                        "geo": {"bbox": [-74.05, 40.68, -73.91, 40.88]},
                    }
                ],
            },
        }

        mock_client = _mock_async_client(_mock_http_response(api_response))
        with patch("providers.twitter.config") as mock_config, \
             patch("providers.twitter.httpx.AsyncClient", return_value=mock_client):
            mock_config.get.return_value = "fake_bearer_token"
            provider = TwitterProvider()
            posts = await provider.search(PARAMS)

        assert len(posts) == 1
        assert posts[0].platform == "twitter"
        assert posts[0].post_id == "tw001"
        assert posts[0].text == "Hello from NYC!"
        assert posts[0].author == "nycperson"
        assert posts[0].latitude == 40.7128
        assert posts[0].longitude == -74.006
        assert posts[0].location_name == "Manhattan, NY"

    @pytest.mark.asyncio
    async def test_search_uses_bbox_centroid_when_no_coordinates(self):
        from providers.twitter import TwitterProvider

        api_response = {
            "data": [
                {
                    "id": "tw002",
                    "text": "No exact coords",
                    "author_id": "u2",
                    "geo": {"place_id": "p2"},
                }
            ],
            "includes": {
                "users": [{"id": "u2", "username": "someone"}],
                "places": [
                    {
                        "id": "p2",
                        "full_name": "Brooklyn, NY",
                        "geo": {"bbox": [-74.0, 40.6, -73.8, 40.7]},
                    }
                ],
            },
        }

        mock_client = _mock_async_client(_mock_http_response(api_response))
        with patch("providers.twitter.config") as mock_config, \
             patch("providers.twitter.httpx.AsyncClient", return_value=mock_client):
            mock_config.get.return_value = "bearer"
            provider = TwitterProvider()
            posts = await provider.search(PARAMS)

        assert len(posts) == 1
        # Centroid of bbox
        assert posts[0].latitude == pytest.approx(40.65, abs=0.01)
        assert posts[0].longitude == pytest.approx(-73.9, abs=0.01)

    @pytest.mark.asyncio
    async def test_search_returns_empty_on_403(self):
        from providers.twitter import TwitterProvider

        error_resp = _mock_http_response({}, status_code=403)
        mock_client = _mock_async_client(error_resp)

        with patch("providers.twitter.config") as mock_config, \
             patch("providers.twitter.httpx.AsyncClient", return_value=mock_client):
            mock_config.get.return_value = "free_tier_token"
            provider = TwitterProvider()
            posts = await provider.search(PARAMS)

        assert posts == []


# ============================================================
# TikTok
# ============================================================


class TestTikTokProvider:
    @pytest.mark.asyncio
    async def test_search_returns_posts(self):
        from providers.tiktok import TikTokProvider

        api_response = {
            "data": [
                {
                    "item": {
                        "id": "tt789",
                        "desc": "Dancing in NYC #newyork",
                        "author": {"uniqueId": "tiktoker"},
                        "createTime": "1718450000",
                        "video": {"cover": "https://tiktok.com/cover.jpg"},
                    }
                }
            ]
        }

        mock_client = _mock_async_client(_mock_http_response(api_response))
        with patch("providers.tiktok.config") as mock_config, \
             patch("providers.tiktok.reverse_geocode", return_value="New York") as mock_geo, \
             patch("providers.tiktok.httpx.AsyncClient", return_value=mock_client):
            mock_config.get.return_value = ""
            provider = TikTokProvider()
            posts = await provider.search(PARAMS)

        mock_geo.assert_awaited_once_with(40.7128, -74.006)
        assert len(posts) == 1
        assert posts[0].platform == "tiktok"
        assert posts[0].post_id == "tt789"
        assert posts[0].author == "tiktoker"
        assert posts[0].location_name == "New York"
        assert "tiktoker" in posts[0].url

    @pytest.mark.asyncio
    async def test_search_handles_non_200(self):
        from providers.tiktok import TikTokProvider

        error_resp = _mock_http_response({}, status_code=429)
        mock_client = _mock_async_client(error_resp)

        with patch("providers.tiktok.config") as mock_config, \
             patch("providers.tiktok.reverse_geocode", return_value="Test City"), \
             patch("providers.tiktok.httpx.AsyncClient", return_value=mock_client):
            mock_config.get.return_value = ""
            provider = TikTokProvider()
            posts = await provider.search(PARAMS)

        assert posts == []

    @pytest.mark.asyncio
    async def test_search_handles_exception_gracefully(self):
        from providers.tiktok import TikTokProvider

        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Network error")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("providers.tiktok.config") as mock_config, \
             patch("providers.tiktok.reverse_geocode", return_value="Somewhere"), \
             patch("providers.tiktok.httpx.AsyncClient", return_value=mock_client):
            mock_config.get.return_value = ""
            provider = TikTokProvider()
            posts = await provider.search(PARAMS)

        assert posts == []

    def test_always_configured(self):
        from providers.tiktok import TikTokProvider

        with patch("providers.tiktok.config") as mock_config:
            mock_config.get.return_value = ""
            assert TikTokProvider().is_configured() is True


# ============================================================
# Bluesky
# ============================================================


class TestBlueskyProvider:
    @pytest.mark.asyncio
    async def test_search_returns_posts(self):
        from providers.bluesky import BlueskyProvider

        api_response = {
            "posts": [
                {
                    "uri": "at://did:plc:abc/app.bsky.feed.post/rkey123",
                    "record": {"text": "Hello from New York!", "createdAt": "2024-06-15T10:00:00Z"},
                    "author": {"handle": "user.bsky.social"},
                    "indexedAt": "2024-06-15T10:00:00Z",
                    "embed": {"images": [{"thumb": "https://bsky.app/thumb.jpg"}]},
                }
            ]
        }

        mock_client = _mock_async_client(_mock_http_response(api_response))
        with patch("providers.bluesky.config") as mock_config, \
             patch("providers.bluesky.reverse_geocode", return_value="New York"), \
             patch("providers.bluesky.httpx.AsyncClient", return_value=mock_client):
            mock_config.get.return_value = ""
            provider = BlueskyProvider()
            posts = await provider.search(PARAMS)

        assert len(posts) == 1
        assert posts[0].platform == "bluesky"
        assert posts[0].author == "user.bsky.social"
        assert posts[0].text == "Hello from New York!"
        assert "user.bsky.social" in posts[0].url
        assert "rkey123" in posts[0].url
        assert posts[0].media_url == "https://bsky.app/thumb.jpg"

    @pytest.mark.asyncio
    async def test_search_returns_empty_on_error(self):
        from providers.bluesky import BlueskyProvider

        mock_client = _mock_async_client(_mock_http_response({}, status_code=500))
        with patch("providers.bluesky.config") as mock_config, \
             patch("providers.bluesky.reverse_geocode", return_value="Paris"), \
             patch("providers.bluesky.httpx.AsyncClient", return_value=mock_client):
            mock_config.get.return_value = ""
            posts = await BlueskyProvider().search(PARAMS)

        assert posts == []

    def test_always_configured(self):
        from providers.bluesky import BlueskyProvider

        with patch("providers.bluesky.config") as mock_config:
            mock_config.get.return_value = ""
            assert BlueskyProvider().is_configured() is True


# ============================================================
# Mastodon
# ============================================================


class TestMastodonProvider:
    @pytest.mark.asyncio
    async def test_search_returns_posts(self):
        from providers.mastodon import MastodonProvider

        # Mastodon now uses the hashtag timeline (returns a list, not dict)
        api_response = [
            {
                "id": "mast001",
                "content": "<p>Testing in <a href='#'>New York</a></p>",
                "url": "https://mastodon.social/@user/mast001",
                "created_at": "2024-06-15T09:00:00Z",
                "account": {"acct": "user@mastodon.social"},
                "media_attachments": [
                    {"type": "image", "preview_url": "https://mastodon.social/preview.jpg"}
                ],
            }
        ]

        mock_client = _mock_async_client(_mock_http_response(api_response))
        with patch("providers.mastodon.config") as mock_config, \
             patch("providers.mastodon.reverse_geocode", return_value="New York"), \
             patch("providers.mastodon.httpx.AsyncClient", return_value=mock_client):
            mock_config.get.return_value = ""
            provider = MastodonProvider()
            posts = await provider.search(PARAMS)

        assert len(posts) == 1
        assert posts[0].platform == "mastodon"
        assert posts[0].post_id == "mast001"
        assert posts[0].author == "user@mastodon.social"
        assert "Testing in" in posts[0].text
        assert "<p>" not in posts[0].text
        assert posts[0].media_url == "https://mastodon.social/preview.jpg"

    @pytest.mark.asyncio
    async def test_search_strips_html(self):
        from providers.mastodon import MastodonProvider

        api_response = [
            {
                "id": "mast002",
                "content": "<p><strong>Bold</strong> and <em>italic</em> text.</p>",
                "url": "",
                "account": {"acct": "tester"},
                "media_attachments": [],
            }
        ]

        mock_client = _mock_async_client(_mock_http_response(api_response))
        with patch("providers.mastodon.config") as mock_config, \
             patch("providers.mastodon.reverse_geocode", return_value="Somewhere"), \
             patch("providers.mastodon.httpx.AsyncClient", return_value=mock_client):
            mock_config.get.return_value = ""
            posts = await MastodonProvider().search(PARAMS)

        assert "<" not in posts[0].text
        assert "Bold" in posts[0].text

    def test_always_configured(self):
        from providers.mastodon import MastodonProvider

        with patch("providers.mastodon.config") as mock_config:
            mock_config.get.return_value = ""
            assert MastodonProvider().is_configured() is True


# ============================================================
# Snapchat
# ============================================================


class TestSnapchatProvider:
    @pytest.mark.asyncio
    async def test_search_returns_posts(self):
        from providers.snapchat import SnapchatProvider

        api_response = {
            "elements": [
                {
                    "id": "snap001",
                    "title": "Times Square",
                    "timestamp": "1718450000000",
                    "location": {"lat": 40.758, "lng": -73.9855},
                    "placeInfo": {"name": "Times Square, NY"},
                    "snapInfo": {
                        "previewImageMediaInfo": {"mediaUrl": "https://snap.com/preview.jpg"}
                    },
                }
            ]
        }

        mock_client = _mock_async_client(_mock_http_response(api_response))
        with patch("providers.snapchat.httpx.AsyncClient", return_value=mock_client):
            provider = SnapchatProvider()
            posts = await provider.search(PARAMS)

        assert len(posts) == 1
        assert posts[0].platform == "snapchat"
        assert posts[0].post_id == "snap001"
        assert posts[0].location_name == "Times Square, NY"
        assert posts[0].latitude == pytest.approx(40.758)

    @pytest.mark.asyncio
    async def test_search_handles_non_200(self):
        from providers.snapchat import SnapchatProvider

        mock_client = _mock_async_client(_mock_http_response({}, status_code=403))
        with patch("providers.snapchat.httpx.AsyncClient", return_value=mock_client):
            posts = await SnapchatProvider().search(PARAMS)

        assert posts == []

    def test_always_configured(self):
        from providers.snapchat import SnapchatProvider
        assert SnapchatProvider().is_configured() is True


# ============================================================
# Facebook
# ============================================================


class TestFacebookProvider:
    @pytest.mark.asyncio
    async def test_search_finds_places_and_posts(self):
        from providers.facebook import FacebookProvider

        places_response = _mock_http_response({
            "data": [
                {
                    "id": "place001",
                    "name": "Central Park",
                    "location": {"latitude": 40.7851, "longitude": -73.9683},
                }
            ]
        })

        posts_response = _mock_http_response({
            "data": [
                {
                    "id": "place001_post999",
                    "message": "Beautiful day in Central Park!",
                    "created_time": "2024-06-15T14:00:00+0000",
                    "attachments": {"data": [{"media": {"image": {"src": "https://fb.com/img.jpg"}}}]},
                }
            ]
        })

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=[places_response, posts_response])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("providers.facebook.config") as mock_config, \
             patch("providers.facebook.httpx.AsyncClient", return_value=mock_client):
            mock_config.get.side_effect = lambda s, k: "fake_id" if k == "app_id" else "fake_secret"
            provider = FacebookProvider()
            posts = await provider.search(PARAMS)

        assert len(posts) == 1
        assert posts[0].platform == "facebook"
        assert posts[0].author == "Central Park"
        assert posts[0].text == "Beautiful day in Central Park!"
        assert posts[0].media_url == "https://fb.com/img.jpg"

    @pytest.mark.asyncio
    async def test_search_returns_empty_when_no_places(self):
        from providers.facebook import FacebookProvider

        mock_client = _mock_async_client(_mock_http_response({"data": []}))
        with patch("providers.facebook.config") as mock_config, \
             patch("providers.facebook.httpx.AsyncClient", return_value=mock_client):
            mock_config.get.side_effect = lambda s, k: "id" if k == "app_id" else "secret"
            posts = await FacebookProvider().search(PARAMS)

        assert posts == []

    def test_not_configured_without_credentials(self):
        from providers.facebook import FacebookProvider

        with patch("providers.facebook.config") as mock_config:
            mock_config.get.return_value = ""
            assert FacebookProvider().is_configured() is False

    def test_configured_with_credentials(self):
        from providers.facebook import FacebookProvider

        with patch("providers.facebook.config") as mock_config:
            mock_config.get.side_effect = lambda s, k: "val"
            assert FacebookProvider().is_configured() is True


# ============================================================
# Telegram
# ============================================================


class TestTelegramProvider:
    @pytest.mark.asyncio
    async def test_search_returns_matching_posts(self):
        from providers.telegram import TelegramProvider

        # Simulate a t.me/s/channel HTML page with one matching message
        html = '''
        <div data-post="bbcpersian/999" class="tgme_widget_message">
          <div class="tgme_widget_message_text js-message_text">Tehran protests today</div>
          <time class="time" datetime="2024-06-15T10:00:00+00:00">10:00</time>
        </div>
        '''
        resp = MagicMock()
        resp.status_code = 200
        resp.text = html

        client = AsyncMock()
        client.get.return_value = resp
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)

        with patch("providers.telegram.config") as mock_config, \
             patch("providers.telegram.reverse_geocode", return_value="Tehran"), \
             patch("providers.telegram.httpx.AsyncClient", return_value=client):
            mock_config.get.return_value = ""
            provider = TelegramProvider()
            provider.channels = ["bbcpersian"]
            posts = await provider.search(PARAMS)

        assert len(posts) == 1
        assert posts[0].platform == "telegram"
        assert posts[0].author == "@bbcpersian"
        assert "Tehran" in posts[0].text

    @pytest.mark.asyncio
    async def test_search_includes_recent_posts_when_no_keyword_match(self):
        """When no posts match the location keyword, recent posts are still returned
        so the channel shows something rather than nothing."""
        from providers.telegram import TelegramProvider

        html = '''
        <div data-post="bbcpersian/1" class="tgme_widget_message">
          <div class="tgme_widget_message_text js-message_text">Unrelated content about sports</div>
          <time datetime="2024-06-15T10:00:00+00:00">10:00</time>
        </div>
        '''
        resp = MagicMock()
        resp.status_code = 200
        resp.text = html

        client = AsyncMock()
        client.get.return_value = resp
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)

        with patch("providers.telegram.config") as mock_config, \
             patch("providers.telegram.reverse_geocode", return_value="Tehran"), \
             patch("providers.telegram.httpx.AsyncClient", return_value=client):
            mock_config.get.return_value = ""
            provider = TelegramProvider()
            provider.channels = ["bbcpersian"]
            posts = await provider.search(PARAMS)

        # Non-matching posts are now included when total matches < 5
        assert len(posts) == 1
        assert posts[0].platform == "telegram"

    def test_always_configured(self):
        from providers.telegram import TelegramProvider

        with patch("providers.telegram.config") as mock_config:
            mock_config.get.return_value = ""
            assert TelegramProvider().is_configured() is True


# ============================================================
# Aparat
# ============================================================


class TestAparatProvider:
    @pytest.mark.asyncio
    async def test_search_returns_posts(self):
        from providers.aparat import AparatProvider

        api_response = {
            "data": [
                {
                    "id": "abc123",
                    "attributes": {
                        "title": "Tehran street view",
                        "username": "iranvlogger",
                        "big_poster": "https://aparat.com/thumb.jpg",
                        "create_date": "2024-06-15T12:00:00",
                    },
                }
            ]
        }

        mock_client = _mock_async_client(_mock_http_response(api_response))
        with patch("providers.aparat.reverse_geocode", return_value="Tehran"), \
             patch("providers.aparat.httpx.AsyncClient", return_value=mock_client):
            provider = AparatProvider()
            posts = await provider.search(PARAMS)

        assert len(posts) == 1
        assert posts[0].platform == "aparat"
        assert posts[0].text == "Tehran street view"
        assert posts[0].author == "iranvlogger"
        assert posts[0].url == "https://www.aparat.com/v/abc123"

    @pytest.mark.asyncio
    async def test_search_returns_empty_on_error(self):
        from providers.aparat import AparatProvider

        mock_client = _mock_async_client(_mock_http_response({}, status_code=503))
        with patch("providers.aparat.reverse_geocode", return_value="Tehran"), \
             patch("providers.aparat.httpx.AsyncClient", return_value=mock_client):
            posts = await AparatProvider().search(PARAMS)

        assert posts == []

    def test_always_configured(self):
        from providers.aparat import AparatProvider
        assert AparatProvider().is_configured() is True


# ============================================================
# Rubika
# ============================================================


class TestRubikaProvider:
    @pytest.mark.asyncio
    async def test_search_returns_posts_from_api(self):
        from providers.rubika import RubikaProvider

        api_response = {
            "posts": [
                {
                    "id": "rub001",
                    "text": "Tehran news today",
                    "author": {"username": "rubikauser"},
                    "thumbnail": "https://rubika.ir/thumb.jpg",
                    "created_at": "2024-06-15T10:00:00",
                }
            ]
        }

        mock_client = _mock_async_client(_mock_http_response(api_response))
        with patch("providers.rubika.reverse_geocode", return_value="Tehran"), \
             patch("providers.rubika.httpx.AsyncClient", return_value=mock_client):
            posts = await RubikaProvider().search(PARAMS)

        assert len(posts) == 1
        assert posts[0].platform == "rubika"
        assert posts[0].post_id == "rub001"
        assert posts[0].author == "rubikauser"

    @pytest.mark.asyncio
    async def test_search_returns_empty_gracefully(self):
        from providers.rubika import RubikaProvider

        mock_client = _mock_async_client(_mock_http_response({}, status_code=404))
        with patch("providers.rubika.reverse_geocode", return_value="Tehran"), \
             patch("providers.rubika.httpx.AsyncClient", return_value=mock_client):
            posts = await RubikaProvider().search(PARAMS)

        assert posts == []

    def test_always_configured(self):
        from providers.rubika import RubikaProvider
        assert RubikaProvider().is_configured() is True


# ============================================================
# Reddit
# ============================================================


class TestRedditProvider:
    @pytest.mark.asyncio
    async def test_search_returns_posts(self):
        from providers.reddit import RedditProvider

        api_response = {
            "data": {
                "children": [
                    {
                        "data": {
                            "id": "red001",
                            "title": "Protests in Tehran today",
                            "selftext": "Large crowds gathered...",
                            "author": "redditor99",
                            "subreddit": "iran",
                            "permalink": "/r/iran/comments/red001/",
                            "thumbnail": "https://reddit.com/thumb.jpg",
                            "created_utc": 1718450000.0,
                        }
                    }
                ]
            }
        }

        mock_client = _mock_async_client(_mock_http_response(api_response))
        with patch("providers.reddit.config") as mock_config, \
             patch("providers.reddit.reverse_geocode", return_value="Tehran"), \
             patch("providers.reddit.httpx.AsyncClient", return_value=mock_client):
            mock_config.get.return_value = ""
            provider = RedditProvider()
            provider.subreddits = []  # Skip subreddit searches in this test
            posts = await provider.search(PARAMS)

        assert len(posts) == 1
        assert posts[0].platform == "reddit"
        assert posts[0].post_id == "red001"
        assert posts[0].author == "u/redditor99"
        assert "Tehran" in posts[0].text
        assert posts[0].url == "https://www.reddit.com/r/iran/comments/red001/"

    @pytest.mark.asyncio
    async def test_search_handles_rate_limit(self):
        from providers.reddit import RedditProvider

        mock_client = _mock_async_client(_mock_http_response({}, status_code=429))
        with patch("providers.reddit.config") as mock_config, \
             patch("providers.reddit.reverse_geocode", return_value="Tehran"), \
             patch("providers.reddit.httpx.AsyncClient", return_value=mock_client):
            mock_config.get.return_value = ""
            provider = RedditProvider()
            provider.subreddits = []
            posts = await provider.search(PARAMS)

        assert posts == []

    def test_always_configured(self):
        from providers.reddit import RedditProvider

        with patch("providers.reddit.config") as mock_config:
            mock_config.get.return_value = ""
            assert RedditProvider().is_configured() is True
