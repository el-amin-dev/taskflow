"""Member commands: invite (list/remove blocked by backend #85)."""
from __future__ import annotations

import json
from enum import Enum

import typer
from rich.console import Console

from taskflow_cli import config
from taskflow_cli.api import members as api_members
from taskflow_cli.session import Session

app = typer.Typer(
    help="Workspace member commands. (list/remove are blocked by backend #85.)",
    no_args_is_help=True,
)
err = Console(stderr=True)


class Role(str, Enum):
    admin = "admin"
    member = "member"
    viewer = "viewer"


@app.command()
def invite(
    workspace_id: str = typer.Argument(..., help="Workspace ID."),
    email: str = typer.Argument(..., help="Email of user to invite."),
    role: Role = typer.Option(
        Role.member, "--role", "-r", help="Role to assign."
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Emit the membership as JSON to stdout."
    ),
) -> None:
    """Invite a user to a workspace by email."""
    cfg = config.load()
    sess = Session(cfg)
    membership = api_members.invite(
        sess, workspace_id, email=email, role=role.value
    )

    if json_output:
        print(json.dumps(membership))
    else:
        err.print(
            f"[green]✓[/green] invited [bold]{email}[/bold] "
            f"as [bold]{role.value}[/bold]"
        )
