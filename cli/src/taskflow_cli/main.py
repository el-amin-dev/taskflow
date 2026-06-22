"""TaskFlow command-line entrypoint with central error handling."""
from __future__ import annotations

import sys

import click
import typer
from rich.console import Console

from taskflow_cli import __version__
from taskflow_cli.commands import auth as auth_cmd
from taskflow_cli.errors import ApiError

app = typer.Typer(help="TaskFlow command-line client.")

app.add_typer(auth_cmd.app, name="auth")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """TaskFlow command-line client."""

def run() -> None:
    """Entrypoint. Translates ApiError + Click exceptions to exit codes."""
    err = Console(stderr=True)
    try:
        # Click in non-standalone mode RETURNS the exit code on typer.Exit
        # (rather than raising it). Some versions re-raise — we handle both.
        result = app(standalone_mode=False)
        if isinstance(result, int) and result != 0:
            sys.exit(result)
    except click.exceptions.Exit as e:
        sys.exit(e.exit_code)
    except ApiError as e:
        err.print(f"[red]error:[/red] {e.message}")
        sys.exit(e.exit_code)
    except click.exceptions.UsageError as e:
        e.show()
        sys.exit(e.exit_code)
    except (click.exceptions.Abort, KeyboardInterrupt):
        err.print("[dim]aborted[/dim]")
        sys.exit(130)
