# GeoFeed

Search multiple social media platforms for content posted near GPS coordinates and visualize results on an interactive map.

![Tests](https://github.com/foxtrotglobal/geofeed/actions/workflows/tests.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Supported Platforms

| Platform | Method | Geo Accuracy | Credential Required |
|----------|--------|-------------|-------------------|
| **YouTube** | Data API v3 `location` + `locationRadius` | Exact | Google API key (free) |
| **Flickr** | `flickr.photos.search` with lat/lon/radius | Exact | Flickr API key (free) |
| **Instagram** | Internal location search endpoint | Nearby venues | Session cookie |
| **X / Twitter** | API v2 `point_radius` query | Exact | Bearer token (paid tier) |
| **TikTok** | Reverse-geocode → keyword search | Approximate | None (web scraping) |

## Quick Start

### 1. Clone & set up the environment

```bash
cd geofeed
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure API keys

```bash
cp config.yaml.example config.yaml
```

Edit `config.yaml` and add your credentials. You only need keys for the platforms you want to use — unconfigured platforms are skipped automatically.

```yaml
youtube:
  api_key: "YOUR_GOOGLE_API_KEY"

flickr:
  api_key: "YOUR_FLICKR_API_KEY"

instagram:
  session_cookie: "YOUR_INSTAGRAM_COOKIE_STRING"

twitter:
  bearer_token: "YOUR_TWITTER_BEARER_TOKEN"

tiktok:
  ms_token: ""  # Optional — improves results but not required
```

Alternatively, set environment variables instead of using the config file (e.g. `YOUTUBE_API_KEY`, `FLICKR_API_KEY`, etc.).

### 3. Run

**Web UI (recommended):**

```bash
python main.py --server
```

Open [http://localhost:5000](http://localhost:5000). Click anywhere on the map to set coordinates, choose platforms, and search.

**CLI:**

```bash
# Search near Times Square, 5km radius
python main.py --lat 40.7580 --lng -73.9855 --radius 5

# Search with keyword, specific platforms, save to JSON
python main.py --lat 48.8566 --lng 2.3522 -k "Eiffel Tower" -p youtube flickr --json results.json
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

## Architecture

```
geofeed/
├── main.py              # CLI entry point
├── server.py            # Flask web server + /api/search endpoint
├── config.py            # YAML + environment variable config loader
├── models.py            # GeoPost & SearchParams dataclasses
├── geo.py               # Haversine distance + Nominatim reverse geocoding
├── providers/
│   ├── base.py          # Abstract BaseProvider interface
│   ├── youtube.py       # YouTube Data API v3
│   ├── flickr.py        # Flickr photo search
│   ├── instagram.py     # Instagram internal location API
│   ├── twitter.py       # X/Twitter API v2
│   └── tiktok.py        # TikTok web search
├── templates/
│   └── map.html         # Leaflet.js map + search form
└── static/
    └── style.css        # Dark sidebar theme
```

All providers implement the same `BaseProvider` interface and run in parallel via `asyncio.gather()`. Each returns a list of `GeoPost` objects with a unified schema (platform, coordinates, text, author, timestamp, media URL, etc.).

## Adding a New Provider

1. Create `providers/myplatform.py`
2. Subclass `BaseProvider` and implement `search()` and `is_configured()`
3. Register it in `server.py` and `main.py` under `ALL_PROVIDERS`

## Limitations

- **Instagram** requires a valid session cookie that may expire or get invalidated
- **X/Twitter** geo queries need a paid API tier
- **TikTok** has no real geo API — results are keyword-based approximations of the location name
- **Facebook** is not supported (no viable public API for geo search)
- API rate limits apply to all platforms

## License

MIT
