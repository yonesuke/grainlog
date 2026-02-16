"""Daily note (journal) creation and retrieval."""

from __future__ import annotations

import sqlite3
from datetime import date

from grainlog.config import get_daily_template
from grainlog.db.queries import (
    create_block,
    get_blocks_for_page,
    get_or_create_page,
    get_page_by_title,
    next_order,
)
from grainlog.core.links import sync_links_for_block


def journal_title(d: date) -> str:
    """Return the canonical page title for a journal date."""
    return d.strftime("%Y-%m-%d")


def get_or_create_daily(conn: sqlite3.Connection, d: date | None = None) -> int:
    """Ensure a journal page exists for the given date.

    If the page is newly created, apply the daily template.
    Returns the page id.
    """
    d = d or date.today()
    title = journal_title(d)

    existing = get_page_by_title(conn, title)
    if existing:
        return existing["id"]

    page_id = get_or_create_page(conn, title, is_journal=True, journal_date=title)
    _apply_template(conn, page_id)
    return page_id


def _apply_template(conn: sqlite3.Connection, page_id: int) -> None:
    """Insert template blocks into a newly created daily page."""
    template = get_daily_template()
    for line in template.splitlines():
        text = line.strip()
        if not text:
            continue
        # Strip leading "- " if present in template
        if text.startswith("- "):
            text = text[2:]
        order = next_order(conn, page_id)
        block_id = create_block(conn, page_id, text, order=order)
        sync_links_for_block(conn, block_id, page_id, text)
