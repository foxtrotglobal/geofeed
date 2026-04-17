# GeoFeed

[![Tests](https://github.com/foxtrotglobal/geofeed/actions/workflows/tests.yml/badge.svg)](https://github.com/foxtrotglobal/geofeed/actions)
[![Docs](https://img.shields.io/badge/docs-foxtrotglobal.github.io%2Fgeofeed-blue)](https://foxtrotglobal.github.io/geofeed/)
[![Python](https://img.shields.io/badge/python-3.11+-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Release](https://img.shields.io/github/v/release/foxtrotglobal/geofeed)](https://github.com/foxtrotglobal/geofeed/releases)

> **[Full documentation → foxtrotglobal.github.io/geofeed](https://foxtrotglobal.github.io/geofeed/)**

GeoFeed searches **13 social media platforms** simultaneously for public content posted near GPS coordinates and displays results on an interactive map.

Designed for researchers, journalists, OSINT investigators, and event monitors — including platforms popular in the Middle East and Iran (Telegram, Aparat, Rubika).

**Key features:**
- 13 platforms queried in parallel — YouTube, Instagram, Twitter/X, Bluesky, Mastodon, Telegram, Reddit, Snapchat, TikTok, Flickr, Facebook, Aparat, Rubika
- Interactive Leaflet.js map with color-coded markers and clickable post previews
- **Live mode** — SSE streams new results to the map automatically
- CLI with JSON export, or web UI
- 169-test suite — all HTTP mocked, no API keys needed to run
- No database — stateless, runs locally or on a $5 VPS

## Supported Platforms

| Platform | Method | Geo Accuracy | Credential Required |
|----------|--------|-------------|-------------------|
| **YouTube** | Data API v3 `location` + `locationRadius` | Exact | Google API key (free) |
| **X / Twitter** | API v2 `point_radius`, falls back to keyword | Approximate | Bearer token |
| **Instagram** | Internal location search + sections API | Nearby venues | Session cookie |
| **Bluesky** | AT Protocol `feed.searchPosts` | Approximate | None (public API) |
| **Mastodon** | Hashtag timeline (`/timelines/tag/`) | Approximate | None (public API) |
| **Telegram** | Scrapes curated public channels via t.me/s/ | Keyword match | None |
| **Reddit** | Public JSON search API | Approximate | None |
| **Snapchat** | Playwright + Snap Map (requires session cookie) | Exact | Session cookie + Playwright |
| **TikTok** | Unofficial web search (requires browser cookies) | Approximate | msToken + ttwid cookies |
| **Flickr** | `flickr.photos.search` with lat/lon/radius | Exact | Flickr API key (free) |
| **Facebook** | Graph API Place search + feed | Nearby venues | App ID + App Secret |
| **Aparat** | Iranian video platform search (aparat.com) | Approximate | None |
| **Rubika** | Iranian social network keyword search | Approximate | None |

## Quick start

**Deploy to a server (one command):**

```bash
curl -fsSL https://raw.githubusercontent.com/foxtrotglobal/geofeed/main/deploy.sh | sudo bash
```

The script sets up Python, Nginx, HTTPS, systemd, and Playwright automatically. See [Deployment docs →](https://foxtrotglobal.github.io/geofeed/deployment/automated/)

**Run locally:**

```bash
git clone https://github.com/foxtrotglobal/geofeed.git
cd geofeed
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && playwright install chromium
cp config.yaml.example config.yaml   # add your API keys
python main.py --server              # open http://localhost:5000
```

See [Installation →](https://foxtrotglobal.github.io/geofeed/installation/) and [Configuration →](https://foxtrotglobal.github.io/geofeed/configuration/) for full setup details.

## Installation

### Prerequisites

- **Python 3.11 or higher** — check with `python3 --version`
- **git** — to clone the repository
- At least one API key (see [Getting API Keys](#getting-api-keys)) — Bluesky, Mastodon, Telegram, Reddit, Aparat, and Rubika work with no credentials at all

### 1. Clone the repository

```bash
git clone https://github.com/foxtrotglobal/geofeed.git
cd geofeed
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate      # macOS / Linux
.venv\Scripts\activate         # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt

# Required for Snapchat (Playwright headless browser)
playwright install chromium
```

### 4. Configure API keys

```bash
cp config.yaml.example config.yaml
```

Edit `config.yaml` and add credentials for the platforms you want to use. Unconfigured platforms are skipped automatically — you do not need all of them.

```yaml
youtube:
  api_key: "YOUR_GOOGLE_API_KEY"       # Free — console.cloud.google.com

twitter:
  bearer_token: "YOUR_BEARER_TOKEN"    # developer.twitter.com

instagram:
  session_cookie: "YOUR_COOKIE"        # Copy from browser DevTools (see below)

snapchat:
  session_cookie: "YOUR_COOKIE"        # Copy from map.snapchat.com DevTools

tiktok:
  ms_token: ""                         # Optional: F12 → Application → Cookies → tiktok.com
  ttwid: ""                            # Optional: same location as ms_token

# Bluesky, Mastodon, Telegram, Reddit, Aparat, Rubika need no credentials
```

You can also use environment variables instead of the config file (e.g. `YOUTUBE_API_KEY`, `FLICKR_API_KEY`). Environment variables take precedence over `config.yaml`.

### 5. Run

**Web UI (recommended):**

```bash
python main.py --server
```

Open [http://localhost:5000](http://localhost:5000). Click anywhere on the map to set coordinates, choose platforms, and hit Search.

**Live mode** — enable the 🟢 Live toggle in the UI to automatically re-poll every N seconds and push new results to the map as they arrive.

**CLI:**

```bash
# Search near Times Square, 5km radius
python main.py --lat 40.7580 --lng -73.9855 --radius 5

# Search with keyword, specific platforms, save to JSON
python main.py --lat 48.8566 --lng 2.3522 -k "Eiffel Tower" -p youtube twitter --json results.json

# Live mode — continuously poll and print new results every 30 seconds
python main.py --lat 35.6892 --lng 51.3890 --live --interval 30   # Tehran
```

## Running Tests

No API keys are needed — all HTTP calls are mocked.

```bash
pip install pytest pytest-asyncio
pytest -v
```

## CLI Reference

```
python main.py --help

Options:
  --lat FLOAT             Latitude (required for CLI search)
  --lng FLOAT             Longitude (required for CLI search)
  --radius FLOAT          Search radius in km (default: 10)
  --keyword, -k TEXT      Optional keyword filter
  --max-results, -n INT   Max results per platform (default: 50)
  --platforms, -p LIST    Platforms to search (default: all)
  --json FILE             Save results to a JSON file
  --server                Start the web UI instead of CLI search
  --port INT              Port for web server (default: 5000)
  --live                  Continuously poll and print new results
  --interval INT          Polling interval in seconds for --live (default: 60)
  --config FILE           Path to config.yaml
```

## Web UI

The web interface features:

- **Interactive Leaflet map** — click to set coordinates, or type them in
- **Search radius visualization** — purple circle shows the search area
- **Color-coded markers** — each platform has a distinct color (red = YouTube, blue = Flickr, pink = Instagram, etc.)
- **Popup previews** — click a marker to see the post text, thumbnail, author, timestamp, and a link to the original
- **Sidebar results list** — scrollable list of all results with direct links

## Getting API Keys

### YouTube (free)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → Enable "YouTube Data API v3"
3. Go to Credentials → Create an API key

### Flickr (free)

1. Go to [Flickr App Garden](https://www.flickr.com/services/apps/create/)
2. Apply for a non-commercial key
3. Copy the API key

### Instagram (session cookie)

1. Log in to Instagram in Chrome
2. Open DevTools (F12) → Application → Cookies → `https://www.instagram.com`
3. Right-click any cookie → "Show Requests With This Cookie"
4. Click a request → Headers → copy the full `cookie:` header value

> **Warning:** Treat your Instagram cookie like a password. It grants full access to your account.

### X / Twitter

1. Apply at [developer.twitter.com](https://developer.twitter.com/)
2. Create a project and app → generate a Bearer Token
3. **Note:** Geo queries (`point_radius`) require Elevated or Academic access (not available on the free tier)

### TikTok

No credentials required. TikTok search uses web scraping with reverse-geocoded place names. Optionally, add an `ms_token` cookie from your browser for better results.

### Bluesky

No credentials required. Uses the public AT Protocol API. Optionally add your handle and an [App Password](https://bsky.app/settings/app-passwords) in `config.yaml` for higher rate limits.

### Mastodon

No credentials required. Searches `mastodon.social` by default. Set `instance` in `config.yaml` to search a different Mastodon instance.

### Snapchat

Requires **Playwright** and a Snapchat session cookie (Snap Map now requires login):

1. Run `playwright install chromium` once after installing dependencies
2. Log in to Snapchat in Chrome and visit **https://map.snapchat.com/**
3. F12 → Network → click any `map.snapchat.com` request → Headers → copy the `cookie:` value
4. Paste into `config.yaml` under `snapchat.session_cookie`

> **Note:** Only copy the `cookie:` line — stop before the next header (`pragma:`, `referer:`, etc.).

### Telegram

No credentials required. Searches a curated list of public channels via `t.me/s/`. To customize the channels:

```yaml
telegram:
  channels:
    - irna_ir
    - bbcpersian
    - your_channel_name
```

### Reddit

No credentials required. Searches Reddit globally and in regional subreddits (`r/iran`, `r/tehran`, `r/middleeast`). To customize:

```yaml
reddit:
  subreddits: "iran,tehran,middleeast,worldnews"
```

### Aparat & Rubika

No credentials required. Iranian video/social platforms searched by reverse-geocoded place name.

### Facebook

1. Go to [developers.facebook.com](https://developers.facebook.com/) and create an app
2. Copy the **App ID** and **App Secret** into `config.yaml`
3. **Note:** Public post search was removed in Graph API v2.0 (2015). This provider finds nearby Places and fetches their public page feeds only.

## Architecture

```
geofeed/
├── main.py              # CLI entry point (--server, --live, --interval)
├── server.py            # Flask web server + /api/search + /api/stream (SSE)
├── config.py            # YAML + environment variable config loader
├── models.py            # GeoPost & SearchParams dataclasses
├── geo.py               # Haversine distance + Nominatim reverse geocoding
├── providers/
│   ├── base.py          # Abstract BaseProvider interface
│   ├── youtube.py       # YouTube Data API v3 (geo search)
│   ├── twitter.py       # X/Twitter API v2 (geo + keyword fallback)
│   ├── instagram.py     # Instagram internal location + sections API
│   ├── bluesky.py       # AT Protocol public search
│   ├── mastodon.py      # Mastodon hashtag timeline
│   ├── telegram.py      # Public channel scraper via t.me/s/
│   ├── reddit.py        # Reddit public JSON search
│   ├── snapchat.py      # Playwright + Snap Map (requires session cookie)
│   ├── tiktok.py        # TikTok web search (requires cookies)
│   ├── flickr.py        # Flickr photo search
│   ├── facebook.py      # Facebook Graph API places + feeds
│   ├── aparat.py        # Aparat Iranian video platform
│   └── rubika.py        # Rubika Iranian social network
├── templates/
│   └── map.html         # Leaflet.js map + live mode toggle
└── static/
    └── style.css        # Dark sidebar theme
```

All providers implement the same `BaseProvider` interface and run in parallel via `asyncio.gather()`. Each returns a list of `GeoPost` objects with a unified schema (platform, coordinates, text, author, timestamp, media URL, etc.).

## For Contributors

This section explains the key design decisions to help you understand the codebase quickly.

### Data model

Every platform returns a list of `GeoPost` objects — a single unified schema regardless of source:

```python
@dataclass
class GeoPost:
    platform: str           # "youtube", "instagram", etc.
    post_id: str            # platform-native ID
    url: str                # direct link to the post
    text: str = ""
    author: str = ""
    latitude: float | None = None
    longitude: float | None = None
    location_name: str = ""
    media_url: str = ""
    timestamp: datetime | None = None
    distance_km: float | None = None
    extra: dict = field(default_factory=dict)
```

`GeoPost.to_dict()` produces the JSON sent to the frontend. The `extra` dict holds platform-specific fields (e.g. `{"subreddit": "iran"}`) without polluting the schema.

### Provider interface

Every provider subclasses `BaseProvider` and implements two methods:

```python
class BaseProvider(ABC):
    name: str   # registry key, must match ALL_PROVIDERS key
    color: str  # unique hex color for map markers

    @abstractmethod
    async def search(self, params: SearchParams) -> list[GeoPost]: ...

    def is_configured(self) -> bool: ...
```

`is_configured()` returning `False` causes the provider to be silently skipped — no error, no empty result entry in the API response. This lets users add only the credentials they have.

### Parallel execution

`server.run_search()` wraps every provider call in `_safe_search()` — which catches any exception and returns `[]` — then gathers all providers concurrently:

```python
async def run_search(params, platform_names):
    tasks = [_safe_search(cls(), params)
             for name, cls in ALL_PROVIDERS.items()
             if name in platform_names and cls().is_configured()]
    results = await asyncio.gather(*tasks)
    posts = [p for batch in results for p in batch]
    return sorted(posts, key=lambda p: p.get("timestamp") or "", reverse=True)
```

Flask is synchronous, so `server.py` calls `loop.run_until_complete(run_search(...))` via `get_or_create_event_loop()` to bridge sync→async.

### SSE live mode

The `/api/stream` endpoint is a Flask streaming `Response` with `mimetype="text/event-stream"`. It runs the search in a loop, deduplicates by `post_id`, and emits only new posts:

```python
def generate():
    seen_ids = set()
    while True:
        posts = loop.run_until_complete(run_search(params, platforms))
        new = [p for p in posts if p["post_id"] not in seen_ids]
        seen_ids.update(p["post_id"] for p in new)
        yield f"data: {json.dumps(new)}\n\n"
        time.sleep(interval)
```

> **Nginx requirement:** `proxy_buffering off` in the Nginx config is mandatory — without it, SSE data is buffered and never delivered to the browser.

### Geo strategy by tier

| Tier | Platforms | How it works |
|---|---|---|
| **Native radius** | YouTube, Flickr, Twitter, Snapchat, Instagram | Direct lat/lon/radius query to the platform API |
| **Venue-based** | Instagram, Facebook, Snapchat | Find nearby venues, then fetch posts tagged there |
| **Reverse geocode** | Bluesky, Mastodon, Telegram, Reddit, TikTok, Aparat, Rubika | `geo.reverse_geocode(lat, lon)` → Nominatim → place name → keyword search |

`geo.haversine()` is used by several providers to filter venues by actual distance before returning posts.

### Playwright (Snapchat)

Snap Map is JavaScript-rendered and requires authentication. The Snapchat provider:
1. Launches headless Chromium via `playwright.async_api`
2. Injects session cookies from `config.yaml`
3. Navigates to `map.snapchat.com/?lng=...&lat=...`
4. Intercepts all JSON responses from `snapchat.com` matching story URL patterns
5. Parses the intercepted data into `GeoPost` objects

### Config loading

`config.get(section, key)` checks environment variables **before** `config.yaml`. The env var format is `SECTION_KEY` uppercase (e.g. `YOUTUBE_API_KEY`). This allows production deployments to override local config without changing the file.

### Test strategy

All 169 tests mock HTTP at the `httpx.AsyncClient` level — no real network calls, no API keys needed.

| File | What it tests |
|---|---|
| `test_providers.py` | Each provider's response parsing with mocked HTTP |
| `test_models_and_geo.py` | `GeoPost` serialization, `haversine` edge cases |
| `test_api.py` | Flask routes, 400 errors, request/response contract |
| `test_config.py` | YAML loading, env var override precedence |
| `test_integration.py` | `run_search` orchestration, provider error isolation |
| `test_core.py` | Concurrent execution timing, SSE wire format, CLI flags |

The concurrency test verifies providers actually run in parallel (3×0.1s providers must complete in <0.24s). The SSE test validates the `data: <json>\n\n` wire format.

## Adding a New Provider

1. Create `providers/myplatform.py` — subclass `BaseProvider`, implement `search()` and `is_configured()`
2. Register it in `server.py` and `main.py` under `ALL_PROVIDERS`
3. Add credentials to `config.yaml.example`
4. Add map UI checkbox + hex color to `templates/map.html`
5. Write tests in `tests/test_providers.py` using mocked HTTP responses

See the [full guide →](https://foxtrotglobal.github.io/geofeed/reference/new-provider/)

## Deployment
### Option A — Automated script (recommended)
A single script handles everything on a fresh Ubuntu 22.04+ / Debian 12+ server:
```bash
curl -fsSL https://raw.githubusercontent.com/foxtrotglobal/geofeed/main/deploy.sh | sudo bash
```
The script will prompt for your domain name and API keys, then automatically:
- Install Python, Nginx, Certbot, and Playwright browser dependencies
- Create a dedicated `geofeed` system user
- Clone the repo, set up the virtual environment, install all dependencies
- Write `config.yaml` with your credentials (permissions: 600)
- Create and enable a systemd service
- Configure Nginx with SSE-safe reverse proxy settings
- Optionally obtain a free Let's Encrypt HTTPS certificate
- Configure the UFW firewall

**Non-interactive** (CI / infrastructure-as-code):
```bash
sudo DOMAIN=geofeed.example.com \
     YOUTUBE_API_KEY=yourkey \
     TWITTER_BEARER_TOKEN=yourtoken \
     bash deploy.sh
```
See [`deploy.sh`](deploy.sh) for the full list of supported environment variables.

### Option B — Manual VPS (Ubuntu 22.04+)
**1. Clone and set up:**
```bash
git clone https://github.com/foxtrotglobal/geofeed.git
cd geofeed
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt gunicorn
cp config.yaml.example config.yaml
# Edit config.yaml with your API keys
```
**2. Create a systemd service** at `/etc/systemd/system/geofeed.service`:
```ini
[Unit]
Description=GeoFeed
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/geofeed
ExecStart=/home/ubuntu/geofeed/.venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 server:app
Restart=always

[Install]
WantedBy=multi-user.target
```
**3. Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable geofeed
sudo systemctl start geofeed
sudo systemctl status geofeed
```
**4. Set up Nginx as reverse proxy** at `/etc/nginx/sites-available/geofeed`:
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    add_header X-Frame-Options SAMEORIGIN;
    add_header X-Content-Type-Options nosniff;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;        # Required for SSE live mode
        proxy_cache off;
        proxy_read_timeout 300s;
        proxy_set_header X-Accel-Buffering no;
    }
}
```
**5. Enable site and obtain HTTPS certificate:**
```bash
sudo ln -s /etc/nginx/sites-available/geofeed /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d yourdomain.com
```
**6. Lock down the firewall:**
```bash
sudo ufw allow 'Nginx Full'
sudo ufw delete allow 5000
```
**7. Verify the deployment:**
```bash
sudo systemctl status nginx geofeed
curl -I https://yourdomain.com
```
### Option C — Docker
```bash
# Build and run (config.yaml mounted as read-only volume)
docker-compose up -d

# Or manually with env vars (no config.yaml needed)
docker build -t geofeed .
docker run -p 5000:5000 \
  -e YOUTUBE_API_KEY=your_key \
  -e TWITTER_BEARER_TOKEN=your_token \
  geofeed
```

### Option D — Render / Railway / Heroku
Set your API keys as environment variables on the platform dashboard (no `config.yaml` needed — the app reads env vars automatically). Use this start command:
```
gunicorn -w 2 -b 0.0.0.0:$PORT server:app
```
### Production tips
- Use environment variables for all API keys — never commit `config.yaml`
- Add `--max-results 20` to limit parallel API load across 13 platforms
- `proxy_buffering off` in Nginx is required for the SSE live mode to work
- View logs: `sudo journalctl -u geofeed -f`
- Restart after changes: `sudo systemctl restart geofeed`
## Limitations

- **Instagram** session cookie expires every 30–90 days — must be refreshed from browser
- **X/Twitter** free tier doesn't support `point_radius` geo queries — falls back to keyword search
- **TikTok** uses unofficial endpoints requiring `msToken`/`ttwid` cookies that expire frequently
- **Snapchat** requires Playwright + session cookie; cookies expire and must be refreshed
- **Facebook** Graph API v2.0+ removed public post search — only nearby Place feeds are accessible
- **Aparat / Rubika** use unofficial/undocumented endpoints that may change
- **Telegram** shows content from pre-configured channels only, not a true geo search
- API rate limits apply to all platforms — use `--max-results 20` in high-load deployments

## License

MIT
