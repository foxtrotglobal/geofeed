# GeoFeed

**Search 13 social media platforms by GPS coordinates.**

[![Tests](https://github.com/foxtrotglobal/geofeed/actions/workflows/tests.yml/badge.svg)](https://github.com/foxtrotglobal/geofeed/actions)
[![Python](https://img.shields.io/badge/python-3.11+-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](https://github.com/foxtrotglobal/geofeed/blob/main/LICENSE)

GeoFeed is an open-source Python tool for researchers, journalists, and OSINT investigators who need to monitor what is being posted about a specific physical location across multiple platforms simultaneously.

## How it works

Enter a latitude, longitude, and search radius. GeoFeed queries all configured platforms in parallel and displays results as color-coded markers on an interactive Leaflet.js map.

![GeoFeed map interface](https://raw.githubusercontent.com/foxtrotglobal/geofeed/main/docs/assets/screenshot.png)

## Supported platforms

| Platform | Geo method | Credentials |
|---|---|---|
| YouTube | Native geo search API | Google API key (free) |
| X / Twitter | point_radius query | Bearer token |
| Instagram | Location search endpoint | Session cookie |
| Bluesky | AT Protocol search | None |
| Mastodon | Hashtag timeline | None |
| Telegram | Public channel scraper | None |
| Reddit | JSON search API | None |
| Snapchat | Playwright + Snap Map | Session cookie + Playwright |
| TikTok | Unofficial web search | Browser cookies |
| Flickr | flickr.photos.search | API key (free) |
| Facebook | Graph API places | App ID + Secret |
| Aparat | Iranian video platform | None |
| Rubika | Iranian social network | None |

## Quick start

```bash
git clone https://github.com/foxtrotglobal/geofeed.git
cd geofeed
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp config.yaml.example config.yaml  # add your API keys
python main.py --server              # open http://localhost:5000
```

See [Installation](installation.md) for detailed setup instructions.

## Deploy to a server

```bash
curl -fsSL https://raw.githubusercontent.com/foxtrotglobal/geofeed/main/deploy.sh | sudo bash
```

See [Deployment](deployment/automated.md) for all options.
