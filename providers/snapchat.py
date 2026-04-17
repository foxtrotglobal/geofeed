"""Snapchat provider — scrapes Snap Map using Playwright headless browser.

Requires Playwright + Chromium AND Snapchat session cookies:
  pip install playwright
  playwright install chromium

Getting your Snapchat cookies:
  1. Log in to Snapchat in Chrome and visit https://map.snapchat.com/
  2. F12 -> Application -> Cookies -> https://map.snapchat.com
  3. Copy the value of 'sc-cookies-enabled' and any 'blizzard_sso' cookie
  4. Or: F12 -> Network -> any map.snapchat.com request -> Headers -> copy full 'cookie:' value
  5. Paste into config.yaml under snapchat.session_cookie
"""

from datetime import datetime, timezone

from geo import reverse_geocode
from models import GeoPost, SearchParams
from providers.base import BaseProvider
import config as cfg

SNAP_MAP_URL = "https://map.snapchat.com/"

STORY_PATTERNS = ["story", "stories", "nearby", "snap", "slide", "getsnaps", "map"]


class SnapchatProvider(BaseProvider):
    name = "snapchat"
    color = "#FFFC00"

    def __init__(self):
        self.session_cookie = cfg.get("snapchat", "session_cookie")

    def is_configured(self) -> bool:
        try:
            import playwright  # noqa: F401
            return bool(self.session_cookie)
        except ImportError:
            return False

    async def search(self, params: SearchParams) -> list[GeoPost]:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            print("[snapchat] playwright not installed. Run: pip install playwright && playwright install chromium")
            return []

        if not self.session_cookie:
            print("[snapchat] No session_cookie in config.yaml. See provider docstring for instructions.")
            return []

        place_name = await reverse_geocode(params.latitude, params.longitude)
        captured: list[dict] = []
        url = f"{SNAP_MAP_URL}?lng={params.longitude}&lat={params.latitude}&zoom=14"

        # Parse cookie string into Playwright cookie objects
        cookies = self._parse_cookies(self.session_cookie)

        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1280, "height": 800},
                )
                # Inject session cookies
                if cookies:
                    await context.add_cookies(cookies)

                page = await context.new_page()

                async def on_response(response):
                    resp_url = response.url.lower()
                    if "snapchat.com" not in resp_url:
                        return
                    if response.status != 200:
                        return
                    ct = response.headers.get("content-type", "")
                    if "json" not in ct:
                        return
                    if not any(pat in resp_url for pat in STORY_PATTERNS):
                        return
                    try:
                        data = await response.json()
                        if data:
                            captured.append({"url": response.url, "data": data})
                    except Exception:
                        pass

                page.on("response", on_response)

                await page.goto(url, wait_until="domcontentloaded", timeout=25000)
                await page.wait_for_timeout(5000)

                # Check if we ended up on the map (not redirected to login)
                current_url = page.url
                if "map.snapchat.com" not in current_url:
                    print(f"[snapchat] Redirected to {current_url[:60]} — cookies may be expired")
                    await browser.close()
                    return []

                # Click center of map to trigger story panel
                vp = page.viewport_size or {"width": 1280, "height": 800}
                await page.mouse.click(vp["width"] // 2, vp["height"] // 2)
                await page.wait_for_timeout(3000)

                await browser.close()

        except Exception as e:
            print(f"[snapchat] Playwright error: {e}")
            return []

        # Parse results
        posts = []
        seen: set = set()

        for entry in captured:
            data = entry["data"]
            items = self._extract_items(data)
            for item in items:
                post = self._parse_item(item, params, place_name)
                if post and post.post_id not in seen:
                    seen.add(post.post_id)
                    posts.append(post)

        return posts[:params.max_results]

    def _parse_cookies(self, cookie_string: str) -> list[dict]:
        """Convert a cookie header string into Playwright cookie dicts."""
        cookies = []
        for part in cookie_string.split(";"):
            part = part.strip()
            if "=" not in part:
                continue
            name, _, value = part.partition("=")
            name = name.strip()
            value = value.strip()
            if name:
                cookies.append({
                    "name": name,
                    "value": value,
                    "domain": ".snapchat.com",
                    "path": "/",
                })
        return cookies

    def _extract_items(self, data: dict) -> list:
        for key in ("stories", "elements", "snaps", "items", "liveSnaps", "data", "results"):
            val = data.get(key)
            if isinstance(val, list) and val:
                return val
        for val in data.values():
            if isinstance(val, list) and val and isinstance(val[0], dict):
                return val
        return []

    def _parse_item(self, item: dict, params: SearchParams, place_name: str):
        snap_id = str(item.get("id") or item.get("snapId") or item.get("storyId", ""))
        if not snap_id:
            return None

        title = item.get("title") or item.get("displayName") or item.get("locationName") or ""
        thumb = (item.get("thumbnailUrl") or item.get("previewUrl")
                 or item.get("mediaUrl") or item.get("coverUrl") or "")
        share_url = item.get("shareUrl") or item.get("url") or f"https://www.snapchat.com/add/story/{snap_id}"

        lat = item.get("lat") or item.get("latitude") or params.latitude
        lon = item.get("lng") or item.get("lon") or item.get("longitude") or params.longitude
        try:
            lat, lon = float(lat), float(lon)
        except (TypeError, ValueError):
            lat, lon = params.latitude, params.longitude

        place_info = item.get("placeInfo") or {}
        loc_name = ((place_info.get("name") if isinstance(place_info, dict) else None)
                    or item.get("locationName") or place_name)

        created_at = None
        ts = item.get("timestamp") or item.get("captureTimeSecs") or item.get("createTime")
        if ts:
            try:
                t = int(ts)
                created_at = datetime.fromtimestamp(t / 1000 if t > 1e10 else t, tz=timezone.utc)
            except (ValueError, TypeError, OSError):
                pass

        return GeoPost(
            platform="snapchat",
            post_id=snap_id,
            url=share_url,
            text=str(title)[:200],
            author="",
            latitude=lat,
            longitude=lon,
            location_name=loc_name,
            media_url=thumb,
            timestamp=created_at,
        )
