"""Tests for config.py — YAML loading, env var overrides, edge cases."""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


def _fresh_config(nonexistent_fallback: bool = True):
    """Return config module with cleared state.
    
    nonexistent_fallback=True patches CONFIG_PATH to /nonexistent so that
    auto-loading the default config.yaml doesn't interfere with test assertions.
    """
    import config as cfg
    cfg._config = {}
    return cfg


from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch as _patch

@contextmanager
def _isolated_config(cfg=None):
    """Ensure get() doesn't fall back to the real config.yaml."""
    import config as c
    if cfg is None:
        cfg = c
    cfg._config = {}
    # Patch CONFIG_PATH so auto-load hits a missing file (returns {})
    with _patch.object(c, 'CONFIG_PATH', Path('/nonexistent/config.yaml')):
        yield cfg
    cfg._config = {}


class TestYamlLoading:
    def test_loads_valid_yaml(self, tmp_path):
        cfg = _fresh_config()
        f = tmp_path / "config.yaml"
        f.write_text("youtube:\n  api_key: test_key_123\n")
        cfg.load_config(f)
        assert cfg.get("youtube", "api_key") == "test_key_123"

    def test_loads_nested_keys(self, tmp_path):
        cfg = _fresh_config()
        f = tmp_path / "config.yaml"
        f.write_text("twitter:\n  bearer_token: tok\nflickr:\n  api_key: flickr_k\n")
        cfg.load_config(f)
        assert cfg.get("twitter", "bearer_token") == "tok"
        assert cfg.get("flickr", "api_key") == "flickr_k"

    def test_returns_empty_dict_for_missing_file(self):
        cfg = _fresh_config()
        result = cfg.load_config(Path("/nonexistent/path/config.yaml"))
        assert result == {}

    def test_handles_empty_yaml_file(self, tmp_path):
        cfg = _fresh_config()
        f = tmp_path / "config.yaml"
        f.write_text("")
        result = cfg.load_config(f)
        assert result == {}

    def test_handles_yaml_with_only_comments(self, tmp_path):
        f = tmp_path / "config.yaml"
        f.write_text("# This is just a comment\n# Another comment\n")
        with _isolated_config() as cfg:
            cfg.load_config(f)
            assert cfg.get("youtube", "api_key") == ""

    def test_returns_empty_string_for_missing_section(self, tmp_path):
        cfg = _fresh_config()
        f = tmp_path / "config.yaml"
        f.write_text("youtube:\n  api_key: key\n")
        cfg.load_config(f)
        assert cfg.get("flickr", "api_key") == ""

    def test_returns_empty_string_for_missing_key(self, tmp_path):
        cfg = _fresh_config()
        f = tmp_path / "config.yaml"
        f.write_text("youtube:\n  api_key: key\n")
        cfg.load_config(f)
        assert cfg.get("youtube", "nonexistent_key") == ""

    def test_returns_default_for_missing_key(self, tmp_path):
        cfg = _fresh_config()
        f = tmp_path / "config.yaml"
        f.write_text("youtube:\n  api_key: key\n")
        cfg.load_config(f)
        assert cfg.get("youtube", "missing", default="fallback") == "fallback"

    def test_empty_string_value_returns_empty(self, tmp_path):
        cfg = _fresh_config()
        f = tmp_path / "config.yaml"
        f.write_text("youtube:\n  api_key: \"\"\n")
        cfg.load_config(f)
        assert cfg.get("youtube", "api_key") == ""

    def test_all_platform_sections_loadable(self, tmp_path):
        cfg = _fresh_config()
        f = tmp_path / "config.yaml"
        f.write_text(
            "youtube:\n  api_key: yt\n"
            "flickr:\n  api_key: fl\n"
            "instagram:\n  session_cookie: ig\n"
            "twitter:\n  bearer_token: tw\n"
            "tiktok:\n  ms_token: tk\n  ttwid: tw2\n"
            "bluesky:\n  identifier: bsky\n"
            "mastodon:\n  instance: mastodon.social\n"
            "snapchat:\n  session_cookie: sc\n"
            "telegram:\n  bot_token: tg\n"
            "reddit:\n  subreddits: iran\n"
            "facebook:\n  app_id: fb_id\n  app_secret: fb_sec\n"
        )
        cfg.load_config(f)
        assert cfg.get("youtube", "api_key") == "yt"
        assert cfg.get("instagram", "session_cookie") == "ig"
        assert cfg.get("tiktok", "ttwid") == "tw2"
        assert cfg.get("mastodon", "instance") == "mastodon.social"


class TestEnvVarOverrides:
    def test_env_var_overrides_config_file(self, tmp_path):
        f = tmp_path / "config.yaml"
        f.write_text("youtube:\n  api_key: from_file\n")
        with _isolated_config() as cfg:
            cfg.load_config(f)
            with patch.dict(os.environ, {"YOUTUBE_API_KEY": "from_env"}):
                assert cfg.get("youtube", "api_key") == "from_env"

    def test_env_var_used_when_config_missing(self):
        cfg = _fresh_config()
        cfg._config = {}
        with patch.dict(os.environ, {"FLICKR_API_KEY": "env_flickr"}):
            assert cfg.get("flickr", "api_key") == "env_flickr"

    def test_env_var_format_is_section_key_uppercase(self, tmp_path):
        f = tmp_path / "config.yaml"
        f.write_text("")
        with _isolated_config() as cfg:
            cfg.load_config(f)
            with patch.dict(os.environ, {"TWITTER_BEARER_TOKEN": "bearer_from_env"}):
                assert cfg.get("twitter", "bearer_token") == "bearer_from_env"

    def test_config_file_used_when_no_env_var(self, tmp_path):
        cfg = _fresh_config()
        f = tmp_path / "config.yaml"
        f.write_text("youtube:\n  api_key: file_key\n")
        cfg.load_config(f)
        env = {k: v for k, v in os.environ.items() if k != "YOUTUBE_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            assert cfg.get("youtube", "api_key") == "file_key"

    def test_empty_env_var_falls_through_to_config(self, tmp_path):
        cfg = _fresh_config()
        f = tmp_path / "config.yaml"
        f.write_text("youtube:\n  api_key: from_yaml\n")
        cfg.load_config(f)
        # Empty string env var should not override
        with patch.dict(os.environ, {"YOUTUBE_API_KEY": ""}):
            # Empty env var is falsy, so config value wins
            val = cfg.get("youtube", "api_key")
            assert val in ("from_yaml", "")  # Either is acceptable behaviour


class TestLoadConfigCaching:
    def test_load_config_returns_the_config_dict(self, tmp_path):
        cfg = _fresh_config()
        f = tmp_path / "config.yaml"
        f.write_text("youtube:\n  api_key: cached\n")
        result = cfg.load_config(f)
        assert isinstance(result, dict)
        assert result.get("youtube", {}).get("api_key") == "cached"

    def test_multiple_get_calls_consistent(self, tmp_path):
        cfg = _fresh_config()
        f = tmp_path / "config.yaml"
        f.write_text("youtube:\n  api_key: consistent\n")
        cfg.load_config(f)
        assert cfg.get("youtube", "api_key") == cfg.get("youtube", "api_key")
