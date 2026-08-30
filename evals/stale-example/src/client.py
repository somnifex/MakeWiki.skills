class Client:
    """Network client for API service."""

    def connect(self, tls_mode: str = "strict") -> bool:
        """Connect to server with TLS mode ('strict' or 'disabled')."""
        if tls_mode not in ("strict", "disabled"):
            raise ValueError(f"Invalid tls_mode: {tls_mode}")
        return True
