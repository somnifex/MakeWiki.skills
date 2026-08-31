# MakeWiki V3 Quality Policy


## 1. Preserve V2 quality assets

必须保留：

```text
L0-L5
SemanticAuditBundle
item-level review_item_id
documents_digest
semantic_model_digest
stale audit rejection
stable code block IDs
stable section IDs
honest four-state Quality Gate
```

## 1A. SemanticAuditBundle schema & consumption

The semantic layers — L3 behavior meaning, L4b prose parity, L5 epistemic
standing — are decided by the Final Semantic Auditor (LLM), not by mechanical
code. The Auditor persists its verdicts into a machine-readable
`SemanticAuditBundle` JSON that the toolkit consumes without re-judging.

### The bundle is ITEM-LEVEL

Each `SemanticAuditVerdict` targets exactly one `review_item_id` (e.g.
`L3:README.md:make build`, `L4b:README:build`, `L5:README.md:make build`). The
merge maps each verdict to exactly one verification check; review items the
Auditor does NOT mention **remain PENDING**. A verdict for an unknown
`review_item_id` (matching no expected review item) **rejects the whole bundle**
— it is never silently ignored.

### Review item registry

After mechanical verification, the report exposes `review_items` — the expected
semantic review items for L3 / L4b / L5 that need LLM adjudication, each with a
deterministic `review_item_id`. The bundle can only adjudicate items that exist
in this registry.

### Bundle schema

```yaml
schema_version: 1                       # bundle schema version
documents_digest: "sha256:<hex>"        # sha256 over the audited markdown doc set
semantic_model_digest: "sha256:<hex>"   # optional; binds to the SemanticModel snapshot
auditor: "llm_auditor"                  # auditor identity
audited_at: "<UTC ISO-8601>"            # when the audit was performed
verdicts:                               # list of semantic verdicts
  - review_item_id: "L3:README.md:make build"   # exactly one review item per verdict
    layer: "L3"                         # one of L3 | L4b | L5
    status: "passed"                    # one of passed | failed
    rationale_summary: "..."            # why the Auditor judged this way
    evidence_refs: ["src/app/cli.py:120-148"]   # optional source citations
    confidence: "medium"                # one of high | medium | low
```

`documents_digest` includes document identity: it hashes each file as
`relative_path + NUL + byte_length + NUL + file_bytes + NUL`, sorted by
normalized relative path — so the digest changes on content edit, rename,
delete, add, and file split, and is stable across machines (no absolute paths
are hashed); it binds the audit to the exact document revision it was performed
against.

`semantic_model_digest` (optional) is the canonical SHA256 of the SEPARATE
authoritative SemanticModel the bundle claims to have been audited against. It
is proven by supplying the current model via `verify-docs --semantic-model
<file>`; the digest uses sorted keys and compact separators so it is stable.

### Staleness rule

If the documents (or the optional semantic model snapshot) change **after** the
bundle was produced, the bundle's digest no longer matches, so the bundle is
**stale and must be rejected and re-audited**. The toolkit raises a stale-audit
error rather than silently trusting an audit of an older revision. The Auditor
must therefore emit the bundle **last**, after all revisions (Review / Revision
are settled), so its `documents_digest` matches the final markdown set on disk.

### Consumption boundary

Python validates the bundle's schema and digests and aggregates the verdicts
ITEM-LEVEL into the Quality Gate, but it **never re-judges the semantic
verdicts**: it does not decide whether a `passed`/`failed` verdict is
reasonable, and it never overrides the Auditor's adjudication. Each verdict
maps to exactly one check by its `review_item_id`; a layer the Auditor did not
mention, or a `review_item_id` it did not adjudicate, stays `pending`. Merged
checks carry `verification_source = "semantic_audit_bundle"` plus the verdict's
`review_item_id` and the Auditor's structured provenance
(`check.provenance`: auditor, rationale_summary, evidence_refs, confidence,
audited_at).

### `verify-docs --semantic-audit <file>` and `--semantic-model <file>`

The Auditor's bundle is machine-consumed by `verify-docs` via the
`--semantic-audit <file>` flag, and the current SemanticModel is supplied via
`--semantic-model <file>` (both on the existing command):

```bash
python run_toolkit.py verify-docs <target> \
  --semantic-audit <output_dir>/semantic_audit.json \
  --semantic-model <output_dir>/semantic_model.json
```

`verify-docs --semantic-audit <file>`:

1. loads and schema-validates the bundle;
2. verifies `documents_digest` against the current documents — a mismatched
   (stale) bundle is **rejected** and the affected layers remain `pending`,
   signaling that a re-audit is required;
3. builds the review-item registry from the pending L3 / L4b / L5 checks, then
   merges the Auditor's verdicts ITEM-LEVEL by `review_item_id` — each verdict
   adjudicates exactly one check; unmentioned pending items stay `pending`; a
   verdict for an unknown `review_item_id` REJECTS the whole bundle;
4. never re-judges the semantics — it only validates schema/digests and
   aggregates.

`--semantic-model <file>` supplies the current SemanticModel; its canonical
SHA256 (sorted keys, compact separators) proves the bundle's
`semantic_model_digest`. If the bundle declares a `semantic_model_digest` but
no `--semantic-model` is given, the model binding is **UNPROVEN** and L3 / L4b
/ L5 stay `pending`; a digest mismatch is **STALE** and the bundle is rejected.

## 2. Reviewer/Revision separation

V2 的 Auditor 可以边审边原地修改。

V3 改为：

```text
Reviewer
→ ReviewFindings
→ Revision Agent
→ re-review
```

Reviewer 默认只读。

## 2A. Page Reviewer vs Final Semantic Auditor

降低重复：Page Review（页面级）与 Final Semantic Audit（最终语义审定）职责收敛。

### Page Reviewer 只负责页面级 fitness/completeness

Page Review 负责：

```text
documentation fitness
audience fit
task completeness
operator completeness
API contract completeness
obvious unsupported/grounding defects
page-local cross-language issues (适用时)
```

Page Reviewer 不负责生成最终 authoritative：

```text
L3 behavior verdict registry
L4b final semantic parity verdict
L5 final epistemic verdict
SemanticAuditBundle
```

这些属于 **Final Semantic Auditor**。

仍然允许 Reviewer 发现明显 behavior/epistemic 问题（作为 finding 上报），
但不要求它完成整套 final semantic audit。

### Final Semantic Auditor 只负责最终 semantic assurance

Final Semantic Auditor 负责：

```text
L3 behavior verdicts
L4b cross-language semantic parity
L5 epistemic standing
cross-page semantic consistency
SemanticAuditBundle
stale/digest-sensitive final review
```

不要求再次全面检查：

```text
页面是否应该拆分
persona IA 是否合理
每个 how-to 是否有漂亮结构
PageSpec 是否应该存在
```

这些属于前面的 Documentation/Page Review 阶段。

Quality Gate 语义保留不变。

## 3. Review dimensions

### grounding

检查：

- source support；
- commands；
- config keys；
- interfaces；
- paths；
- examples。

### behavior

检查：

- workflow 是否达到文档声明目的；
- prerequisite；
- order；
- side effect；
- error handling。

### epistemic

检查：

- overclaim；
- guarantee；
- stale docs；
- uncertain facts；
- environment-dependent behavior。

### documentation fitness

检查：

- persona coverage；
- capability coverage；
- journey completeness；
- page intent；
- page overload；
- reference discoverability。

### audience fit

检查：

- 普通用户页面是否泄露 implementation；
- operator 信息是否足够；
- developer reference 是否混入 root-only 运维内容；
- 页面技术深度是否合适。

### abstraction correctness

新 categories：

```text
implementation_leakage
abstraction_mismatch
persona_mismatch
unsupported_product_rule
```

### task completeness

检查：

```text
goal
prerequisites
steps
expected result
recovery/caveat when important
```

### API contract review

检查：

```text
method/path
audience/auth
required params
request body
known responses/errors
side effects
idempotency when claimed
pagination/rate limit when claimed
examples
```

字段缺失本身不一定是错误。

“有证据但漏写”才是 completeness 问题。

“无证据却补写”是 grounding/epistemic 问题。

## 4. Documentation Fitness result

V3 初期建议作为 LLM review artifact，不立即硬编码成新的 Python L6。

原因：

这些判断主要是语义判断。

可以在 ReviewFindings 中表达：

```text
persona_coverage
capability_coverage
journey_coverage
operator_coverage
api_reference_coverage
page_overload
implementation_leakage
```

未来证明某些部分可机械验证后再加入工具。

## 5. Severity

建议：

```text
critical
major
minor
advisory
```

Critical 示例：

- destructive operator action documented incorrectly；
- auth/permission guidance wrong；
- endpoint method/path wrong；
- fabricated required parameter；
- critical workflow wrong。

Major：

- major capability missing；
- operator API largely undocumented；
- page serves wrong persona；
- important prerequisite omitted。

Minor：

- related link missing；
- small explanation gap；
- non-critical naming inconsistency。

## 6. Shipping policy

可以交付 pending 的行为继续由现有 Quality Gate config 控制。

但 completion report 必须区分：

```text
mechanical pending
semantic pending
documentation fitness findings
known documentation gaps
```

不能只报 grounding score。

## 7. Review loop

The review ↔ revision loop is bounded by the single authoritative budget:
**`agent.max_audit_rounds`** (the only audit-loop budget; see SKILL.md §2 and
`src/makewiki_skills/config.py`). There is **no** separate hard-coded per-page
revision-rounds value — the config field is the sole source of the cap.

仍然失败：

```text
escalate to Orchestrator
→ re-investigate or revise PageSpec/DocumentationModel
```

不能让 Writer 无限自修，也绝不新设独立于 `agent.max_audit_rounds` 的轮次上限。

## 8. NewAPI benchmark criteria

详见：

`evals/newapi-v3-rubric.md`
