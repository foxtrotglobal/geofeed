"""Load configuration from config.yaml."""

import os
import sys
from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).parent / "config.yaml"

_config: dict = {}


def load_config(path: Path | None = None) -> dict:
    """Load and cache the YAML config file."""
    global _config
    p = path or CONFIG_PATH
    if not p.exists():
        print(f"[config] Warning: {p} not found. Copy config.yaml.example and fill in your keys.")
        _config = {}
        return _config
    with open(p) as f:
        _config = yaml.safe_load(f) or {}
    return _config


def get(section: str, key: str, default: str = "") -> str:
    """Get a config value, falling back to environment variables then default."""
    if not _config:
        load_config()
    # Try config file first
    val = _config.get(section, {}).get(key, "")
    if val:
        return str(val)
    # Try environment variable: SECTION_KEY (e.g. YOUTUBE_API_KEY)
    env_key = f"{section.upper()}_{key.upper()}"
    return os.environ.get(env_key, default)
