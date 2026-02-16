"""Tests for #tag parsing and sync."""

from grainlog.core.links import parse_tags, sync_links_for_block
from grainlog.db.queries import (
    create_block,
    create_page,
    get_blocks_by_tag,
    list_all_tags,
)


class TestTagParsing:
    def test_single_tag(self):
        assert parse_tags("hello #world") == ["world"]

    def test_multiple_tags(self):
        assert parse_tags("#foo bar #baz") == ["foo", "baz"]

    def test_no_tags(self):
        assert parse_tags("plain text") == []

    def test_tag_at_start(self):
        assert parse_tags("#start of line") == ["start"]

    def test_tag_with_numbers(self):
        assert parse_tags("#item123") == ["item123"]

    def test_tag_with_underscore(self):
        assert parse_tags("#my_tag") == ["my_tag"]

    def test_tag_with_hyphen(self):
        assert parse_tags("#my-tag") == ["my-tag"]

    def test_japanese_tag(self):
        assert parse_tags("#日本語タグ") == ["日本語タグ"]

    def test_no_tag_if_no_space_before(self):
        # e.g. "issue#123" should not match
        assert parse_tags("issue#123") == []

    def test_hash_only_no_match(self):
        assert parse_tags("# heading") == []


class TestTagSync:
    def test_sync_creates_tags(self, conn):
        pid = create_page(conn, "Source")
        bid = create_block(conn, pid, "hello #world #test")
        sync_links_for_block(conn, bid, pid, "hello #world #test")
        tags = list_all_tags(conn)
        names = [t["name"] for t in tags]
        assert "world" in names
        assert "test" in names

    def test_blocks_by_tag(self, conn):
        pid = create_page(conn, "P1")
        b1 = create_block(conn, pid, "item #todo", order=0)
        sync_links_for_block(conn, b1, pid, "item #todo")
        b2 = create_block(conn, pid, "other #done", order=1)
        sync_links_for_block(conn, b2, pid, "other #done")
        results = get_blocks_by_tag(conn, "todo")
        assert len(results) == 1
        assert results[0]["content"] == "item #todo"

    def test_tag_count(self, conn):
        pid = create_page(conn, "P1")
        for i in range(3):
            bid = create_block(conn, pid, f"item{i} #common", order=i)
            sync_links_for_block(conn, bid, pid, f"item{i} #common")
        tags = list_all_tags(conn)
        common = [t for t in tags if t["name"] == "common"]
        assert common[0]["count"] == 3

    def test_tag_resync_on_update(self, conn):
        pid = create_page(conn, "P1")
        bid = create_block(conn, pid, "#old content")
        sync_links_for_block(conn, bid, pid, "#old content")
        assert len(get_blocks_by_tag(conn, "old")) == 1

        # Re-sync with new content
        sync_links_for_block(conn, bid, pid, "#new content")
        assert len(get_blocks_by_tag(conn, "old")) == 0
        assert len(get_blocks_by_tag(conn, "new")) == 1
