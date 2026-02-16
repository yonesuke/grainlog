"""Search screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Input
from textual.containers import VerticalScroll

from grainlog.db.connection import get_connection
from grainlog.db.search import search_blocks


class SearchScreen(Screen):
    BINDINGS = [
        Binding("escape", "pop_screen", "Back"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(placeholder="Search...", id="search-input")
        yield VerticalScroll(id="search-results")
        yield Footer()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        if not query:
            return
        conn = get_connection()
        results = search_blocks(conn, query)
        conn.close()

        container = self.query_one("#search-results", VerticalScroll)
        container.remove_children()
        if not results:
            container.mount(Static("[dim]No results found.[/dim]"))
        else:
            for r in results:
                container.mount(
                    Static(f"  [cyan]{r['page_title']}[/cyan]: {r['highlighted']}")
                )
