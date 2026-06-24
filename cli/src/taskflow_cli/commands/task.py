"""Task commands: list, create, update, status, delete."""
from __future__ import annotations

import json
from enum import Enum

import typer
from rich.console import Console
from rich.table import Table

from taskflow_cli import config
from taskflow_cli.api import tasks as api_tasks
from taskflow_cli.session import Session

app = typer.Typer(help="Task commands. Workspace ID is the first positional arg.", no_args_is_help=True)
err = Console(stderr=True)


class TaskStatus(str, Enum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"


def _session() -> Session:
    return Session(config.load())


@app.command(name="list")
def list_tasks(
    workspace_id: str = typer.Argument(..., help="Workspace ID."),
    status: TaskStatus = typer.Option(None, "--status", "-s", help="Filter by status."),
    json_output: bool = typer.Option(False, "--json", help="Emit tasks as JSON to stdout."),
) -> None:
    """List tasks in a workspace."""
    items = api_tasks.list_all(_session(), workspace_id, status=status.value if status else None)

    if json_output:
        print(json.dumps(items))
        return

    if not items:
        err.print("[dim]no tasks yet[/dim]")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("ID", style="dim")
    table.add_column("Title")
    table.add_column("Status")
    table.add_column("Assignee", style="dim")
    table.add_column("Deadline", style="dim")
    for t in items:
        table.add_row(
            t["id"], t["title"], t["status"],
            t.get("assignee_id") or "—",
            t.get("deadline") or "—",
        )
    Console().print(table)


@app.command()
def create(
    workspace_id: str = typer.Argument(..., help="Workspace ID."),
    title: str = typer.Argument(..., help="Task title."),
    description: str = typer.Option(None, "--description", "-d", help="Task description."),
    status: TaskStatus = typer.Option(None, "--status", "-s", help="Initial status (default: todo)."),
    assignee: str = typer.Option(None, "--assignee", "-a", help="Assignee user ID."),
    deadline: str = typer.Option(None, "--deadline", help="ISO 8601 deadline."),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Create a task."""
    task = api_tasks.create(
        _session(), workspace_id,
        title=title,
        description=description,
        status=status.value if status else None,
        assignee_id=assignee,
        deadline=deadline,
    )
    if json_output:
        print(json.dumps(task))
    else:
        err.print(f"[green]✓[/green] created task [bold]{task['title']}[/bold]")
        print(task["id"])  # stdout: scriptable


@app.command()
def update(
    workspace_id: str = typer.Argument(..., help="Workspace ID."),
    task_id: str = typer.Argument(..., help="Task ID."),
    title: str = typer.Option(None, "--title", "-t"),
    description: str = typer.Option(None, "--description", "-d"),
    assignee: str = typer.Option(None, "--assignee", "-a"),
    deadline: str = typer.Option(None, "--deadline"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Update task metadata. Use `task status` to change status."""
    if not any([title, description, assignee, deadline]):
        err.print("[red]error:[/red] no fields to update; pass at least one of --title/--description/--assignee/--deadline")
        raise typer.Exit(code=2)

    task = api_tasks.update(
        _session(), workspace_id, task_id,
        title=title, description=description,
        assignee_id=assignee, deadline=deadline,
    )
    if json_output:
        print(json.dumps(task))
    else:
        err.print(f"[green]✓[/green] updated task [bold]{task['id']}[/bold]")


@app.command()
def status(
    workspace_id: str = typer.Argument(..., help="Workspace ID."),
    task_id: str = typer.Argument(..., help="Task ID."),
    new_status: TaskStatus = typer.Argument(..., help="New status."),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Change a task's status."""
    task = api_tasks.change_status(_session(), workspace_id, task_id, status=new_status.value)
    if json_output:
        print(json.dumps(task))
    else:
        err.print(f"[green]✓[/green] task {task['id']} → [bold]{task['status']}[/bold]")


@app.command()
def delete(
    workspace_id: str = typer.Argument(..., help="Workspace ID."),
    task_id: str = typer.Argument(..., help="Task ID."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt."),
) -> None:
    """Delete a task. Asks for confirmation unless --yes."""
    if not yes:
        typer.confirm(f"Delete task {task_id}?", abort=True, err=True)

    api_tasks.delete(_session(), workspace_id, task_id)
    err.print(f"[green]✓[/green] deleted task {task_id}")
