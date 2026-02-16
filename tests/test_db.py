"""Tests for database CRUD operations."""

from grainlog.db.queries import (
    create_block,
    create_page,
    delete_block,
    delete_page,
    get_blocks_for_page,
    get_or_create_page,
    get_page_by_id,
    get_page_by_title,
    list_pages,
    next_order,
    update_block_content,
)


class TestPages:
    def test_create_and_get(self, conn):
        pid = create_page(conn, "Test Page")
        page = get_page_by_id(conn, pid)
        assert page["title"] == "Test Page"
        assert page["is_journal"] == 0

    def test_create_journal(self, conn):
        pid = create_page(conn, "2026-02-17", is_journal=True, journal_date="2026-02-17")
        page = get_page_by_id(conn, pid)
        assert page["is_journal"] == 1
        assert page["journal_date"] == "2026-02-17"

    def test_get_by_title(self, conn):
        create_page(conn, "Alpha")
        page = get_page_by_title(conn, "Alpha")
        assert page is not None
        assert page["title"] == "Alpha"

    def test_get_or_create(self, conn):
        id1 = get_or_create_page(conn, "New")
        id2 = get_or_create_page(conn, "New")
        assert id1 == id2

    def test_list_pages(self, conn):
        create_page(conn, "A")
        create_page(conn, "B")
        create_page(conn, "J", is_journal=True, journal_date="2026-01-01")
        assert len(list_pages(conn)) == 3
        assert len(list_pages(conn, journals_only=True)) == 1

    def test_delete_page(self, conn):
        pid = create_page(conn, "Deleteme")
        delete_page(conn, pid)
        assert get_page_by_id(conn, pid) is None


class TestBlocks:
    def test_create_and_get(self, conn):
        pid = create_page(conn, "P")
        bid = create_block(conn, pid, "Hello", order=0)
        blocks = get_blocks_for_page(conn, pid)
        assert len(blocks) == 1
        assert blocks[0]["content"] == "Hello"

    def test_nested_blocks(self, conn):
        pid = create_page(conn, "P")
        b1 = create_block(conn, pid, "Parent", order=0)
        b2 = create_block(conn, pid, "Child", parent_id=b1, order=0)
        roots = get_blocks_for_page(conn, pid, parent_id=None)
        children = get_blocks_for_page(conn, pid, parent_id=b1)
        assert len(roots) == 1
        assert len(children) == 1

    def test_update_content(self, conn):
        pid = create_page(conn, "P")
        bid = create_block(conn, pid, "old")
        update_block_content(conn, bid, "new")
        from grainlog.db.queries import get_block_by_id
        assert get_block_by_id(conn, bid)["content"] == "new"

    def test_delete_block(self, conn):
        pid = create_page(conn, "P")
        bid = create_block(conn, pid, "bye")
        delete_block(conn, bid)
        assert get_blocks_for_page(conn, pid) == []

    def test_next_order(self, conn):
        pid = create_page(conn, "P")
        assert next_order(conn, pid) == 0
        create_block(conn, pid, "a", order=0)
        assert next_order(conn, pid) == 1
