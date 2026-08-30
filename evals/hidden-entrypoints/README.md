# service

A small Python service.

## Run

```bash
uv run uvicorn service.app:app --host 0.0.0.0 --port 8080
```

## Configuration

The service reads configuration from a `.env` file (and optional
`.config/app.yml`). Required keys: `API_TOKEN`, `DB_URL`, `LOG_LEVEL`.
