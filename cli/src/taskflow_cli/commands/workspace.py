"""Workspace commands: list, create."""
from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.table import Table

from taskflow_cli import config
from taskflow_cli.api import workspaces as api_ws
from taskflow_cli.session import Session

app = typer.Typer(help="Workspace commands.", no_args_is_help=True)
err = Console(stderr=True)


@app.command(name="list")
def list_workspaces(
    json_output: bool = typer.Option(
        False, "--json", help="Emit workspaces as JSON to stdout."
    ),
) -> None:
    """List your workspaces (newest first)."""
    cfg = config.load()
    sess = Session(cfg)
    items = api_ws.list_all(sess)

    if json_output:
        print(json.dumps(items))
        return

    if not items:
        err.print("[dim]no workspaces yet[/dim]")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("ID", style="dim")
    table.add_column("Name")
    table.add_column("Created", style="dim")
    for ws in items:
        table.add_row(ws["id"], ws["name"], ws["created_at"])
    Console().print(table)


@app.command()
def create(
    name: str = typer.Argument(..., help="Name for the new workspace."),
    json_output: bool = typer.Option(
        False, "--json", help="Emit the new workspace as JSON to stdout."
    ),
) -> None:
    """Create a new workspace."""
    cfg = config.load()
    sess = Session(cfg)
    ws = api_ws.create(sess, name=name)

    if json_output:
        print(json.dumps(ws))
    else:
        err.print(f"[green]✓[/green] created workspace [bold]{ws['name']}[/bold]")
        print(ws["id"])  # stdout: scriptable
