import typer

app = typer.Typer()


@app.command()
def echo(message: str = typer.Argument(...)) -> None:
    """Echo a message back to the terminal."""
    typer.echo(message)


@app.command()
def serve(port: int = typer.Option(8080, "--port", help="Port to bind")) -> None:
    """Serve a stub HTTP endpoint on the given port."""
    typer.echo(f"listening on {port}")


if __name__ == "__main__":
    app()
