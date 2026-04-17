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
    """Get a config value. Environment variables take precedence over config.yaml."""
    if not _config:
        load_config()
    # Check environment variable first — allows production secrets to override config.yaml
    env_key = f"{section.upper()}_{key.upper()}"
    env_val = os.environ.get(env_key, "")
    if env_val:
        return env_val
    # Fall back to config file
    val = _config.get(section, {}).get(key, "")
    if val:
        return str(val)
    return default
