import os
from pathlib import Path

import yaml


def load_config() -> dict:
    cfg = yaml.safe_load(Path("config.yaml").read_text()) or {}
    # env vars override the base config (composed via docker-compose).
    if os.getenv("PORT"):
        cfg["port"] = int(os.getenv("PORT"))
    if os.getenv("CACHE_ENABLED") is not None:
        cfg["features"]["cache"] = os.getenv("CACHE_ENABLED") == "true"
    return cfg


def main() -> None:
    print(load_config()["port"])
