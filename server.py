"""Flask web server for GeoFeed — serves the map UI and search API."""

import asyncio
import sys
from pathlib import Path

from flask import Flask, jsonify, render_template, request

# Ensure the project root is on the path
sys.path.insert(0, str(Path(__file__).parent))

import config
from models import SearchParams
from providers.youtube import YouTubeProvider
from providers.flickr import FlickrProvider
from providers.instagram import InstagramProvider
from providers.twitter import TwitterProvider
from providers.tiktok import TikTokProvider

app = Flask(__name__)

# Registry of all providers
ALL_PROVIDERS = {
    "youtube": YouTubeProvider,
    "flickr": FlickrProvider,
    "instagram": InstagramProvider,
    "twitter": TwitterProvider,
    "tiktok": TikTokProvider,
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


@app.route("/api/providers")
def list_providers():
    """List available providers and whether they are configured."""
    result = {}
    for name, cls in ALL_PROVIDERS.items():
        p = cls()
        result[name] = {"configured": p.is_configured(), "color": p.color}
    return jsonify(result)


if __name__ == "__main__":
    config.load_config()
    print("🌍 GeoFeed starting at http://localhost:5000")
    print("   Click the map or enter coordinates to search.")
    app.run(debug=True, port=5000)
