"""CLI entry point and all subcommands."""

from __future__ import annotations

import os
import subprocess
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from grainlog.config import (
    get_config_path,
    get_config_value,
    get_db_path,
    get_editor,
    load_config,
    save_default_daily_template,
    set_config_value,
    unset_config_value,
    DEFAULTS,
)
from grainlog.db.connection import get_connection
from grainlog.db.queries import (
    bulk_done_todos,
    clear_done_blocks,
    create_block,
    get_backlinks,
    get_blocks_by_tag,
    get_blocks_for_page,
    get_forward_links,
    get_or_create_page,
    get_page_by_title,
    get_todo_blocks,
    list_all_tags,
    list_pages,
    next_order,
    toggle_todo_block,
    update_block_content,
)
from grainlog.db.search import search_blocks
from grainlog.core.daily import get_or_create_daily, journal_title
from grainlog.core.links import sync_links_for_block
from grainlog.core.outliner import build_block_tree
from grainlog.core.models import Block
from grainlog.export.markdown import export_all

app = typer.Typer(
    name="grainlog",
    help="Logseq-style CLI knowledge management tool.",
    no_args_is_help=False,
    invoke_without_command=True,
)
tag_app = typer.Typer(help="Tag management commands.")
app.add_typer(tag_app, name="tag")

todo_app = typer.Typer(help="TODO management commands.")
app.add_typer(todo_app, name="todo")

template_app = typer.Typer(help="Template management commands.")
app.add_typer(template_app, name="template")

config_app = typer.Typer(help="Configuration management.")
app.add_typer(config_app, name="config")

console = Console()


def _print_block_tree(blocks: list[Block], depth: int = 0) -> None:
    indent = "  " * depth
    for b in blocks:
        console.print(f"{indent}[dim]•[/dim] {b.content}")
        if b.children:
            _print_block_tree(b.children, depth + 1)


def _show_page(conn, title: str) -> None:
    page = get_page_by_title(conn, title)
    if not page:
        console.print(f"[yellow]Page '{title}' not found.[/yellow]")
        raise typer.Exit(1)
    tree = build_block_tree(conn, page["id"])
    console.print(Panel(f"[bold]{title}[/bold]"))
    if tree:
        _print_block_tree(tree)
    else:
        console.print("[dim]  (empty page)[/dim]")


@app.callback()
def main(ctx: typer.Context) -> None:
    """grainlog — Logseq-style CLI knowledge management."""
    if ctx.invoked_subcommand is None:
        # No subcommand: launch TUI
        from grainlog.tui.app import run_tui
        run_tui()


@app.command()
def today() -> None:
    """Show or create today's daily note."""
    conn = get_connection()
    page_id = get_or_create_daily(conn)
    title = journal_title(date.today())
    _show_page(conn, title)
    conn.close()


@app.command()
def daily(
    date_str: Optional[str] = typer.Argument(None, help="Date in YYYY-MM-DD format"),
    list_all: bool = typer.Option(False, "--list", "-l", help="List all journal entries"),
) -> None:
    """Show a daily note for a specific date, or list all journals."""
    conn = get_connection()
    if list_all:
        pages = list_pages(conn, journals_only=True)
        if not pages:
            console.print("[dim]No journal entries yet.[/dim]")
        else:
            table = Table(title="Journals")
            table.add_column("Date", style="cyan")
            table.add_column("Created", style="dim")
            for p in pages:
                table.add_row(p["journal_date"], p["created_at"][:10])
            console.print(table)
        conn.close()
        return
    if date_str:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
    else:
        d = date.today()
    get_or_create_daily(conn, d)
    _show_page(conn, journal_title(d))
    conn.close()


@app.command()
def new(title: str = typer.Argument(..., help="Page title")) -> None:
    """Create a new page."""
    conn = get_connection()
    page = get_page_by_title(conn, title)
    if page:
        console.print(f"[yellow]Page '{title}' already exists.[/yellow]")
    else:
        get_or_create_page(conn, title)
        console.print(f"[green]Created page: {title}[/green]")
    conn.close()


@app.command()
def add(
    title: str = typer.Argument(..., help="Page title"),
    content: str = typer.Argument(..., help="Block content"),
) -> None:
    """Add a block to a page."""
    conn = get_connection()
    page_id = get_or_create_page(conn, title)
    order = next_order(conn, page_id)
    block_id = create_block(conn, page_id, content, order=order)
    sync_links_for_block(conn, block_id, page_id, content)
    console.print(f"[green]Added block to '{title}'[/green]")
    conn.close()


@app.command()
def edit(title: str = typer.Argument(..., help="Page title")) -> None:
    """Edit a page's blocks in $EDITOR."""
    conn = get_connection()
    page = get_page_by_title(conn, title)
    if not page:
        console.print(f"[yellow]Page '{title}' not found.[/yellow]")
        raise typer.Exit(1)
    page_id = page["id"]

    # Build current content
    tree = build_block_tree(conn, page_id)

    def _serialize(blocks: list[Block], depth: int = 0) -> list[str]:
        lines: list[str] = []
        for b in blocks:
            lines.append("  " * depth + "- " + b.content)
            if b.children:
                lines.extend(_serialize(b.children, depth + 1))
        return lines

    current = "\n".join(_serialize(tree)) + "\n" if tree else ""

    editor = get_editor()
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False, encoding="utf-8") as f:
        f.write(current)
        tmp_path = f.name

    try:
        subprocess.run([editor, tmp_path], check=True)
        new_content = Path(tmp_path).read_text(encoding="utf-8")
    finally:
        os.unlink(tmp_path)

    # Parse lines back into blocks: delete old, insert new
    conn.execute("DELETE FROM blocks WHERE page_id = ?", (page_id,))
    conn.execute("DELETE FROM links WHERE source_page_id = ?", (page_id,))
    conn.commit()

    parent_stack: list[int | None] = [None]
    prev_depth = 0
    order_at_depth: dict[int, int] = {0: 0}

    for line in new_content.splitlines():
        stripped = line.rstrip()
        if not stripped:
            continue
        # Count indentation (2-space units) before "- "
        indent = 0
        s = stripped
        while s.startswith("  "):
            indent += 1
            s = s[2:]
        text = s.lstrip("- ").rstrip() if s.startswith("- ") else s.rstrip()
        if not text:
            continue

        depth = indent
        if depth > prev_depth:
            # go deeper – parent is the last block at prev_depth
            pass  # parent_stack already updated below
        elif depth < prev_depth:
            parent_stack = parent_stack[: depth + 1]

        order_at_depth.setdefault(depth, 0)
        parent_id = parent_stack[depth] if depth < len(parent_stack) else parent_stack[-1]
        block_id = create_block(conn, page_id, text, parent_id=parent_id, order=order_at_depth.get(depth, 0))
        sync_links_for_block(conn, block_id, page_id, text)
        order_at_depth[depth] = order_at_depth.get(depth, 0) + 1

        # Update parent stack
        if depth + 1 < len(parent_stack):
            parent_stack[depth + 1] = block_id
        else:
            while len(parent_stack) <= depth + 1:
                parent_stack.append(block_id)
            parent_stack[depth + 1] = block_id

        # Reset child order counters
        for d in list(order_at_depth):
            if d > depth:
                order_at_depth[d] = 0

        prev_depth = depth

    console.print(f"[green]Updated page '{title}'[/green]")
    conn.close()


@app.command()
def search(query: str = typer.Argument(..., help="Search query")) -> None:
    """Full-text search across all blocks."""
    conn = get_connection()
    results = search_blocks(conn, query)
    if not results:
        console.print("[dim]No results found.[/dim]")
    else:
        for r in results:
            console.print(f"[cyan]{r['page_title']}[/cyan]: {r['highlighted']}")
    conn.close()


@app.command()
def links(title: str = typer.Argument(..., help="Page title")) -> None:
    """Show backlinks and forward links for a page."""
    conn = get_connection()
    page = get_page_by_title(conn, title)
    if not page:
        console.print(f"[yellow]Page '{title}' not found.[/yellow]")
        raise typer.Exit(1)

    backlinks = get_backlinks(conn, page["id"])
    forward = get_forward_links(conn, page["id"])

    console.print(Panel(f"[bold]Links for: {title}[/bold]"))

    if backlinks:
        console.print("\n[bold]Backlinks:[/bold]")
        for bl in backlinks:
            console.print(f"  [cyan]{bl['source_page_title']}[/cyan]: {bl['block_content']}")
    else:
        console.print("\n[dim]No backlinks.[/dim]")

    if forward:
        console.print("\n[bold]Forward links:[/bold]")
        for fl in forward:
            console.print(f"  → [cyan]{fl['target_title']}[/cyan]")
    else:
        console.print("\n[dim]No forward links.[/dim]")
    conn.close()


@app.command()
def pages() -> None:
    """List all pages."""
    conn = get_connection()
    all_pages = list_pages(conn)
    if not all_pages:
        console.print("[dim]No pages yet.[/dim]")
    else:
        table = Table(title="Pages")
        table.add_column("Title", style="cyan")
        table.add_column("Type", style="dim")
        table.add_column("Updated", style="dim")
        for p in all_pages:
            ptype = "journal" if p["is_journal"] else "page"
            table.add_row(p["title"], ptype, p["updated_at"][:10])
        console.print(table)
    conn.close()


# ---------------------------------------------------------------------------
# Tag commands
# ---------------------------------------------------------------------------

@tag_app.command("list")
def tag_list() -> None:
    """List all tags with usage counts."""
    conn = get_connection()
    tags = list_all_tags(conn)
    if not tags:
        console.print("[dim]No tags yet.[/dim]")
    else:
        table = Table(title="Tags")
        table.add_column("Tag", style="cyan")
        table.add_column("Count", style="bold", justify="right")
        for t in tags:
            table.add_row(f"#{t['name']}", str(t["count"]))
        console.print(table)
    conn.close()


@tag_app.command("show")
def tag_show(name: str = typer.Argument(..., help="Tag name (without #)")) -> None:
    """Show all blocks with a specific tag."""
    conn = get_connection()
    blocks = get_blocks_by_tag(conn, name)
    if not blocks:
        console.print(f"[dim]No blocks tagged #{name}.[/dim]")
    else:
        console.print(Panel(f"[bold]#{name}[/bold]  ({len(blocks)} blocks)"))
        for b in blocks:
            console.print(f"  [cyan]{b['page_title']}[/cyan]: {b['content']}")
    conn.close()


# ---------------------------------------------------------------------------
# TODO commands
# ---------------------------------------------------------------------------

@todo_app.command("list")
def todo_list(
    all_: bool = typer.Option(False, "--all", "-a", help="Show both TODO and DONE"),
    done: bool = typer.Option(False, "--done", "-d", help="Show only DONE items"),
    page: Optional[str] = typer.Option(None, "--page", "-p", help="Filter by page title"),
) -> None:
    """List TODO/DONE blocks."""
    conn = get_connection()
    if all_:
        status = None
    elif done:
        status = "done"
    else:
        status = "todo"
    blocks = get_todo_blocks(conn, status=status, page_title=page)
    if not blocks:
        console.print("[dim]No items found.[/dim]")
    else:
        table = Table(title="TODO" if status != "done" else "DONE")
        table.add_column("ID", style="dim", justify="right")
        table.add_column("Page", style="cyan")
        table.add_column("Content")
        for b in blocks:
            content = b["content"]
            if content.startswith("TODO "):
                styled = f"[yellow]TODO[/yellow] {content[5:]}"
            elif content.startswith("DONE "):
                styled = f"[green]DONE[/green] [dim]{content[5:]}[/dim]"
            else:
                styled = content
            table.add_row(str(b["id"]), b["page_title"], styled)
        console.print(table)
    conn.close()


@todo_app.command("done")
def todo_done(
    block_ids: list[int] = typer.Argument(..., help="Block IDs to mark as DONE"),
) -> None:
    """Mark TODO blocks as DONE (bulk)."""
    conn = get_connection()
    count = bulk_done_todos(conn, block_ids)
    console.print(f"[green]Marked {count} block(s) as DONE.[/green]")
    conn.close()


@todo_app.command("toggle")
def todo_toggle(
    block_id: int = typer.Argument(..., help="Block ID to toggle"),
) -> None:
    """Toggle a block between TODO and DONE."""
    conn = get_connection()
    result = toggle_todo_block(conn, block_id)
    if result is None:
        console.print("[yellow]Block not found or not a TODO/DONE block.[/yellow]")
    else:
        label = "[green]DONE[/green]" if result == "done" else "[yellow]TODO[/yellow]"
        console.print(f"Toggled to {label}.")
    conn.close()


@todo_app.command("clear")
def todo_clear(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Delete all DONE blocks."""
    conn = get_connection()
    if not force:
        done_blocks = get_todo_blocks(conn, status="done")
        if not done_blocks:
            console.print("[dim]No DONE blocks to clear.[/dim]")
            conn.close()
            return
        console.print(f"[yellow]This will delete {len(done_blocks)} DONE block(s).[/yellow]")
        confirm = typer.confirm("Proceed?")
        if not confirm:
            console.print("Cancelled.")
            conn.close()
            return
    count = clear_done_blocks(conn)
    console.print(f"[green]Cleared {count} DONE block(s).[/green]")
    conn.close()


# ---------------------------------------------------------------------------
# Template commands
# ---------------------------------------------------------------------------

@template_app.command("show")
def template_show() -> None:
    """Show the current daily template."""
    from grainlog.config import get_daily_template
    template = get_daily_template()
    console.print(Panel("[bold]Daily Template[/bold]"))
    console.print(template)


@template_app.command("edit")
def template_edit() -> None:
    """Edit the daily template in $EDITOR."""
    path = save_default_daily_template()
    editor = get_editor()
    subprocess.run([editor, str(path)], check=True)
    console.print(f"[green]Template saved: {path}[/green]")


@template_app.command("path")
def template_path() -> None:
    """Show the template file path."""
    path = save_default_daily_template()
    console.print(f"[bold]Template file:[/bold] {path}")


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

@app.command(name="export")
def export_cmd(
    output: Path = typer.Option(Path("./grainlog-export"), "--output", "-o", help="Output directory"),
) -> None:
    """Export all pages to Logseq-compatible Markdown files."""
    conn = get_connection()
    count = export_all(conn, output)
    console.print(f"[green]Exported {count} pages to {output}[/green]")
    conn.close()


@app.command()
def tui() -> None:
    """Launch the interactive TUI."""
    from grainlog.tui.app import run_tui
    run_tui()


# ---------------------------------------------------------------------------
# Config commands
# ---------------------------------------------------------------------------

@config_app.command("show")
def config_show() -> None:
    """Show current configuration."""
    console.print(f"[bold]Database:[/bold]    {get_db_path()}")
    console.print(f"[bold]Config file:[/bold] {get_config_path()}")
    console.print("")
    cfg = load_config()
    table = Table(title="Settings")
    table.add_column("Key", style="cyan")
    table.add_column("Value")
    table.add_column("Source", style="dim")
    for key in sorted(set(list(DEFAULTS.keys()) + list(cfg.keys()))):
        value = get_config_value(key)
        if key in cfg:
            source = "config.toml"
        elif key == "editor" and os.environ.get("EDITOR"):
            source = "$EDITOR"
        else:
            source = "default"
        table.add_row(key, value, source)
    console.print(table)


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Config key (e.g. editor)"),
    value: str = typer.Argument(..., help="Config value (e.g. code, vim, nano)"),
) -> None:
    """Set a configuration value."""
    set_config_value(key, value)
    console.print(f"[green]Set {key} = {value}[/green]")


@config_app.command("unset")
def config_unset(
    key: str = typer.Argument(..., help="Config key to remove"),
) -> None:
    """Remove a configuration value (revert to default)."""
    if unset_config_value(key):
        console.print(f"[green]Removed '{key}' from config (will use default).[/green]")
    else:
        console.print(f"[yellow]'{key}' is not set in config.[/yellow]")


@config_app.command("path")
def config_path() -> None:
    """Show the config file path."""
    console.print(f"[bold]Config file:[/bold] {get_config_path()}")


def app_entry() -> None:
    """Entry point for the console script."""
    app()
