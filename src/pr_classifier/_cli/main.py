"""Thin CLI wrapper — full implementation in T016."""
import typer

app = typer.Typer(help="Classify GitHub pull requests by review state.")


@app.command()
def classify() -> None:  # pragma: no cover
    """Not yet implemented — see T016."""
    typer.echo("Not yet implemented.", err=True)
    raise typer.Exit(2)


if __name__ == "__main__":  # pragma: no cover
    app()
