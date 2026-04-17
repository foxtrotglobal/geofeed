# GeoFeed

![Tests](https://github.com/foxtrotglobal/geofeed/actions/workflows/tests.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## About

GeoFeed is an open-source Python tool that searches **13 social media platforms** simultaneously for public content posted near a pair of GPS coordinates. Results are aggregated into a unified format and displayed as color-coded markers on an interactive map, with clickable popups showing post previews, thumbnails, authors, and timestamps.

It is designed for researchers, journalists, OSINT investigators, event monitors, or anyone who wants to understand what is being posted in a specific physical location across multiple platforms at once — including platforms popular in the Middle East and Iran (Telegram, Aparat, Rubika).

**Key features:**
- Search 13 platforms in parallel with a single command
- Interactive Leaflet.js map with color-coded markers per platform
- **Live mode** — SSE streaming pushes new results to the map automatically every N seconds
- CLI for scripting and JSON export, or a web UI for visual exploration
- Pluggable provider architecture — easy to add new platforms
- 59-test suite with fully mocked HTTP — no API keys needed to run tests
- No database required — stateless, runs locally

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

## Adding a New Provider

1. Create `providers/myplatform.py`
2. Subclass `BaseProvider` and implement `search()` and `is_configured()`
3. Register it in `server.py` and `main.py` under `ALL_PROVIDERS`

## Deployment
### Option A — VPS (Ubuntu 22.04+)
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
### Option B — Docker
Add a `Dockerfile` to the project root:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt gunicorn
EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "server:app"]
```
```bash
docker build -t geofeed .
docker run -p 5000:5000 \
  -e YOUTUBE_API_KEY=your_key \
  -e FLICKR_API_KEY=your_key \
  geofeed
```
### Option C — Render / Railway / Heroku
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
