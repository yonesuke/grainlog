"""Tests for FTS5 full-text search."""

from grainlog.db.queries import create_block, create_page
from grainlog.db.search import search_blocks


class TestSearch:
    def test_basic_search(self, conn):
        pid = create_page(conn, "Notes")
        create_block(conn, pid, "hello world")
        create_block(conn, pid, "goodbye world")
        results = search_blocks(conn, "hello")
        assert len(results) == 1
        assert "hello" in results[0]["content"]

    def test_no_results(self, conn):
        pid = create_page(conn, "Notes")
        create_block(conn, pid, "hello")
        results = search_blocks(conn, "nonexistent")
        assert results == []

    def test_search_includes_page_title(self, conn):
        pid = create_page(conn, "My Page")
        create_block(conn, pid, "some content")
        results = search_blocks(conn, "content")
        assert results[0]["page_title"] == "My Page"

    def test_search_limit(self, conn):
        pid = create_page(conn, "P")
        for i in range(10):
            create_block(conn, pid, f"item number {i}", order=i)
        results = search_blocks(conn, "item", limit=3)
        assert len(results) == 3
