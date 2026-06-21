import typer 

from taskflow_cli import __version__
from taskflow_cli.commands import auth as auth_cmd  

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
