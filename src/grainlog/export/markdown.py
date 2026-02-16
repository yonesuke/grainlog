"""Export database contents to Logseq-compatible Markdown files."""

from __future__ import annotations

from pathlib import Path
import sqlite3

from grainlog.core.outliner import build_block_tree
from grainlog.core.models import Block
from grainlog.db.queries import list_pages


def _render_blocks(blocks: list[Block], depth: int = 0) -> list[str]:
    """Render blocks as indented Logseq-style bullet lines."""
    lines: list[str] = []
    indent = "  " * depth
    for b in blocks:
        lines.append(f"{indent}- {b.content}")
        if b.children:
            lines.extend(_render_blocks(b.children, depth + 1))
    return lines


def export_page(conn: sqlite3.Connection, page_id: int, title: str) -> str:
    """Render a single page as Logseq-compatible Markdown."""
    tree = build_block_tree(conn, page_id)
    lines = _render_blocks(tree)
    return "\n".join(lines) + "\n" if lines else ""


def export_all(conn: sqlite3.Connection, output_dir: Path) -> int:
    """Export all pages to output_dir. Returns the count of exported files."""
    journals_dir = output_dir / "journals"
    pages_dir = output_dir / "pages"
    journals_dir.mkdir(parents=True, exist_ok=True)
    pages_dir.mkdir(parents=True, exist_ok=True)

    pages = list_pages(conn)
    count = 0
    for page in pages:
        content = export_page(conn, page["id"], page["title"])
        if not content.strip():
            continue
        if page["is_journal"] and page["journal_date"]:
            filename = page["journal_date"].replace("-", "_") + ".md"
            path = journals_dir / filename
        else:
            safe_title = page["title"].replace("/", "_").replace("\\", "_")
            path = pages_dir / f"{safe_title}.md"
        path.write_text(content, encoding="utf-8")
        count += 1
    return count
