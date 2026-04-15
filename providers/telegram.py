"""Telegram provider — scrapes public Telegram channels via t.me/s/.

Searches a curated list of public Middle East / Iran channels plus any
user-configured channels, filtering messages that mention the location name.
No API key required. Optionally provide a Bot token for extended channel lookup.

To add custom channels, set `channels` in config.yaml:
  telegram:
    channels:
      - irna_ir
      - isna_farsi
      - mychannel
"""

import re
from datetime import datetime, timezone
from html import unescape

import httpx

import config
from geo import reverse_geocode
from models import GeoPost, SearchParams
from providers.base import BaseProvider

# Curated public Middle East / Iran channels (no login required)
DEFAULT_CHANNELS = [
    "irna_ir",          # Islamic Republic News Agency
    "isna_farsi",       # Iranian Students' News Agency
    "mehr_farsi",       # Mehr News Agency
    "tasnim_fa",        # Tasnim News Agency
    "bbcpersian",       # BBC Persian
    "VOApersian",       # Voice of America Persian
    "irdiplomacy",      # Iranian Diplomacy
    "iran_press",       # Iran Press News
    "aljazeera_ar",     # Al Jazeera Arabic
    "alarabiya_news",   # Al Arabiya News
]

CHANNEL_URL = "https://t.me/s/{channel}"
_TAG_RE = re.compile(r"<[^>]+>")
_MSG_RE = re.compile(
    r'tgme_widget_message_text[^>]*>(.*?)</div>',
    re.DOTALL,
)
_TIME_RE = re.compile(r'datetime="([^"]+)"')
_MSG_ID_RE = re.compile(r'data-post="([^"]+)"')


class TelegramProvider(BaseProvider):
    name = "telegram"
    color = "#2CA5E0"

    def __init__(self):
        self.bot_token = config.get("telegram", "bot_token")
        custom = config.get("telegram", "channels")
        if isinstance(custom, list):
            self.channels = custom
        elif custom:
            self.channels = [c.strip() for c in custom.split(",") if c.strip()]
        else:
            self.channels = list(DEFAULT_CHANNELS)

    def is_configured(self) -> bool:
        return True  # Public channel scraping needs no credentials

    async def search(self, params: SearchParams) -> list[GeoPost]:
        place_name = await reverse_geocode(params.latitude, params.longitude)
        keywords = {
            w.lower() for w in (params.keyword + " " + place_name).split() if len(w) > 2
        }

        posts = []
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "fa,en;q=0.9",
        }

        async with httpx.AsyncClient() as client:
            for channel in self.channels[: 8]:  # Limit concurrent channels
                try:
                    resp = await client.get(
                        CHANNEL_URL.format(channel=channel),
                        headers=headers,
                        timeout=10,
                        follow_redirects=True,
                    )
                    if resp.status_code != 200:
                        continue
                    channel_posts = self._parse_channel(
                        resp.text, channel, place_name, keywords, params
                    )
                    posts.extend(channel_posts)
                except Exception:
                    continue

        # Sort newest first, deduplicate
        seen = set()
        unique = []
        for p in sorted(posts, key=lambda x: x.timestamp or datetime.min.replace(tzinfo=timezone.utc), reverse=True):
            if p.post_id not in seen:
                seen.add(p.post_id)
                unique.append(p)

        return unique[: params.max_results]

    def _parse_channel(
        self, html: str, channel: str, place_name: str, keywords: set, params: SearchParams
    ) -> list[GeoPost]:
        """Parse messages from a t.me/s/{channel} HTML page."""
        posts = []

        # Extract message blocks
        msg_texts = _MSG_RE.findall(html)
        timestamps = _TIME_RE.findall(html)
        msg_ids = _MSG_ID_RE.findall(html)

        matched = []
        all_recent = []

        for i, raw_text in enumerate(msg_texts):
            text = unescape(_TAG_RE.sub("", raw_text)).strip()
            if not text:
                continue

            ts = None
            if i < len(timestamps):
                try:
                    ts = datetime.fromisoformat(timestamps[i].replace("Z", "+00:00"))
                except ValueError:
                    pass

            msg_id = msg_ids[i] if i < len(msg_ids) else f"{channel}_{i}"
            url = f"https://t.me/{msg_id}" if "/" in msg_id else f"https://t.me/{channel}"

            post = GeoPost(
                platform="telegram",
                post_id=msg_id,
                url=url,
                text=text[:200],
                author=f"@{channel}",
                latitude=params.latitude,
                longitude=params.longitude,
                location_name=place_name,
                timestamp=ts,
            )
            all_recent.append(post)
            text_lower = text.lower()
            if any(kw in text_lower for kw in keywords):
                matched.append(post)

        # Return keyword-matched posts; fall back to recent posts if nothing matched
        return matched if matched else all_recent
