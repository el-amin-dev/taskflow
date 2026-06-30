"""Auth commands: login, register, whoami, logout."""
from __future__ import annotations

import json
import sys

import typer
from rich.console import Console

from taskflow_cli import config
from taskflow_cli.api import auth as api_auth
from taskflow_cli.errors import EXIT_AUTH
from taskflow_cli.session import Session

app = typer.Typer(help="Authentication commands.", no_args_is_help=True)
err = Console(stderr=True)  # all chatter goes here


@app.command()
def login(
    email: str | None = typer.Option(None, "--email", "-e", help="Your email address."),
    password_stdin: bool = typer.Option(
        False,
        "--password-stdin",
        help="Read password from stdin (for scripts).",
    ),
) -> None:
    """Log in and save credentials. Prompts for missing values."""
    if email is None:
        email = typer.prompt("Email")
    if password_stdin:
        password = sys.stdin.read().strip()
    else:
        password = typer.prompt("Password", hide_input=True)

    cfg = config.load()
    sess = Session(cfg)
    with sess.anonymous_client() as t:
        body = api_auth.login(t, email=email, password=password)

    sess.save_tokens(body)
    err.print(f"[green]✓[/green] logged in as {email}")


@app.command()
def register(
    email: str | None = typer.Option(None, "--email", "-e", help="Email for the new account."),
    password_stdin: bool = typer.Option(
        False,
        "--password-stdin",
        help="Read password from stdin (for scripts).",
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Emit the new user as JSON to stdout."
    ),
) -> None:
    """Create a new account. Does not log in — use `auth login` after."""
    if email is None:
        email = typer.prompt("Email")
    if password_stdin:
        password = sys.stdin.read().strip()
    else:
        password = typer.prompt("Password", hide_input=True, confirmation_prompt=True)

    cfg = config.load()
    sess = Session(cfg)
    with sess.anonymous_client() as t:
        user = api_auth.register(t, email=email, password=password)

    if json_output:
        print(json.dumps(user))
    else:
        err.print(f"[green]✓[/green] created account for {user['email']}")
        err.print("[dim]  next: tflowctl auth login[/dim]")


@app.command()
def whoami(
    json_output: bool = typer.Option(
        False, "--json", help="Emit user as JSON to stdout."
    ),
) -> None:
    """Show the authenticated user."""
    cfg = config.load()
    sess = Session(cfg)
    if not sess.is_authenticated:
        err.print("[red]error:[/red] not logged in (run `tflowctl auth login`)")
        raise typer.Exit(code=EXIT_AUTH)

    user = api_auth.me(sess)  # session has the same shape as Transport
    if json_output:
        print(json.dumps(user))
    else:
        print(user["email"])                                # stdout: data
        err.print(f"[dim]  role: {user['role']}[/dim]")     # stderr: chatter


@app.command()
def logout() -> None:
    """Revoke the session and remove local credentials. Idempotent."""
    cfg = config.load()
    sess = Session(cfg)
    if not sess.is_authenticated:
        err.print("[dim]already logged out[/dim]")
        return
    sess.logout()
    err.print("[green]✓[/green] logged out")
