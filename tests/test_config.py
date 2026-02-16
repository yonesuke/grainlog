"""Tests for config.toml management."""

from unittest.mock import patch

from grainlog.config import (
    get_config_value,
    get_editor,
    load_config,
    set_config_value,
    unset_config_value,
)


class TestConfig:
    def test_default_editor(self, tmp_path):
        path = tmp_path / "config.toml"
        with patch("grainlog.config.get_config_path", return_value=path), \
             patch.dict("os.environ", {}, clear=True):
            assert get_config_value("editor") == "vi"

    def test_env_editor_overrides_default(self, tmp_path):
        path = tmp_path / "config.toml"
        with patch("grainlog.config.get_config_path", return_value=path), \
             patch.dict("os.environ", {"EDITOR": "nano"}):
            assert get_config_value("editor") == "nano"

    def test_config_toml_overrides_env(self, tmp_path):
        path = tmp_path / "config.toml"
        path.write_text('editor = "code"\n', encoding="utf-8")
        with patch("grainlog.config.get_config_path", return_value=path), \
             patch.dict("os.environ", {"EDITOR": "nano"}):
            assert get_config_value("editor") == "code"

    def test_set_config_value(self, tmp_path):
        path = tmp_path / "config.toml"
        with patch("grainlog.config.get_config_path", return_value=path):
            set_config_value("editor", "vim")
            assert load_config()["editor"] == "vim"

    def test_set_multiple_values(self, tmp_path):
        path = tmp_path / "config.toml"
        with patch("grainlog.config.get_config_path", return_value=path):
            set_config_value("editor", "vim")
            set_config_value("theme", "dark")
            cfg = load_config()
            assert cfg["editor"] == "vim"
            assert cfg["theme"] == "dark"

    def test_unset_config_value(self, tmp_path):
        path = tmp_path / "config.toml"
        with patch("grainlog.config.get_config_path", return_value=path):
            set_config_value("editor", "vim")
            assert unset_config_value("editor") is True
            assert "editor" not in load_config()

    def test_unset_nonexistent_key(self, tmp_path):
        path = tmp_path / "config.toml"
        with patch("grainlog.config.get_config_path", return_value=path):
            assert unset_config_value("nosuchkey") is False

    def test_get_editor_uses_config(self, tmp_path):
        path = tmp_path / "config.toml"
        path.write_text('editor = "code"\n', encoding="utf-8")
        with patch("grainlog.config.get_config_path", return_value=path):
            assert get_editor() == "code"

    def test_load_empty_config(self, tmp_path):
        path = tmp_path / "config.toml"
        with patch("grainlog.config.get_config_path", return_value=path):
            assert load_config() == {}
