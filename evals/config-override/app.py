import os

import yaml


def get_database_url():
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url
    with open("config.yaml") as f:
        cfg = yaml.safe_load(f)
    return f"postgresql://{cfg['database']['host']}:{cfg['database']['port']}/mydb"
