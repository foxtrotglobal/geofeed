"""Flask web server for GeoFeed — serves the map UI and search API."""

import asyncio
import json
import sys
import time
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request

# Ensure the project root is on the path
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

app = Flask(__name__)

# Registry of all providers
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


def get_or_create_event_loop():
    """Get the current event loop or create a new one."""
    try:
        return asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


async def run_search(params: SearchParams, platform_names: list[str]) -> list[dict]:
    """Run searches across selected providers in parallel."""
    tasks = []
    for name in platform_names:
        cls = ALL_PROVIDERS.get(name)
        if not cls:
            continue
        provider = cls()
        if not provider.is_configured():
            continue
        tasks.append(_safe_search(provider, params))

    results = await asyncio.gather(*tasks)
    # Flatten and sort by timestamp (newest first)
    posts = [post for batch in results for post in batch]
    posts.sort(key=lambda p: p.get("timestamp") or "", reverse=True)
    return posts


async def _safe_search(provider, params: SearchParams) -> list[dict]:
    """Run a single provider's search, catching errors gracefully."""
    try:
        posts = await provider.search(params)
        return [p.to_dict() for p in posts]
    except Exception as e:
        print(f"[{provider.name}] Error: {e}")
        return []


@app.route("/")
def index():
    return render_template("map.html")


@app.route("/api/search", methods=["POST"])
def search():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    try:
        params = SearchParams(
            latitude=float(data["latitude"]),
            longitude=float(data["longitude"]),
            radius_km=float(data.get("radius_km", 10)),
            keyword=data.get("keyword", ""),
            max_results=int(data.get("max_results", 50)),
        )
    except (KeyError, ValueError) as e:
        return jsonify({"error": f"Invalid parameters: {e}"}), 400

    platforms = data.get("platforms", list(ALL_PROVIDERS.keys()))

    loop = get_or_create_event_loop()
    posts = loop.run_until_complete(run_search(params, platforms))

    return jsonify({"posts": posts, "count": len(posts)})


@app.route("/api/geocode")
def geocode():
    """Geocode a place name (city, state, country) to lat/lon."""
    place = request.args.get("q", "").strip()
    if not place:
        return jsonify({"error": "Missing query parameter ?q="}), 400
    from geo import forward_geocode
    result = get_or_create_event_loop().run_until_complete(forward_geocode(place))
    if not result:
        return jsonify({"error": f"Location not found: {place}"}), 404
    return jsonify(result)


@app.route("/api/providers")
def list_providers():
    """List available providers and whether they are configured."""
    result = {}
    for name, cls in ALL_PROVIDERS.items():
        p = cls()
        result[name] = {"configured": p.is_configured(), "color": p.color}
    return jsonify(result)


@app.route("/api/stream")
def stream():
    """SSE endpoint — re-runs the search every `interval` seconds and pushes new posts."""
    try:
        lat = float(request.args["latitude"])
        lng = float(request.args["longitude"])
        radius = float(request.args.get("radius_km", 10))
        keyword = request.args.get("keyword", "")
        interval = max(int(request.args.get("interval", 60)), 10)  # min 10s
        platforms = request.args.getlist("platforms") or list(ALL_PROVIDERS.keys())
    except (KeyError, ValueError) as e:
        return jsonify({"error": str(e)}), 400

    params = SearchParams(
        latitude=lat, longitude=lng, radius_km=radius, keyword=keyword
    )

    def generate():
        seen_ids: set = set()
        while True:
            loop = get_or_create_event_loop()
            posts = loop.run_until_complete(run_search(params, platforms))
            new_posts = [p for p in posts if p["post_id"] not in seen_ids]
            for p in new_posts:
                seen_ids.add(p["post_id"])
            if new_posts:
                yield f"data: {json.dumps(new_posts)}\n\n"
            else:
                yield "data: []\n\n"
            time.sleep(interval)

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


if __name__ == "__main__":
    config.load_config()
    print("🌍 GeoFeed starting at http://localhost:5000")
    print("   Click the map or enter coordinates to search.")
    app.run(debug=True, port=5000)
