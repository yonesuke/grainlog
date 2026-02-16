"""Textual TUI application."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer

from grainlog.tui.screens.daily import DailyScreen
from grainlog.tui.screens.page import PageListScreen
from grainlog.tui.screens.search import SearchScreen


class GrainlogApp(App):
    """Main Textual application for grainlog."""

    TITLE = "grainlog"
    CSS_PATH = None

    BINDINGS = [
        Binding("d", "push_screen('daily')", "Daily"),
        Binding("p", "push_screen('pages')", "Pages"),
        Binding("s", "push_screen('search')", "Search"),
        Binding("q", "quit", "Quit"),
    ]

    SCREENS = {
        "daily": DailyScreen,
        "pages": PageListScreen,
        "search": SearchScreen,
    }

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

    def on_mount(self) -> None:
        self.push_screen("daily")


def run_tui() -> None:
    """Launch the TUI app."""
    app = GrainlogApp()
    app.run()
