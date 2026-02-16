"""Tests for CLI commands."""

from unittest.mock import patch
from pathlib import Path
import sqlite3

from typer.testing import CliRunner

from grainlog.cli import app
from grainlog.db.schema import initialize_schema

runner = CliRunner()


def _make_conn(db_path):
    """Create a test connection."""
    c = sqlite3.connect(str(db_path))
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    initialize_schema(c)
    return c


class TestCLI:
    def test_config_show(self):
        result = runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0
        assert "Database" in result.output

    def test_config_set_and_show(self, tmp_path):
        config_toml = tmp_path / "config.toml"
        with patch("grainlog.cli.get_config_path", return_value=config_toml), \
             patch("grainlog.cli.set_config_value") as mock_set:
            result = runner.invoke(app, ["config", "set", "editor", "nano"])
            assert result.exit_code == 0
            assert "nano" in result.output

    def test_new_page(self, tmp_path):
        db = tmp_path / "test.db"
        with patch("grainlog.cli.get_connection", side_effect=lambda: _make_conn(db)):
            result = runner.invoke(app, ["new", "TestPage"])
            assert result.exit_code == 0
            assert "Created" in result.output

    def test_add_and_search(self, tmp_path):
        db = tmp_path / "test.db"
        with patch("grainlog.cli.get_connection", side_effect=lambda: _make_conn(db)):
            result = runner.invoke(app, ["add", "TestPage", "hello world"])
            assert result.exit_code == 0

            result = runner.invoke(app, ["search", "hello"])
            assert result.exit_code == 0
            assert "hello" in result.output

    def test_pages_list(self, tmp_path):
        db = tmp_path / "test.db"
        with patch("grainlog.cli.get_connection", side_effect=lambda: _make_conn(db)):
            runner.invoke(app, ["new", "Page1"])
            result = runner.invoke(app, ["pages"])
            assert result.exit_code == 0
            assert "Page1" in result.output

    def test_export(self, tmp_path):
        db = tmp_path / "test.db"
        export_dir = tmp_path / "export"
        with patch("grainlog.cli.get_connection", side_effect=lambda: _make_conn(db)):
            runner.invoke(app, ["add", "MyPage", "test content"])
            result = runner.invoke(app, ["export", "--output", str(export_dir)])
            assert result.exit_code == 0
            assert "Exported" in result.output

    def test_links(self, tmp_path):
        db = tmp_path / "test.db"
        with patch("grainlog.cli.get_connection", side_effect=lambda: _make_conn(db)):
            runner.invoke(app, ["add", "Source", "see [[Target]]"])
            result = runner.invoke(app, ["links", "Target"])
            assert result.exit_code == 0
            assert "Source" in result.output
