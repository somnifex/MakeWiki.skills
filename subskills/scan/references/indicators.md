# Project Type Detection Indicators

## Supported Framework Indicators

- **Python CLI**: `pyproject.toml` (`[project.scripts]`), `setup.py`, `setup.cfg`, imports of `typer`, `click`, `argparse`.
- **Node/React**: `package.json` with `react` dependencies, `src/App.tsx`, `vite.config.ts`, `next.config.js`.
- **Node CLI**: `package.json` (`"bin"` field), `commander`, `yargs`, `cac`.
- **Go CLI / Service**: `go.mod`, `*.go`, `cobra`, `urfave/cli`, `gin-gonic/gin`, `labstack/echo`.
- **Rust CLI / Service**: `Cargo.toml`, `src/main.rs`, `clap`, `axum`, `actix-web`.