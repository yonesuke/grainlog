"""Page list screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, ListView, ListItem, Label
from textual.containers import VerticalScroll

from grainlog.db.connection import get_connection
from grainlog.db.queries import list_pages
from grainlog.core.outliner import build_block_tree
from grainlog.core.models import Block


class PageListScreen(Screen):
    BINDINGS = [
        Binding("escape", "pop_screen", "Back"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(id="page-list-content")
        yield Footer()

    def on_mount(self) -> None:
        conn = get_connection()
        all_pages = list_pages(conn)
        conn.close()

        container = self.query_one("#page-list-content", VerticalScroll)
        container.mount(Static("[bold]Pages[/bold]\n"))
        if not all_pages:
            container.mount(Static("[dim]No pages yet.[/dim]"))
        else:
            for p in all_pages:
                ptype = "📓" if p["is_journal"] else "📄"
                container.mount(Static(f"  {ptype} [cyan]{p['title']}[/cyan]  [dim]{p['updated_at'][:10]}[/dim]"))
