class CustomAuthPlugin:
    """Plugin providing custom token validation."""

    def validate(self, token: str) -> bool:
        return bool(token)
