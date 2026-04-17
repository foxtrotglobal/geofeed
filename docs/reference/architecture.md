# Architecture

## Directory structure

```
geofeed/
├── main.py              # CLI entry point
├── server.py            # Flask web server + /api/search + /api/stream (SSE)
├── config.py            # YAML + environment variable config loader
├── models.py            # GeoPost & SearchParams dataclasses
├── geo.py               # Haversine distance + Nominatim reverse geocoding
├── providers/
│   ├── base.py          # Abstract BaseProvider interface
│   ├── youtube.py       # YouTube Data API v3
│   ├── twitter.py       # X/Twitter API v2
│   ├── instagram.py     # Instagram internal location API
│   ├── bluesky.py       # AT Protocol public search
│   ├── mastodon.py      # Mastodon hashtag timeline
│   ├── telegram.py      # Public channel scraper
│   ├── reddit.py        # Reddit public JSON search
│   ├── snapchat.py      # Playwright + Snap Map
│   ├── tiktok.py        # TikTok web search
│   ├── flickr.py        # Flickr photo search
│   ├── facebook.py      # Facebook Graph API
│   ├── aparat.py        # Aparat Iranian video platform
│   └── rubika.py        # Rubika Iranian social network
├── templates/
│   └── map.html         # Leaflet.js map + search form + live mode
└── static/
    └── style.css        # Dark sidebar theme
```

## Data flow

```
User request → Flask /api/search
  → SearchParams(lat, lng, radius, keyword, max_results)
  → asyncio.gather(*[provider.search(params) for configured providers])
  → [GeoPost, GeoPost, ...] from each provider
  → Sorted by timestamp (newest first)
  → [GeoPost.to_dict(), ...] → JSON response
  → Leaflet.js renders markers on map
```

## Key classes

### GeoPost

Unified data model returned by every provider:

```python
@dataclass
class GeoPost:
    platform: str
    post_id: str
    url: str
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

### BaseProvider

Every provider implements this interface:

```python
class BaseProvider(ABC):
    name: str
    color: str  # hex marker color

    @abstractmethod
    async def search(self, params: SearchParams) -> list[GeoPost]: ...

    def is_configured(self) -> bool: ...
```

## API endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Web UI (Leaflet map) |
| `GET` | `/api/providers` | List all providers + configured status |
| `POST` | `/api/search` | Run a geo search, returns JSON |
| `GET` | `/api/stream` | SSE stream for live mode |
