"""Tests for TODO/DONE block management."""

from grainlog.db.queries import (
    bulk_done_todos,
    clear_done_blocks,
    create_block,
    create_page,
    get_block_by_id,
    get_todo_blocks,
    toggle_todo_block,
)


class TestTodoQueries:
    def test_list_todos(self, conn):
        pid = create_page(conn, "P")
        create_block(conn, pid, "TODO task1", order=0)
        create_block(conn, pid, "DONE task2", order=1)
        create_block(conn, pid, "normal block", order=2)

        todos = get_todo_blocks(conn, status="todo")
        assert len(todos) == 1
        assert todos[0]["content"] == "TODO task1"

        dones = get_todo_blocks(conn, status="done")
        assert len(dones) == 1
        assert dones[0]["content"] == "DONE task2"

        both = get_todo_blocks(conn)
        assert len(both) == 2

    def test_list_todos_by_page(self, conn):
        p1 = create_page(conn, "Page1")
        p2 = create_page(conn, "Page2")
        create_block(conn, p1, "TODO from page1", order=0)
        create_block(conn, p2, "TODO from page2", order=0)

        results = get_todo_blocks(conn, status="todo", page_title="Page1")
        assert len(results) == 1
        assert results[0]["page_title"] == "Page1"

    def test_toggle_todo_to_done(self, conn):
        pid = create_page(conn, "P")
        bid = create_block(conn, pid, "TODO buy milk")
        result = toggle_todo_block(conn, bid)
        assert result == "done"
        assert get_block_by_id(conn, bid)["content"] == "DONE buy milk"

    def test_toggle_done_to_todo(self, conn):
        pid = create_page(conn, "P")
        bid = create_block(conn, pid, "DONE buy milk")
        result = toggle_todo_block(conn, bid)
        assert result == "todo"
        assert get_block_by_id(conn, bid)["content"] == "TODO buy milk"

    def test_toggle_non_todo_block(self, conn):
        pid = create_page(conn, "P")
        bid = create_block(conn, pid, "just a note")
        result = toggle_todo_block(conn, bid)
        assert result is None

    def test_toggle_nonexistent_block(self, conn):
        result = toggle_todo_block(conn, 9999)
        assert result is None

    def test_bulk_done(self, conn):
        pid = create_page(conn, "P")
        b1 = create_block(conn, pid, "TODO task1", order=0)
        b2 = create_block(conn, pid, "TODO task2", order=1)
        b3 = create_block(conn, pid, "DONE already", order=2)
        b4 = create_block(conn, pid, "normal block", order=3)

        count = bulk_done_todos(conn, [b1, b2, b3, b4])
        assert count == 2  # only TODO blocks changed
        assert get_block_by_id(conn, b1)["content"] == "DONE task1"
        assert get_block_by_id(conn, b2)["content"] == "DONE task2"
        assert get_block_by_id(conn, b3)["content"] == "DONE already"
        assert get_block_by_id(conn, b4)["content"] == "normal block"

    def test_clear_done(self, conn):
        pid = create_page(conn, "P")
        create_block(conn, pid, "TODO keep this", order=0)
        create_block(conn, pid, "DONE remove1", order=1)
        create_block(conn, pid, "DONE remove2", order=2)
        create_block(conn, pid, "normal keep", order=3)

        count = clear_done_blocks(conn)
        assert count == 2
        # Verify remaining
        todos = get_todo_blocks(conn, status="todo")
        assert len(todos) == 1
        dones = get_todo_blocks(conn, status="done")
        assert len(dones) == 0
