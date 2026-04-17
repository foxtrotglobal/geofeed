# Running GeoFeed

## Web UI

```bash
python main.py --server
```

Open [http://localhost:5000](http://localhost:5000).

- Click anywhere on the map to set coordinates, or type them in the sidebar
- Set a radius (km) and optional keyword
- Choose which platforms to search
- Enable **🟢 Live** to stream new results automatically every N seconds

## CLI

```bash
# Search near Tehran, 10km radius
python main.py --lat 35.6892 --lng 51.3890 --radius 10

# Search with keyword, specific platforms, save to JSON
python main.py --lat 40.7128 --lng -74.006 -k "protest" -p youtube twitter reddit

# Live mode — poll every 30 seconds and print new results
python main.py --lat 35.6892 --lng 51.3890 --live --interval 30
```

## CLI reference

| Flag | Default | Description |
|---|---|---|
| `--lat` | required | Latitude |
| `--lng` | required | Longitude |
| `--radius` | `10` | Search radius in km |
| `--keyword`, `-k` | | Optional keyword filter |
| `--platforms`, `-p` | all | Platforms to search |
| `--max-results`, `-n` | `50` | Max results per platform |
| `--json FILE` | | Save results to JSON file |
| `--server` | | Start web UI |
| `--port` | `5000` | Web UI port |
| `--live` | | Continuously poll for new results |
| `--interval` | `60` | Polling interval in seconds |
| `--config FILE` | | Path to config.yaml |
