# Core Data Contracts & Schemas

## 1. SemanticModel

```json
{
  "identity": {
    "name": "my-app",
    "version": "2.0.0",
    "description": "Short project description"
  },
  "installation": {
    "prerequisites": [{"name": "Node.js", "version_constraint": ">=18"}],
    "steps": [{"order": 1, "title": "Install", "commands": ["npm install"]}],
    "verify_command": "npm test"
  },
  "commands": [
    {
      "name": "my-app start",
      "description": "Start the service",
      "args": [{"name": "--port", "description": "Port number", "default": "3000"}]
    }
  ],
  "configuration": [
    {
      "name": "Server",
      "items": [{"key": "PORT", "description": "HTTP port", "default_value": "3000"}]
    }
  ]
}
```

## 2. EvidenceBundle

```json
{
  "detection": {
    "project_name": "my-app",
    "project_type": "node-cli",
    "confidence": 0.95
  },
  "total_facts": 12,
  "summary": {"command": 4, "config_key": 6, "path": 2},
  "commands_discovered": ["npm run build", "npm start"]
}
```

`evidence` (alias `scan`) emits this bundle. It contains **facts only**:
deterministic extractions from the codebase. No interpretation of what the
repository *means* is included — that is the LLM's responsibility.

---

## 3. SemanticModel — LLM-populated fields

The `SemanticModel` separates **mechanical identity** (filled by Python from
evidence) from **semantic content** (filled by the LLM from comprehension).
Python never invents items in the semantic sections; when the LLM leaves them
empty, the corresponding Markdown slot renders an `UNKNOWN` marker rather than
fabricated prose.

| Section                | Source                                            | Notes                                                    |
| ---------------------- | ------------------------------------------------- | -------------------------------------------------------- |
| `identity`             | python + LLM                                      | `name`/`version` mechanical; `description` LLM-written.  |
| `installation`         | python (steps) + LLM (verify_command via `claim`) | `verify_command` is `UNKNOWN` unless a Claim proves it.  |
| `commands`             | python (AST/CLI help)                             | Mechanical only.                                         |
| `configuration`        | python (config scan)                              | Mechanical only.                                         |
| `faq`                  | **LLM only**                                      | Empty → rendered as `UNKNOWN`. Never invented by Python. |
| `troubleshooting`      | **LLM only**                                      | Empty → rendered as `UNKNOWN`. Symptom→cause→fix chains. |
| `usage_examples`       | **LLM only**                                      | Empty → rendered as `UNKNOWN`. Task-oriented how-tos.    |
| `command_groups`       | **LLM only**                                      | Empty → rendered as `UNKNOWN`. Workflow groupings.       |
| `user_tasks`           | **LLM only**                                      | Persona + goal mapping. Never auto-synthesized.          |
| `platform_notes`       | **LLM only**                                      | OS-specific caveats. No canned notes from Python.        |
| `env_vars`             | python + LLM                                      | Mechanical discovery + LLM-described semantics.          |
| `compatibility_matrix` | **LLM only**                                      | Empty → rendered as `UNKNOWN`.                           |
| `health_checks`        | **LLM only**                                      | Empty → rendered as `UNKNOWN`.                           |
| `deployment_notes`     | **LLM only**                                      | Empty → rendered as `UNKNOWN`.                           |
| `log_paths`            | python + LLM                                      | Mechanical discovery + LLM explanation.                  |

`provenance` is stamped on each node (`"python"` | `"llm"` | `"unknown"`) so
the verification layers can distinguish mechanically extracted facts from
LLM-authored claims and surface the latter for evidence audit.

---

## 4. Claim

See `references/claim_schema.md` for the full Claim data model. A Claim is the
unit the L0–L5 verification layers grade; `provenance` (`llm_claim` vs
`python_fact`) lets the Quality Gate distinguish facts from authored content
when scoring over-assertion risk.