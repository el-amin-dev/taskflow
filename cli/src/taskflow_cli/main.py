"""TaskFlow command-line entrypoint with central error handling."""
from __future__ import annotations

import sys

import click
import typer
from typer._click import exceptions as _typer_exc
from rich.console import Console

from taskflow_cli import __version__
from taskflow_cli.commands import auth as auth_cmd
from taskflow_cli.errors import ApiError
from taskflow_cli.commands import workspace as workspace_cmd
from taskflow_cli.commands import member as member_cmd

app = typer.Typer(help="TaskFlow command-line client.")

app.add_typer(auth_cmd.app, name="auth")
app.add_typer(workspace_cmd.app, name="workspace")
app.add_typer(member_cmd.app, name="member")

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
    """Entrypoint. Translates ApiError + Click/Typer exceptions to exit codes."""
    err = Console(stderr=True)
    try:
        # Click in non-standalone mode RETURNS the exit code on typer.Exit
        # (rather than raising it). Some versions re-raise — we handle both.
        result = app(standalone_mode=False)
        if isinstance(result, int) and result != 0:
            sys.exit(result)
    except (click.exceptions.Exit, _typer_exc.Exit) as e:
        sys.exit(e.exit_code)
    except ApiError as e:
        err.print(f"[red]error:[/red] {e.message}")
        sys.exit(e.exit_code)
    except (click.exceptions.UsageError, _typer_exc.UsageError) as e:
        # Covers BadParameter, MissingParameter, NoSuchOption from both packages.
        e.show()
        sys.exit(e.exit_code)
    except (click.exceptions.Abort, _typer_exc.Abort, KeyboardInterrupt):
        err.print("[dim]aborted[/dim]")
        sys.exit(130)
