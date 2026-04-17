# Docker

## docker-compose (recommended)

```bash
cp config.yaml.example config.yaml
# Edit config.yaml with your API keys
docker-compose up -d
```

The `docker-compose.yml` mounts `config.yaml` as a read-only volume so secrets are never baked into the image.

## Manual

```bash
docker build -t geofeed .

# With config.yaml
docker run -p 5000:5000 -v ./config.yaml:/app/config.yaml:ro geofeed

# With environment variables (no config.yaml needed)
docker run -p 5000:5000 \
  -e YOUTUBE_API_KEY=your_key \
  -e TWITTER_BEARER_TOKEN=your_token \
  geofeed
```

## Notes

- The `--timeout 120` Gunicorn flag keeps SSE live mode connections alive
- Playwright Chromium is **not** included in the Docker image — Snapchat requires the host install or a separate browser container
