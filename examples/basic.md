# Basic Example: Single-Module Python CLI

## 1. Project Profile

- **Type**: Python CLI (Typer / Click)
- **Files**: 8 source files (Single-module)
- **Target**: `examples/sample-python-cli`

## 2. Command Invocation

```bash
/makewiki --lang en --lang zh-CN
```

## 3. Autonomous Execution Flow

1. **Phase 0 (Census)**: Raw facts extracted (8 files, single CLI entrypoint). Main Agent synthesizes consolidated scout and 2 writers.
2. **Phase 1 (Scout)**: Discovers `sample-cli greet <name>`, `--count`, and `.env.example`.
3. **Phase 2 (ReBattle)**: Fast-path consensus verifies commands against Typer AST (0 debate rounds).
4. **Phase 3 (Writers)**: Generates 7 pages for English and 7 pages for Chinese.
5. **Phase 4 (Review)**: Verifies 100% command parity between `README.md` and `README.zh-CN.md`.
6. **Phase 5 (Site)**: Compiles `makewiki/site/index.html`.