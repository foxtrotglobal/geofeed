# Automated Deployment (recommended)

The `deploy.sh` script handles the full setup on a fresh Ubuntu 22.04+ or Debian 12+ server in a single command.

## Interactive

```bash
curl -fsSL https://raw.githubusercontent.com/foxtrotglobal/geofeed/main/deploy.sh | sudo bash
```

The script will prompt for:

1. Your domain name (e.g. `geofeed.example.com`)
2. YouTube API key
3. Twitter bearer token
4. Instagram session cookie
5. Snapchat session cookie

All other platforms (Bluesky, Mastodon, Telegram, Reddit, Aparat, Rubika) need no credentials.

## Non-interactive (CI / infrastructure-as-code)

Set environment variables before running:

```bash
sudo DOMAIN=geofeed.example.com \
     YOUTUBE_API_KEY=your_key \
     TWITTER_BEARER_TOKEN=your_token \
     INSTAGRAM_SESSION_COOKIE="your_cookie" \
     bash deploy.sh
```

## What the script does

1. Installs system packages (Python, Nginx, Certbot, Playwright browser deps)
2. Creates a dedicated `geofeed` system user
3. Clones the repository to `/opt/geofeed`
4. Creates Python virtual environment and installs all dependencies
5. Installs Playwright + Chromium headless browser
6. Writes `config.yaml` with your credentials (permissions: 600)
7. Creates and enables a systemd service
8. Configures Nginx with SSE-safe reverse proxy settings
9. Obtains a Let's Encrypt HTTPS certificate
10. Configures the UFW firewall

## After deployment

| Command | Purpose |
|---|---|
| `sudo systemctl status geofeed` | Check service status |
| `sudo journalctl -u geofeed -f` | Live logs |
| `sudo systemctl restart geofeed` | Restart after config changes |
| `sudo nano /opt/geofeed/config.yaml` | Edit API keys |

See [Maintenance](../maintenance.md) for ongoing operations.
