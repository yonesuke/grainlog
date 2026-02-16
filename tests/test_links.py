"""Tests for link parsing and synchronization."""

from grainlog.core.links import parse_links, sync_links_for_block
from grainlog.db.queries import create_block, create_page, get_backlinks, get_forward_links


class TestParsing:
    def test_single_link(self):
        assert parse_links("Hello [[world]]") == ["world"]

    def test_multiple_links(self):
        assert parse_links("[[a]] and [[b]]") == ["a", "b"]

    def test_no_links(self):
        assert parse_links("plain text") == []

    def test_nested_brackets_ignored(self):
        assert parse_links("[[[not a link]]]") == ["not a link"]


class TestLinkSync:
    def test_sync_creates_target_page(self, conn):
        pid = create_page(conn, "Source")
        bid = create_block(conn, pid, "see [[Target]]")
        sync_links_for_block(conn, bid, pid, "see [[Target]]")
        from grainlog.db.queries import get_page_by_title
        assert get_page_by_title(conn, "Target") is not None

    def test_backlinks(self, conn):
        src_pid = create_page(conn, "Source")
        tgt_pid = create_page(conn, "Target")
        bid = create_block(conn, src_pid, "link to [[Target]]")
        sync_links_for_block(conn, bid, src_pid, "link to [[Target]]")
        backlinks = get_backlinks(conn, tgt_pid)
        assert len(backlinks) == 1
        assert backlinks[0]["source_page_title"] == "Source"

    def test_forward_links(self, conn):
        src_pid = create_page(conn, "Source")
        create_page(conn, "A")
        create_page(conn, "B")
        bid = create_block(conn, src_pid, "see [[A]] and [[B]]")
        sync_links_for_block(conn, bid, src_pid, "see [[A]] and [[B]]")
        flinks = get_forward_links(conn, src_pid)
        titles = [f["target_title"] for f in flinks]
        assert "A" in titles
        assert "B" in titles
