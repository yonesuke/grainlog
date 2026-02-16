"""Block tree operations (indent, dedent, move, tree building)."""

from __future__ import annotations

import sqlite3

from grainlog.core.models import Block
from grainlog.db.queries import get_blocks_for_page


def build_block_tree(conn: sqlite3.Connection, page_id: int) -> list[Block]:
    """Build a nested block tree for a page."""

    def _children(parent_id: int | None) -> list[Block]:
        rows = get_blocks_for_page(conn, page_id, parent_id=parent_id)
        blocks: list[Block] = []
        for r in rows:
            b = Block(
                id=r["id"],
                page_id=r["page_id"],
                content=r["content"],
                parent_id=r["parent_id"],
                order=r["order"],
                collapsed=bool(r["collapsed"]),
                created_at=r["created_at"],
                updated_at=r["updated_at"],
            )
            b.children = _children(b.id)
            blocks.append(b)
        return blocks

    return _children(None)


def indent_block(conn: sqlite3.Connection, block_id: int) -> bool:
    """Make a block a child of its previous sibling. Returns True on success."""
    block = conn.execute("SELECT * FROM blocks WHERE id = ?", (block_id,)).fetchone()
    if not block:
        return False
    prev_sibling = conn.execute(
        'SELECT * FROM blocks WHERE page_id = ? AND parent_id IS ? AND "order" < ? ORDER BY "order" DESC LIMIT 1',
        (block["page_id"], block["parent_id"], block["order"]),
    ).fetchone()
    if not prev_sibling:
        return False
    new_order_row = conn.execute(
        'SELECT COALESCE(MAX("order"), -1) + 1 AS next_ord FROM blocks WHERE parent_id = ?',
        (prev_sibling["id"],),
    ).fetchone()
    conn.execute(
        'UPDATE blocks SET parent_id = ?, "order" = ?, updated_at = strftime(\'%Y-%m-%dT%H:%M:%fZ\',\'now\') WHERE id = ?',
        (prev_sibling["id"], new_order_row["next_ord"], block_id),
    )
    conn.commit()
    return True


def dedent_block(conn: sqlite3.Connection, block_id: int) -> bool:
    """Move a block up one level (make it a sibling of its parent). Returns True on success."""
    block = conn.execute("SELECT * FROM blocks WHERE id = ?", (block_id,)).fetchone()
    if not block or block["parent_id"] is None:
        return False
    parent = conn.execute("SELECT * FROM blocks WHERE id = ?", (block["parent_id"],)).fetchone()
    if not parent:
        return False
    new_order_row = conn.execute(
        'SELECT COALESCE(MAX("order"), -1) + 1 AS next_ord FROM blocks WHERE page_id = ? AND parent_id IS ?',
        (block["page_id"], parent["parent_id"]),
    ).fetchone()
    conn.execute(
        'UPDATE blocks SET parent_id = ?, "order" = ?, updated_at = strftime(\'%Y-%m-%dT%H:%M:%fZ\',\'now\') WHERE id = ?',
        (parent["parent_id"], new_order_row["next_ord"], block_id),
    )
    conn.commit()
    return True
