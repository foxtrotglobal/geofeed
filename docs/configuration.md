# Configuration

GeoFeed is configured via `config.yaml`. Copy the example file to get started:

```bash
cp config.yaml.example config.yaml
```

Unconfigured platforms are skipped automatically — you do not need credentials for all of them.

## Environment variables

Environment variables take precedence over `config.yaml`. The format is `SECTION_KEY` in uppercase:

```bash
export YOUTUBE_API_KEY=your_key
export TWITTER_BEARER_TOKEN=your_token
```

This is the recommended approach for production deployments.

## Full config reference

```yaml
youtube:
  api_key: ""           # console.cloud.google.com → YouTube Data API v3

flickr:
  api_key: ""           # flickr.com/services/apps/create

instagram:
  session_cookie: ""    # Copy from browser DevTools (see Platforms → Instagram)

twitter:
  bearer_token: ""      # developer.twitter.com

tiktok:
  ms_token: ""          # F12 → Application → Cookies → tiktok.com → msToken
  ttwid: ""             # F12 → Application → Cookies → tiktok.com → ttwid

bluesky:
  identifier: ""        # Optional — your handle for higher rate limits
  app_password: ""      # Optional — bsky.app/settings/app-passwords

mastodon:
  instance: "mastodon.social"   # Any Mastodon instance
  access_token: ""              # Optional — for higher rate limits

snapchat:
  session_cookie: ""    # Copy from map.snapchat.com DevTools

telegram:
  bot_token: ""         # Optional — from @BotFather
  channels:             # Optional — override default channel list
    # - irna_ir
    # - bbcpersian

facebook:
  app_id: ""            # developers.facebook.com
  app_secret: ""

reddit:
  client_id: ""         # Optional — for higher rate limits
  client_secret: ""
  subreddits: ""        # e.g. "iran,tehran,middleeast"

# No credentials needed:
aparat:
rubika:
```

!!! warning "Never commit config.yaml"
    `config.yaml` is listed in `.gitignore`. Use environment variables in production.
