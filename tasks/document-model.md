# Task: Documentation Modeling (文档语义建模)

## Overview

Documentation Modeling is the core V3 layer that takes the canonical **`SemanticModel`**
(*what the software is*) and translates it into the **`DocumentationModel`** (*which people,
for which goals, need to understand which concepts, perform which tasks, and query which
references*). The **Documentation Architect** performs this translation.

The `DocumentationModel` is a semantic audience/goal model, **not** a page or route
layout. Page structure and membership are decided later in Documentation Planning.

---

## 1. Input / Output

```text
SemanticModel (+ RepositoryBrief, relevant claims/evidence)
→ DocumentationModel
```

The `DocumentationModel` must include:

```text
personas
capabilities
journeys
concepts
references
interface_references
documentation_gaps
```

Each fully specified with `evidence_refs` and honest `confidence`.

---

## 2. Persona

A persona is a distinct audience with stable goals. It is **not** a fixed mandatory list.

```yaml
persona:
  id: operator
  name: Operator
  goals:
    - deploy safely
    - monitor health
    - manage configuration
    - recover from failures
  permissions: []
  evidence_refs: []
  confidence: high
```

Candidate personas (only those with evidence exist): `end-user`, `developer`,
`administrator`, `operator`, `platform-admin`, `root`, `maintainer`, `SDK consumer`,
`plugin author`.

### Operator / administrator is first-class

When the repository shows production deployment, a management surface, operational
interfaces, or an admin/management API, the Architect **must** explicitly identify an
`operator` / `administrator` / `platform-admin` persona. Operator concerns are not just
a note buried inside a deployment page — when evidence supports them, they get their own
documented treatment.

---

## 3. Capability

A capability is a stable product ability one or more personas can use or depend on.

```yaml
capability:
  id: channel.manage
  name: Manage channels
  personas:
    - admin
    - operator
  goal: Configure upstream provider connectivity.
  operations:
    - create
    - edit
    - test
    - disable
    - delete
  constraints: []
  evidence_refs: []
  visibility: admin
```

---

## 4. Journey

A journey expresses the semantic steps of a user/operator goal. UI coordinates and
button labels are **not** required; steps must be provable from source.

```yaml
journey:
  id: channel.add
  persona: admin
  goal: Add an upstream provider channel.
  prerequisites:
    - provider credentials
  steps:
    - choose provider/channel type
    - provide credentials
    - configure supported models
    - save configuration
    - validate/test channel if supported
  expected_result:
    - channel becomes available to routing
  failure_conditions: []
  evidence_refs: []
```

Every step that cannot be proven from source must be **downgraded in confidence or
removed** — never padded to look complete.

---

## 5. Concept

A concept serves explanation / mental model.

```yaml
concept:
  id: channel
  definition: ""
  why_it_matters: ""
  related:
    - model
    - group
    - routing
  evidence_refs: []
```

---

## 6. Reference

A reference serves stable lookup, e.g. configuration keys, environment variables, CLI
commands, permissions, model fields, file formats, compatibility.

---

## 7. InterfaceReference

Interface references model stable interfaces, including:

```text
HTTP API
admin API
management API
RPC
webhook
event/message contract
health/readiness endpoint
metrics endpoint
CLI interface
configuration interface
```

HTTP / CLI / operator-interface details follow `API_REFERENCE.md`: operation contracts
(method, path, purpose, audience, auth, params, request/response, errors, side effects,
idempotency, pagination, rate limits) with every unproven field kept at `UNKNOWN`, `null`,
or omitted — **never guessed**. Each `InterfaceReference` is part of the DocumentationModel;
it is not a Python-generated OpenAPI.

### 7.1 Interface disposition (interface 去向)

For every interface operation the Architect deems **important**, record an explicit
disposition rather than silently omitting it:

```yaml
interface_disposition:
  operation_id: channel.create
  disposition: documented   # documented | grouped | omitted | unresolved
  page_id: reference/management-api/channels/create
  reason: ""                # required when omitted (e.g. internal-only)
  gap_id: ""                # required when unresolved
```

Rules:

- `documented` / `grouped` → must carry `page_id`.
- `omitted` → must carry a semantic `reason` (e.g. internal-only, not for the target
  persona).
- `unresolved` → must point to a `documentation_gap`; never claim covered.

Python may later validate *that a disposition exists and is complete*, but must never
decide which operation is important or which page it belongs on.

---

## 8. DocumentationGap

Do not hide capabilities that cannot be fully documented.

```yaml
documentation_gap:
  id: gap.admin-api.error-schema
  severity: major
  reason: >
    Route and request body are confirmed, but repository evidence does not
    establish a stable error response schema.
  affected_pages:
    - admin-api/channel-create
```

---

## 9. Audience hierarchy (no single "dual" string)

V3 does **not** collapse all audiences into one `audience: dual` string. The Architect
identifies persona-specific documentation. A page may serve multiple personas, but only
with a clear reason. Avoid mixing unrelated audiences in one page, e.g. an end-user
tutorial + ORM table structure + root-only admin API + production recovery runbook.

---

## 10. Operator / Admin / API reference must be explicitly considered

When an operator/admin persona or a management/API surface exists, the Architect must
explicitly check (where evidence supports it):

```text
deployment
configuration sources and precedence
secrets/credential handling — only where evidence exists
health/readiness
metrics/observability
logs
admin/management interfaces (HTTP / CLI)
maintenance operations
upgrade/migration
backup/restore
failure recovery
rate/capacity constraints
dependency requirements
```

Only the parts that source evidence supports are produced. That which cannot be proven
is not fabricated.

---

## 11. Prohibitions & Strict Boundaries

During documentation modeling the Architect **MUST NOT**:
1. **Fix the page directory / routes** — the model lists personas, capabilities,
   journeys, concepts, references, interface references, and gaps; it does not lay out
   the final site tree (that is Documentation Planning).
2. **Write Markdown pages** — no end-user prose, manual pages, or runbooks yet.
3. **Re-decide semantic truth** — documentation modeling derives from the `SemanticModel`
   and its evidence, not from a fresh reinterpretation of source.
4. **Guess unproven interface contracts** — missing fields stay `UNKNOWN` / `null`.
5. **Leak internal-only facts into end-user-facing intent** — respect the public /
   internal boundary established in the SemanticModel.
6. **Let Python infer personas, capabilities, journeys, or interface purpose** — these
   are LLM decisions; Python only validates structure.

---

## 12. Stop Conditions

The Architect **MUST STOP** when:
1. All major personas are identified (operator/admin explicitly considered when evidence
   warrants) with goals and evidence.
2. Every major capability is represented and tied to personas.
3. High-value journeys, concepts, references, and interface references are modeled.
4. Management / admin / API reference needs are explicitly considered.
5. Documentation gaps are recorded instead of papered over.
6. No page directory has been fixed and no Markdown page has been written.

Terminate with a single status (`completed`, `blocked`, or `needs_followup`) and report
the `artifact produced`, `uncertainties`, and any `scope expansions`.
