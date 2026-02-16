"""[[link]] and #tag parsers with synchronization."""

from __future__ import annotations

import re
import sqlite3

from grainlog.db.queries import get_or_create_page, replace_links_for_block, replace_tags_for_block

LINK_PATTERN = re.compile(r"\[\[([^\[\]]+)\]\]")
TAG_PATTERN = re.compile(r"(?:^|(?<=\s))#([A-Za-z\u3040-\u9fff\uff66-\uff9f][A-Za-z0-9_\u3040-\u9fff\uff66-\uff9f-]*)")


def parse_links(text: str) -> list[str]:
    """Extract all [[link]] targets from text."""
    return LINK_PATTERN.findall(text)


def parse_tags(text: str) -> list[str]:
    """Extract all #tag names from text."""
    return TAG_PATTERN.findall(text)


def sync_links_for_block(
    conn: sqlite3.Connection, block_id: int, page_id: int, content: str
) -> None:
    """Parse links and tags from block content and update tables."""
    # Links
    titles = parse_links(content)
    targets: list[tuple[int, str]] = []
    for title in titles:
        target_page_id = get_or_create_page(conn, title)
        targets.append((target_page_id, title))
    replace_links_for_block(conn, block_id, page_id, targets)

    # Tags
    tag_names = parse_tags(content)
    replace_tags_for_block(conn, block_id, page_id, tag_names)
