---
name: makewiki-init
description: "Generate a default makewiki.config.yaml configuration file in the current project with multi-agent budget, static site, evidence, review and quality-gate options. Use when: user wants to customize MakeWiki behavior before generating docs. Fields are either consumed by the Python Mechanical Plane or by the LLM Skill layer — no dead config."
version: "2.0.0"
argument-hint: "[--lang <code>...]"
license: MIT
allowed-tools: Bash(python */scripts/bootstrap_toolkit.py) Bash(python */scripts/run_toolkit.py *) Write
---

# MakeWiki Init - Generate Configuration

Create a default `makewiki.config.yaml` in the current project root.

## Execution

### Step 1: Bootstrap the home-scoped toolkit

```bash
python scripts/bootstrap_toolkit.py
```

### Step 2: Create Configuration File

The canonical config is emitted by the Python config model, so do not hand-write
or paste an inline copy — hand-maintained YAML drifts from the model. Generate
the default config for the target directory instead:

```bash
python scripts/run_toolkit.py init-config <target>
```

`<target>` is the directory where `makewiki.config.yaml` should be created
(omit or pass `.` for the current directory). This emits the full config
derived from `MakeWikiConfig` (`src/makewiki_skills/config.py`), covering every
field — including `agent.*` resource limits, `documentation_policy.*` writer
guidance, `delivery.*`, `quality.*`, and `scan.*` options.

If the user wants to hand-edit a config, point them at the checked-in reference
template: `templates/config.yaml` (mirrored at
`subskills/init/templates/default.config.yaml`). Every field in that template is
annotated `# Python-consumed` or `# LLM-consumed`; the contract tests in
`tests/contracts/test_config_consumption_contract.py` enforce that no field is
dead.
