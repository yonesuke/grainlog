"""Configuration and path management."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

from platformdirs import user_config_dir, user_data_dir

APP_NAME = "grainlog"

DEFAULT_DAILY_TEMPLATE = """\
TODO
読んだもの
メモ
"""

DEFAULTS: dict[str, str] = {
    "editor": "vi",
}


# ---------------------------------------------------------------------------
# Directories
# ---------------------------------------------------------------------------

def get_data_dir() -> Path:
    """Return the OS-appropriate data directory, creating it if needed."""
    return Path(user_data_dir(APP_NAME, ensure_exists=True))


def get_config_dir() -> Path:
    """Return the OS-appropriate config directory, creating it if needed."""
    return Path(user_config_dir(APP_NAME, ensure_exists=True))


def get_db_path() -> Path:
    """Return the path to the SQLite database file."""
    return get_data_dir() / "grainlog.db"


# ---------------------------------------------------------------------------
# config.toml
# ---------------------------------------------------------------------------

def get_config_path() -> Path:
    """Return the path to config.toml."""
    return get_config_dir() / "config.toml"


def load_config() -> dict[str, Any]:
    """Load config.toml and return as dict. Returns empty dict if not found."""
    path = get_config_path()
    if not path.exists():
        return {}
    with open(path, "rb") as f:
        return tomllib.load(f)


def get_config_value(key: str) -> str:
    """Get a config value. Priority: config.toml > env var > default."""
    cfg = load_config()
    if key in cfg:
        return str(cfg[key])
    # For "editor", also check $EDITOR
    if key == "editor":
        env_val = os.environ.get("EDITOR")
        if env_val:
            return env_val
    return DEFAULTS.get(key, "")


def set_config_value(key: str, value: str) -> None:
    """Set a config value in config.toml."""
    path = get_config_path()
    cfg = load_config()
    cfg[key] = value
    _write_config(cfg, path)


def unset_config_value(key: str) -> bool:
    """Remove a key from config.toml. Returns True if key existed."""
    path = get_config_path()
    cfg = load_config()
    if key not in cfg:
        return False
    del cfg[key]
    _write_config(cfg, path)
    return True


def _write_config(cfg: dict[str, Any], path: Path) -> None:
    """Write config dict as TOML to path."""
    lines: list[str] = []
    for k, v in sorted(cfg.items()):
        if isinstance(v, bool):
            lines.append(f"{k} = {'true' if v else 'false'}")
        elif isinstance(v, int):
            lines.append(f"{k} = {v}")
        else:
            lines.append(f'{k} = "{v}"')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def get_editor() -> str:
    """Return the editor command to use."""
    return get_config_value("editor")


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

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
