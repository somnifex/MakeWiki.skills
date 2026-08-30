"""Server entrypoint for `app`."""

# The authoritative default port is hard-coded HERE, in the source.
DEFAULT_PORT = 8080
DEFAULT_HOST = "0.0.0.0"


def create_app():
    return {"port": DEFAULT_PORT}
