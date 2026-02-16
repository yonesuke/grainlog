"""Tests for Markdown export."""

from pathlib import Path

from grainlog.db.queries import create_block, create_page
from grainlog.export.markdown import export_all, export_page


class TestExport:
    def test_export_page_content(self, conn):
        pid = create_page(conn, "Test")
        create_block(conn, pid, "first", order=0)
        create_block(conn, pid, "second", order=1)
        md = export_page(conn, pid, "Test")
        assert "- first" in md
        assert "- second" in md

    def test_export_nested(self, conn):
        pid = create_page(conn, "Nested")
        b1 = create_block(conn, pid, "parent", order=0)
        create_block(conn, pid, "child", parent_id=b1, order=0)
        md = export_page(conn, pid, "Nested")
        assert "- parent" in md
        assert "  - child" in md

    def test_export_all_creates_files(self, conn, tmp_path):
        pid = create_page(conn, "Regular Page")
        create_block(conn, pid, "content", order=0)
        jpid = create_page(conn, "2026-02-17", is_journal=True, journal_date="2026-02-17")
        create_block(conn, jpid, "journal entry", order=0)

        count = export_all(conn, tmp_path)
        assert count == 2
        assert (tmp_path / "pages" / "Regular Page.md").exists()
        assert (tmp_path / "journals" / "2026_02_17.md").exists()

    def test_empty_page_not_exported(self, conn, tmp_path):
        create_page(conn, "Empty")
        count = export_all(conn, tmp_path)
        assert count == 0
