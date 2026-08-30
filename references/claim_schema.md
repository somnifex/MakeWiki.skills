# Claim Schema & Representation Standard


## Overview

In MakeWiki v2, documentation is treated as a set of **structured, verifiable
Claims** rather than unconstrained markdown strings. All multi-language
writers render verified Claims. Every Claim carries a `provenance` marker
that distinguishes **LLM-authored claims** (`llm_claim`) from **Python-extracted
facts** (`python_fact`); the L0–L5 verification pipeline grades both using
the same status vocabulary, but `llm_claim` items are subject to additional
over-assertion review at L5.

---

## 0. The Four-Layer Claim Vocabulary

Claims flow through four layers from raw mechanical evidence to accepted
documentation fact:

```
EvidenceFact        -> scanner raw deterministic facts
     │  (Python normalizes provenance="python_fact")
     ▼
MechanicalAssertion -> Python normalized statement of deterministic evidence
     │  (LLM Scout authors provenance="llm_claim")
     ▼
AgentClaim          -> LLM-authored semantic claims (carries semantic_key)
     │  (ReBattle cross-examination + Judge ruling)
     ▼
AdjudicatedClaim    -> accepted post-ReBattle consensus fact (explicit ruling only)
     │
     ▼
SemanticModel
```

| Layer                 | Class (import path)                                                      | Provenance    | Producer                                            | Keyed by                   |
| --------------------- | ------------------------------------------------------------------------ | ------------- | --------------------------------------------------- | -------------------------- |
| `EvidenceFact`        | `toolkit.evidence.EvidenceFact`                                          | — (raw)       | scanner                                             | claim text                 |
| `MechanicalAssertion` | `model.claim.MechanicalAssertion` == `model.claim.Claim` (`python_fact`) | `python_fact` | `build_claims_from_evidence`                        | `project_name`             |
| `AgentClaim`          | `model.rebattle.AgentClaim`                                              | `llm_claim`   | Scout / debate LLM agents; `ClaimSet.from_llm_json` | REQUIRED `semantic_key`    |
| `AdjudicatedClaim`    | `model.rebattle.AdjudicatedClaim`                                        | `adjudicated` | ReBattle + Judge (`synthesize_consensus`)           | wrapped `AgentClaim`       |

**Provenance values** carried on `model.claim.Claim`:

- `python_fact` — deterministic fact extracted and normalized by Python. This
  is the **MechanicalAssertion** layer. Python is allowed to prove it.
- `llm_claim` — semantic claim authored by an LLM subagent (the **AgentClaim**
  layer). Python validates schema and verifies, but never invents it.
- `adjudicated` — an accepted post-ReBattle consensus fact (an AgentClaim that
  survived cross-examination and received a Judge ruling, once folded back
  into the model). Guarantees the claim has been reviewed and upheld.

> Note: `model.rebattle.Claim` / `model.rebattle.ClaimSet` are **deprecated**
> aliases for the canonical `AgentClaim*` names. `model.claim.Claim` (the
> mechanical layer) is not the same as `model.rebattle.AgentClaim`.

### Cognitive Authority Boundary: only a Judge ruling creates an AdjudicatedClaim

MakeWiki is *strong LLM + weak code + code evidence*. Python never adjudicates
and never invents cognitive content:

- **No auto-accept.** A claim that survives cross-examination with no dispute
  is **NOT** wrapped as `ruling="accepted"`. "No challenge" means
  undisputed / pending-adjudication. `synthesize_consensus` only produces an
  `AdjudicatedClaim` when an explicit `AdjudicationResult` (Judge ruling)
  exists for that claim; an undisputed claim is returned as a plain, pending
  `AgentClaim`.
- **Rejected / hedged rulings** never enter the authoritative model.
- `fold_adjudicated_into_semantic_model` is the ONLY Python path by which
  cognitive content enters the `SemanticModel`, and it ingests ONLY
  `AdjudicatedClaim` — never a raw `AgentClaim` or `MechanicalAssertion`.

---

## 1. Claim Data Model

### AgentClaim (model.rebattle)

```json
{
  "claim_id": "claim-a1b2c3d4",
  "agent_id": "agent_red",
  "perspective": "user_experience",
  "claim_type": "workflow",
  "semantic_key": "workflow.auth",
  "assertion": "Login -> token -> refresh, then JWT issued.",
  "value": "auth flow",
  "subject": "myapp",
  "predicate": "authenticates_users",
  "object": "auth flow",
  "source_file": "src/auth.py",
  "evidence_refs": ["src/auth.py"],
  "confidence": "high"
}
```

`semantic_key` is **REQUIRED** and is the canonical *meaning* of the claim (a
dotted path such as `network.port` or `workflow.auth`). `evidence_refs`
defaults to `[]` and maps from `source_file` when present.

### Claim / MechanicalAssertion (model.claim)

```json
{
  "claim_id": "CLI_SCAN_JSON",
  "claim_type": "command",
  "semantic_key": "scanner.cli.scan",
  "subject": "makewiki scan",
  "predicate": "produces",
  "object": "structured JSON evidence bundle",
  "provenance": "python_fact",
  "command": {
    "executable": "makewiki",
    "subcommand": "evidence",
    "arguments": ["."],
    "flags": ["--format json"],
    "expected_output_type": "application/json"
  },
  "evidence": [
    {
      "source_file": "src/makewiki_skills/cli.py",
      "line_range": [120, 145],
      "raw_text": "@app.command(name=\"evidence\")\ndef evidence(...):",
      "extraction_method": "ast_parser",
      "confidence": "high"
    }
  ],
  "verification": {
    "l0_syntax": "passed",
    "l1_existence": "passed",
    "l2_interface": "passed",
    "l3_behavior": "pending",
    "l4_cross_language": "pending",
    "l5_epistemic": "pending"
  },
  "uncertainty": null
}
```

The canonical field name is **`claim_type`** (not `type`). The full ClaimType
vocabulary — used for both mechanical and cognitive claims — is:

- **Mechanical** (Python proves): `command`, `config`, `path`, `version`
- **Cognitive** (LLM Agent authors): `workflow`, `persona`, `prerequisite`,
  `behavior`, `error_case`, `faq_topic`, `troubleshooting`, `constraint`,
  `capability`, `architecture`

There is **no `ngx`** type; that was a historical typo. A `claim_id` is a
stable unique slug (`[A-Za-z0-9._-]+`) and is **not** forced to carry a
mechanical `CMD_`/`CFG_`/`PATH_`/`VER_` prefix — cognitive claims use free-form
ids such as `FW_AUTH_FLOW`. A semantic_key is a slash-shaped dotted path.

`l3_behavior`, `l4_cross_language` (prose portion), and `l5_epistemic` are
**LLM-judged layers**: Python emits the underlying evidence and a tentative
status, and the Skill layer's Auditor / Semantic Revision step resolves them
into `passed` / `failed` / `hedged`. The Quality Gate reads the resolved
status to decide PASS / FAIL.

---

## 2. ReBattle keys on meaning (semantic_key), never value

ReBattle groups and compares claims by `semantic_key`:

- Two agents asserting **different values** (port 3000 vs 8080) but the **same**
  `semantic_key` land in **one** discrepancy.
- The **same value** under **different** `semantic_key` never collides.
- `claim_type` is a secondary attribute retained on a `Discrepancy` for display
  only.

`detect_discrepancies` builds `{semantic_key -> claims}` and flags a group when
multiple agents assert differing assertions, or when a claim's confidence is
`inferred`/`low`. `synthesize_consensus` and `_consensus_agent_claims` also key
and deduplicate by `semantic_key`.

---

## 3. Claim-Level Multilingual Rendering

All target languages (`en`, `zh-CN`, `ja`, etc.) share the exact same `claim_id`
and executable command representation:

- **English Prose**: `Run \`makewiki evidence . --format json\` to generate a structured evidence bundle.`
- **Chinese Prose**: `运行 \`makewiki evidence . --format json\` 获取结构化代码证据清单。`

This guarantees 100% parameter and code block parity across all language
versions. The Mechanical Plane enforces exact block parity by comparing block
IDs; the LLM-driven Auditor resolves prose parity via `semantic-review`.
