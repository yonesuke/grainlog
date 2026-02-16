"""Daily note screen."""

from __future__ import annotations

from datetime import date

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Input
from textual.containers import VerticalScroll

from grainlog.db.connection import get_connection
from grainlog.core.daily import get_or_create_daily, journal_title
from grainlog.core.outliner import build_block_tree
from grainlog.core.models import Block
from grainlog.db.queries import create_block, next_order
from grainlog.core.links import sync_links_for_block


class DailyScreen(Screen):
    BINDINGS = [
        Binding("escape", "pop_screen", "Back"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(id="daily-content")
        yield Input(placeholder="Add a block... (Enter to submit)", id="block-input")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_content()

    def _refresh_content(self) -> None:
        conn = get_connection()
        d = date.today()
        page_id = get_or_create_daily(conn, d)
        title = journal_title(d)
        tree = build_block_tree(conn, page_id)
        conn.close()

        container = self.query_one("#daily-content", VerticalScroll)
        container.remove_children()
        container.mount(Static(f"[bold]📅 {title}[/bold]\n"))
        if tree:
            container.mount(Static(self._render_tree(tree)))
        else:
            container.mount(Static("[dim](empty — type below to add a block)[/dim]"))

    def _render_tree(self, blocks: list[Block], depth: int = 0) -> str:
        lines: list[str] = []
        for b in blocks:
            indent = "  " * depth
            lines.append(f"{indent}• {b.content}")
            if b.children:
                lines.append(self._render_tree(b.children, depth + 1))
        return "\n".join(lines)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return
        conn = get_connection()
        d = date.today()
        page_id = get_or_create_daily(conn, d)
        order = next_order(conn, page_id)
        block_id = create_block(conn, page_id, text, order=order)
        sync_links_for_block(conn, block_id, page_id, text)
        conn.close()
        event.input.value = ""
        self._refresh_content()
