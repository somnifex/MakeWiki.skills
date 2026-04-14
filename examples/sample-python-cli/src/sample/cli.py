"""Sample CLI application."""

import click


@click.group()
@click.version_option("1.2.0")
def main():
    """sample-cli - a demo command-line tool."""
    pass


@main.command()
@click.argument("name")
def greet(name: str):
    """Say hello to NAME."""
    click.echo(f"Hello, {name}!")


@main.command()
@click.option("--port", default=8080, help="Port to listen on")
@click.option("--host", default="127.0.0.1", help="Host to bind to")
def serve(host: str, port: int):
    """Start the development server."""
    click.echo(f"Serving on {host}:{port}")


if __name__ == "__main__":
    main()
