# Example: makewiki-sync

```bash
# Prepare both Confluence and Notion import bundles (no publishing)
/makewiki-sync ./makewiki

# Generate Confluence bundle only for English docs
/makewiki-sync ./makewiki --target confluence --lang en
```

The authoritative toolkit command is `sync-bundle`; `sync` is retained as a
deprecated alias. The bundles are written to disk for manual import; no
external API calls are made.