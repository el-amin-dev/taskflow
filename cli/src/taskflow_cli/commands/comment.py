"""Comment commands: list, add, edit, delete."""
from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.table import Table

from taskflow_cli import config
from taskflow_cli.api import comments as api_comments
from taskflow_cli.session import Session
from taskflow_cli.util.editor import compose_body

app = typer.Typer(
    help="Task comment commands. Workspace ID and Task ID are positional.",
    no_args_is_help=True,
)
err = Console(stderr=True)


def _session() -> Session:
    return Session(config.load())


def _short(uuid_str: str | None, n: int = 8) -> str:
    return uuid_str[:n] if uuid_str else "—"


def _render_table(items: list[dict]) -> None:
    table = Table(show_header=True, header_style="bold")
    table.add_column("ID", style="dim")
    table.add_column("Author", style="dim")
    table.add_column("Body")
    table.add_column("Created", style="dim")
    for c in items:
        body = c.get("body", "").strip() or "(empty)"
        table.add_row(
            _short(c["id"]),
            _short(c.get("author_id")) if c.get("author_id") else "(deleted user)",
            body,
            c.get("created_at", ""),
        )
    Console().print(table)


@app.command(name="list")
def list_comments(
    workspace_id: str = typer.Argument(..., help="Workspace ID."),
    task_id: str = typer.Argument(..., help="Task ID."),
    cursor: str = typer.Option(None, "--cursor", help="Resume from a previous next_cursor."),
    limit: int = typer.Option(None, "--limit", help="Page size."),
    all_pages: bool = typer.Option(False, "--all", help="Walk every page."),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """List comments on a task (oldest first). One page by default."""
    sess = _session()

    if all_pages:
        items = api_comments.list_all(sess, workspace_id, task_id, limit=limit)
        if json_output:
            print(json.dumps({"items": items, "next_cursor": None}))
            return
        if not items:
            err.print("[dim]no comments yet[/dim]")
            return
        _render_table(items)
        return

    page = api_comments.list_page(sess, workspace_id, task_id, cursor=cursor, limit=limit)
    if json_output:
        print(json.dumps(page))
        return

    if not page["items"]:
        err.print("[dim]no comments yet[/dim]")
        return

    _render_table(page["items"])

    if page["next_cursor"]:
        err.print(f"\n[dim]more available — re-run with --cursor {page['next_cursor']} or --all[/dim]")


def _compose_message(message: str | None, message_stdin: bool, template: str) -> str:
    return compose_body(message=message, message_stdin=message_stdin, editor_template=template)


@app.command()
def add(
    workspace_id: str = typer.Argument(..., help="Workspace ID."),
    task_id: str = typer.Argument(..., help="Task ID."),
    message: str = typer.Option(None, "-m", "--message", help="Comment body inline."),
    message_stdin: bool = typer.Option(False, "--message-stdin", help="Read body from stdin."),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Add a comment to a task."""
    body = _compose_message(
        message,
        message_stdin,
        template=f"Add a comment to task {task_id}.\nLines starting with # are ignored.",
    )
    comment = api_comments.create(_session(), workspace_id, task_id, body=body)
    if json_output:
        print(json.dumps(comment))
    else:
        err.print(f"[green]✓[/green] added comment to task {_short(task_id)}")
        print(comment["id"])


@app.command()
def edit(
    workspace_id: str = typer.Argument(..., help="Workspace ID."),
    task_id: str = typer.Argument(..., help="Task ID."),
    comment_id: str = typer.Argument(..., help="Comment ID."),
    message: str = typer.Option(None, "-m", "--message", help="New body inline."),
    message_stdin: bool = typer.Option(False, "--message-stdin", help="Read new body from stdin."),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Replace a comment's body. Only the author can edit."""
    body = _compose_message(
        message,
        message_stdin,
        template=f"Edit comment {comment_id}.\nLines starting with # are ignored.",
    )
    updated = api_comments.update(_session(), workspace_id, task_id, comment_id, body=body)
    if json_output:
        print(json.dumps(updated))
    else:
        err.print(f"[green]✓[/green] updated comment {_short(comment_id)}")


@app.command()
def delete(
    workspace_id: str = typer.Argument(..., help="Workspace ID."),
    task_id: str = typer.Argument(..., help="Task ID."),
    comment_id: str = typer.Argument(..., help="Comment ID."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt."),
) -> None:
    """Delete a comment. Only the author can delete."""
    if not yes:
        typer.confirm(f"Delete comment {comment_id}?", abort=True, err=True)
    api_comments.delete(_session(), workspace_id, task_id, comment_id)
    err.print(f"[green]✓[/green] deleted comment {_short(comment_id)}")
