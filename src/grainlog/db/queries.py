"""CRUD operations for pages, blocks, and links."""

from __future__ import annotations

import sqlite3
from datetime import datetime


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

def create_page(
    conn: sqlite3.Connection,
    title: str,
    *,
    is_journal: bool = False,
    journal_date: str | None = None,
) -> int:
    """Insert a new page and return its id."""
    cur = conn.execute(
        "INSERT INTO pages (title, is_journal, journal_date) VALUES (?, ?, ?)",
        (title, int(is_journal), journal_date),
    )
    conn.commit()
    return cur.lastrowid  # type: ignore[return-value]


def get_page_by_title(conn: sqlite3.Connection, title: str) -> sqlite3.Row | None:
    """Return a page row by title, or None."""
    return conn.execute("SELECT * FROM pages WHERE title = ?", (title,)).fetchone()


def get_page_by_id(conn: sqlite3.Connection, page_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM pages WHERE id = ?", (page_id,)).fetchone()


def get_or_create_page(
    conn: sqlite3.Connection,
    title: str,
    *,
    is_journal: bool = False,
    journal_date: str | None = None,
) -> int:
    """Return existing page id or create a new one."""
    row = get_page_by_title(conn, title)
    if row:
        return row["id"]
    return create_page(conn, title, is_journal=is_journal, journal_date=journal_date)


def list_pages(conn: sqlite3.Connection, *, journals_only: bool = False) -> list[sqlite3.Row]:
    if journals_only:
        return conn.execute(
            "SELECT * FROM pages WHERE is_journal = 1 ORDER BY journal_date DESC"
        ).fetchall()
    return conn.execute("SELECT * FROM pages ORDER BY updated_at DESC").fetchall()


def delete_page(conn: sqlite3.Connection, page_id: int) -> None:
    conn.execute("DELETE FROM pages WHERE id = ?", (page_id,))
    conn.commit()


# ---------------------------------------------------------------------------
# Blocks
# ---------------------------------------------------------------------------

def create_block(
    conn: sqlite3.Connection,
    page_id: int,
    content: str,
    *,
    parent_id: int | None = None,
    order: int = 0,
) -> int:
    """Insert a block and return its id."""
    cur = conn.execute(
        'INSERT INTO blocks (page_id, parent_id, content, "order") VALUES (?, ?, ?, ?)',
        (page_id, parent_id, content, order),
    )
    conn.commit()
    return cur.lastrowid  # type: ignore[return-value]


def get_blocks_for_page(
    conn: sqlite3.Connection, page_id: int, *, parent_id: int | None = None
) -> list[sqlite3.Row]:
    """Return child blocks ordered by 'order'."""
    return conn.execute(
        'SELECT * FROM blocks WHERE page_id = ? AND parent_id IS ? ORDER BY "order"',
        (page_id, parent_id),
    ).fetchall()


def get_block_by_id(conn: sqlite3.Connection, block_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM blocks WHERE id = ?", (block_id,)).fetchone()


def update_block_content(conn: sqlite3.Connection, block_id: int, content: str) -> None:
    conn.execute(
        "UPDATE blocks SET content = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id = ?",
        (content, block_id),
    )
    conn.commit()


def delete_block(conn: sqlite3.Connection, block_id: int) -> None:
    conn.execute("DELETE FROM blocks WHERE id = ?", (block_id,))
    conn.commit()


def next_order(conn: sqlite3.Connection, page_id: int, parent_id: int | None = None) -> int:
    """Return the next available order value for sibling blocks."""
    row = conn.execute(
        'SELECT COALESCE(MAX("order"), -1) + 1 AS next_ord FROM blocks WHERE page_id = ? AND parent_id IS ?',
        (page_id, parent_id),
    ).fetchone()
    return row["next_ord"]


# ---------------------------------------------------------------------------
# Links
# ---------------------------------------------------------------------------

def replace_links_for_block(
    conn: sqlite3.Connection,
    block_id: int,
    source_page_id: int,
    targets: list[tuple[int, str]],
) -> None:
    """Delete existing links for a block and insert new ones."""
    conn.execute("DELETE FROM links WHERE source_block_id = ?", (block_id,))
    for target_page_id, target_title in targets:
        conn.execute(
            "INSERT INTO links (source_block_id, source_page_id, target_page_id, target_title) VALUES (?, ?, ?, ?)",
            (block_id, source_page_id, target_page_id, target_title),
        )
    conn.commit()


def get_backlinks(conn: sqlite3.Connection, page_id: int) -> list[sqlite3.Row]:
    """Return blocks that link *to* the given page, with source page info."""
    return conn.execute(
        """
        SELECT l.*, b.content AS block_content, p.title AS source_page_title
        FROM links l
        JOIN blocks b ON b.id = l.source_block_id
        JOIN pages p ON p.id = l.source_page_id
        WHERE l.target_page_id = ?
        ORDER BY b.created_at DESC
        """,
        (page_id,),
    ).fetchall()


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------

def replace_tags_for_block(
    conn: sqlite3.Connection,
    block_id: int,
    page_id: int,
    tag_names: list[str],
) -> None:
    """Delete existing tags for a block and insert new ones."""
    conn.execute("DELETE FROM tags WHERE block_id = ?", (block_id,))
    for name in tag_names:
        conn.execute(
            "INSERT INTO tags (block_id, page_id, name) VALUES (?, ?, ?)",
            (block_id, page_id, name),
        )
    conn.commit()


def list_all_tags(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Return all unique tag names with usage counts."""
    return conn.execute(
        "SELECT name, COUNT(*) AS count FROM tags GROUP BY name ORDER BY count DESC, name"
    ).fetchall()


def get_blocks_by_tag(conn: sqlite3.Connection, tag_name: str) -> list[sqlite3.Row]:
    """Return blocks that have a specific tag, with page info."""
    return conn.execute(
        """
        SELECT t.name, b.id AS block_id, b.content, p.title AS page_title
        FROM tags t
        JOIN blocks b ON b.id = t.block_id
        JOIN pages p ON p.id = t.page_id
        WHERE t.name = ?
        ORDER BY b.created_at DESC
        """,
        (tag_name,),
    ).fetchall()


# ---------------------------------------------------------------------------
# TODO blocks
# ---------------------------------------------------------------------------

def get_todo_blocks(
    conn: sqlite3.Connection,
    *,
    status: str | None = None,
    page_title: str | None = None,
) -> list[sqlite3.Row]:
    """Return blocks starting with TODO or DONE markers.

    status: 'todo', 'done', or None for both.
    page_title: filter by page title if given.
    """
    conditions = []
    params: list[str] = []
    if status == "todo":
        conditions.append("b.content LIKE 'TODO %'")
    elif status == "done":
        conditions.append("b.content LIKE 'DONE %'")
    else:
        conditions.append("(b.content LIKE 'TODO %' OR b.content LIKE 'DONE %')")
    if page_title:
        conditions.append("p.title = ?")
        params.append(page_title)
    where = " AND ".join(conditions)
    return conn.execute(
        f"""
        SELECT b.id, b.page_id, b.content, p.title AS page_title
        FROM blocks b
        JOIN pages p ON p.id = b.page_id
        WHERE {where}
        ORDER BY b.created_at DESC
        """,
        params,
    ).fetchall()


def toggle_todo_block(conn: sqlite3.Connection, block_id: int) -> str | None:
    """Toggle a block between TODO and DONE. Returns new state or None."""
    row = conn.execute("SELECT content FROM blocks WHERE id = ?", (block_id,)).fetchone()
    if not row:
        return None
    content: str = row["content"]
    if content.startswith("TODO "):
        new_content = "DONE " + content[5:]
    elif content.startswith("DONE "):
        new_content = "TODO " + content[5:]
    else:
        return None
    conn.execute(
        "UPDATE blocks SET content = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id = ?",
        (new_content, block_id),
    )
    conn.commit()
    return "done" if new_content.startswith("DONE ") else "todo"


def bulk_done_todos(conn: sqlite3.Connection, block_ids: list[int]) -> int:
    """Mark multiple TODO blocks as DONE. Returns count of changed blocks."""
    count = 0
    for bid in block_ids:
        row = conn.execute("SELECT content FROM blocks WHERE id = ?", (bid,)).fetchone()
        if row and row["content"].startswith("TODO "):
            conn.execute(
                "UPDATE blocks SET content = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id = ?",
                ("DONE " + row["content"][5:], bid),
            )
            count += 1
    conn.commit()
    return count


def clear_done_blocks(conn: sqlite3.Connection) -> int:
    """Delete all DONE blocks. Returns count of deleted blocks."""
    cur = conn.execute("SELECT COUNT(*) AS cnt FROM blocks WHERE content LIKE 'DONE %'")
    count = cur.fetchone()["cnt"]
    conn.execute("DELETE FROM blocks WHERE content LIKE 'DONE %'")
    conn.commit()
    return count


def get_forward_links(conn: sqlite3.Connection, page_id: int) -> list[sqlite3.Row]:
    """Return links originating from the given page."""
    return conn.execute(
        """
        SELECT DISTINCT l.target_page_id, l.target_title
        FROM links l
        WHERE l.source_page_id = ?
        ORDER BY l.target_title
        """,
        (page_id,),
    ).fetchall()
