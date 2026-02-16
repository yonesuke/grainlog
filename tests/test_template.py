"""Tests for daily template functionality."""

from datetime import date
from unittest.mock import patch

from grainlog.core.daily import get_or_create_daily, journal_title
from grainlog.db.queries import create_page, get_blocks_for_page, get_page_by_title


class TestTemplate:
    def test_new_daily_applies_template(self, conn):
        """New daily page should have template blocks inserted."""
        with patch("grainlog.core.daily.get_daily_template", return_value="TODO\nメモ\n"):
            page_id = get_or_create_daily(conn, date(2026, 3, 1))
        blocks = get_blocks_for_page(conn, page_id)
        contents = [b["content"] for b in blocks]
        assert "TODO" in contents
        assert "メモ" in contents

    def test_existing_daily_no_duplicate_template(self, conn):
        """Reopening an existing daily should NOT re-insert template blocks."""
        with patch("grainlog.core.daily.get_daily_template", return_value="TODO\n"):
            page_id1 = get_or_create_daily(conn, date(2026, 3, 2))
            page_id2 = get_or_create_daily(conn, date(2026, 3, 2))
        assert page_id1 == page_id2
        blocks = get_blocks_for_page(conn, page_id1)
        assert len(blocks) == 1  # template applied only once

    def test_custom_template(self, conn):
        """Custom template content should be applied."""
        custom = "- 朝の振り返り\n- 読書メモ\n- タスク\n"
        with patch("grainlog.core.daily.get_daily_template", return_value=custom):
            page_id = get_or_create_daily(conn, date(2026, 3, 3))
        blocks = get_blocks_for_page(conn, page_id)
        contents = [b["content"] for b in blocks]
        assert "朝の振り返り" in contents
        assert "読書メモ" in contents
        assert "タスク" in contents

    def test_empty_template(self, conn):
        """Empty template should create a page with no blocks."""
        with patch("grainlog.core.daily.get_daily_template", return_value=""):
            page_id = get_or_create_daily(conn, date(2026, 3, 4))
        blocks = get_blocks_for_page(conn, page_id)
        assert len(blocks) == 0
