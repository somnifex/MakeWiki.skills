# gateway

A small service whose configuration is contradictory: `config.yaml` declares
`server.port: 8080` while `docker-compose.yml` declares `PORT=9090` for the
same service. There is no source of truth that reconciles the two.

Docs must surface the contradiction as a dispute — not silently pick one port
as canonical. If forced to state a value, docs should hedge / mark UNKNOWN and
flag that `config.yaml` and `docker-compose.yml` disagree.
