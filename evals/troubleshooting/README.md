# syncsvc — a small job-syncing service

`syncsvc` syncs local files to a remote object store. It reads its config
from `config.yaml`.

## Quick start

```bash
python sync.py --config config.yaml
```

This connects to the object store configured in `config.yaml` and pushes any
files that have changed since the last run.

## Configuration

`config.yaml` holds the endpoint and credentials. See
`config.example.yaml` for a template with every option explained.
