#!/usr/bin/env python3
"""GeoFeed CLI — search social media by GPS coordinates."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import config
from models import SearchParams
from providers.youtube import YouTubeProvider
from providers.flickr import FlickrProvider
from providers.instagram import InstagramProvider
from providers.twitter import TwitterProvider
from providers.tiktok import TikTokProvider
from providers.bluesky import BlueskyProvider
from providers.mastodon import MastodonProvider
from providers.snapchat import SnapchatProvider
from providers.facebook import FacebookProvider
from providers.telegram import TelegramProvider
from providers.aparat import AparatProvider
from providers.rubika import RubikaProvider
from providers.reddit import RedditProvider

ALL_PROVIDERS = {
    "youtube": YouTubeProvider,
    "flickr": FlickrProvider,
    "instagram": InstagramProvider,
    "twitter": TwitterProvider,
    "tiktok": TikTokProvider,
    "bluesky": BlueskyProvider,
    "mastodon": MastodonProvider,
    "snapchat": SnapchatProvider,
    "facebook": FacebookProvider,
    "telegram": TelegramProvider,
    "aparat": AparatProvider,
    "rubika": RubikaProvider,
    "reddit": RedditProvider,
}

PLATFORM_NAMES = list(ALL_PROVIDERS.keys())


async def run_search(params: SearchParams, platform_names: list[str]) -> list[dict]:
    """Run searches across selected providers in parallel."""
    tasks = []
    for name in platform_names:
        cls = ALL_PROVIDERS.get(name)
        if not cls:
            print(f"  ⚠ Unknown platform: {name}", file=sys.stderr)
            continue
        provider = cls()
        if not provider.is_configured():
            print(f"  ⚠ {name}: not configured (missing API key). Skipping.", file=sys.stderr)
            continue
        print(f"  🔍 Searching {name}...", file=sys.stderr)
        tasks.append(safe_search(provider, params))

    if not tasks:
        print("No configured providers. See config.yaml.example.", file=sys.stderr)
        return []

    results = await asyncio.gather(*tasks)
    posts = [post for batch in results for post in batch]
    posts.sort(key=lambda p: p.get("timestamp") or "", reverse=True)
    return posts


async def safe_search(provider, params: SearchParams) -> list[dict]:
    try:
        posts = await provider.search(params)
        return [p.to_dict() for p in posts]
    except Exception as e:
        print(f"  ❌ [{provider.name}] {e}", file=sys.stderr)
        return []


def main():
    parser = argparse.ArgumentParser(
        description="GeoFeed — Search social media by GPS coordinates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  %(prog)s --lat 40.7128 --lng -74.006 --radius 5
  %(prog)s --lat 48.8566 --lng 2.3522 --keyword "Eiffel Tower" --platforms youtube flickr
  %(prog)s --lat 34.0522 --lng -118.2437 --json results.json
  %(prog)s --server                       # Start the web UI
""",
    )

    parser.add_argument("--lat", type=float, help="Latitude")
    parser.add_argument("--lng", type=float, help="Longitude")
    parser.add_argument("--radius", type=float, default=10, help="Search radius in km (default: 10)")
    parser.add_argument("--keyword", "-k", default="", help="Optional keyword filter")
    parser.add_argument("--max-results", "-n", type=int, default=50, help="Max results per platform (default: 50)")
    parser.add_argument(
        "--platforms", "-p", nargs="+", choices=PLATFORM_NAMES, default=PLATFORM_NAMES,
        help="Platforms to search (default: all)",
    )
    parser.add_argument("--json", dest="json_output", metavar="FILE", help="Save results to a JSON file")
    parser.add_argument("--server", action="store_true", help="Start the web UI instead of CLI search")
    parser.add_argument("--port", type=int, default=5000, help="Port for web server (default: 5000)")
    parser.add_argument("--live", action="store_true", help="Re-poll continuously and print new results")
    parser.add_argument("--interval", type=int, default=60, help="Polling interval for --live mode in seconds (default: 60)")
    parser.add_argument("--config", metavar="FILE", help="Path to config.yaml")

    args = parser.parse_args()

    # Load config
    config_path = Path(args.config) if args.config else None
    config.load_config(config_path)

    # Web server mode
    if args.server:
        from server import app
        print(f"🌍 GeoFeed web UI starting at http://localhost:{args.port}")
        app.run(debug=True, port=args.port)
        return

    # CLI search mode — require lat/lng
    if args.lat is None or args.lng is None:
        parser.error("--lat and --lng are required for CLI search (or use --server for the web UI)")

    params = SearchParams(
        latitude=args.lat,
        longitude=args.lng,
        radius_km=args.radius,
        keyword=args.keyword,
        max_results=args.max_results,
    )

    print(f"📍 Searching near ({args.lat}, {args.lng}), radius {args.radius} km", file=sys.stderr)

    if args.live:
        import time
        print(f"🟢 Live mode — polling every {args.interval}s. Press Ctrl+C to stop.", file=sys.stderr)
        seen_ids: set = set()
        while True:
            posts = asyncio.run(run_search(params, args.platforms))
            new_posts = [p for p in posts if p["post_id"] not in seen_ids]
            for p in new_posts:
                seen_ids.add(p["post_id"])
                print(f"[{p['platform']}] {p.get('text', '')[:80]}")
                print(f"  👤 @{p.get('author', '?')}  📍 {p.get('location_name', '')}")
                print(f"  🔗 {p.get('url', '')}")
                print()
            print(f"  [⏳ {len(new_posts)} new | {len(seen_ids)} total — next poll in {args.interval}s]", file=sys.stderr)
            time.sleep(args.interval)
        return

    posts = asyncio.run(run_search(params, args.platforms))

    print(f"\n✅ Found {len(posts)} total result(s)\n", file=sys.stderr)

    # Output
    if args.json_output:
        with open(args.json_output, "w") as f:
            json.dump(posts, f, indent=2, default=str)
        print(f"💾 Results saved to {args.json_output}", file=sys.stderr)
    else:
        # Print to stdout as formatted text
        for p in posts:
            ts = p.get("timestamp", "")
            print(f"[{p['platform']}] {p.get('text', '')[:80]}")
            print(f"  👤 @{p.get('author', '?')}  📍 {p.get('location_name', '')}")
            print(f"  🔗 {p.get('url', '')}")
            if ts:
                print(f"  🕐 {ts}")
            print()


if __name__ == "__main__":
    main()
