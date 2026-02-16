"""Configuration and path management."""

from __future__ import annotations

from pathlib import Path

from platformdirs import user_config_dir, user_data_dir

APP_NAME = "grainlog"

DEFAULT_DAILY_TEMPLATE = """\
TODO
読んだもの
メモ
"""


def get_data_dir() -> Path:
    """Return the OS-appropriate data directory, creating it if needed."""
    return Path(user_data_dir(APP_NAME, ensure_exists=True))


def get_config_dir() -> Path:
    """Return the OS-appropriate config directory, creating it if needed."""
    return Path(user_config_dir(APP_NAME, ensure_exists=True))


def get_db_path() -> Path:
    """Return the path to the SQLite database file."""
    return get_data_dir() / "grainlog.db"


def get_templates_dir() -> Path:
    """Return the templates directory, creating it if needed."""
    d = get_config_dir() / "templates"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_daily_template() -> str:
    """Load daily template from config or return default."""
    path = get_templates_dir() / "daily.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return DEFAULT_DAILY_TEMPLATE


def save_default_daily_template() -> Path:
    """Write the default daily template to config dir and return the path."""
    path = get_templates_dir() / "daily.md"
    if not path.exists():
        path.write_text(DEFAULT_DAILY_TEMPLATE, encoding="utf-8")
    return path
