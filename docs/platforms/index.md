# Platforms

GeoFeed supports 13 platforms across three tiers based on credential requirements.

## No credentials needed

These platforms work immediately after installation:

- [Bluesky](bluesky.md) — AT Protocol public search
- [Mastodon](mastodon.md) — hashtag timeline
- [Telegram](telegram.md) — curated public channel scraper
- [Reddit](reddit.md) — public JSON API
- [TikTok](tiktok.md) — unofficial web search (cookies optional)
- [Aparat](aparat.md) — Iranian video platform
- [Rubika](rubika.md) — Iranian social network

## Free API key required

- [YouTube](youtube.md) — Google Cloud Console (free tier, 10k units/day)
- [Flickr](flickr.md) — Flickr App Garden (free)

## Session cookie required

- [Instagram](instagram.md) — copy from browser DevTools
- [Snapchat](snapchat.md) — copy from map.snapchat.com + Playwright required

## Paid or restricted

- [Twitter / X](twitter.md) — bearer token required; geo queries need paid tier
- [Facebook](facebook.md) — Graph API app credentials; public post search removed in 2015

## Geo accuracy

| Tier | Platforms | How geo works |
|---|---|---|
| **Exact** | YouTube, Flickr, Twitter | Native lat/lon radius query |
| **Nearby venues** | Instagram, Snapchat, Facebook | Searches nearby places, then fetches posts |
| **Approximate** | All others | Reverse-geocodes coordinates to place name, then keyword search |
