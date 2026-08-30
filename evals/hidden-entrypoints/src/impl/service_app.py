from pathlib import Path

import yaml


def load_config() -> dict:
    """Load .env + .config/app.yml into a single config dict."""
    env: dict[str, str] = {}
    env_file = Path(".env")
    if env_file.is_file():
        for line in env_file.read_text().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()

    app: dict = {}
    cfg_file = Path(".config/app.yml")
    if cfg_file.is_file():
        app = yaml.safe_load(cfg_file.read_text()) or {}

    return {"env": env, "app": app}


def main() -> None:
    cfg = load_config()
    print(cfg["env"]["LOG_LEVEL"])
