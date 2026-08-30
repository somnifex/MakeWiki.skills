import typer

app = typer.Typer()


@app.command()
def serve(port: int = typer.Option(9000, "--port")) -> None:
    typer.echo(f"svc-a serving on {port}")
