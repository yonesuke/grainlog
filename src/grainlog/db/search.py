"""FTS5 full-text search helpers."""

from __future__ import annotations

import sqlite3


def search_blocks(conn: sqlite3.Connection, query: str, *, limit: int = 50) -> list[sqlite3.Row]:
    """Search blocks using FTS5 and return matching rows with page info."""
    return conn.execute(
        """
        SELECT b.id, b.page_id, b.content, p.title AS page_title,
               highlight(blocks_fts, 0, '**', '**') AS highlighted
        FROM blocks_fts fts
        JOIN blocks b ON b.id = fts.rowid
        JOIN pages p ON p.id = b.page_id
        WHERE blocks_fts MATCH ?
        ORDER BY rank
        LIMIT ?
        """,
        (query, limit),
    ).fetchall()
