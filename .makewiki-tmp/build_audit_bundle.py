"""Build + validate the Final Semantic Auditor bundle.

Input: a JSON file of verdicts:
  {"auditor": "llm_auditor",
   "verdicts": [{"review_item_id": "L3:...|L4b:...|L5:...",
                 "status": "passed"|"failed",
                 "rationale_summary": "...",
                 "evidence_refs": ["controller/token.go:264-341"],
                 "confidence": "high"}]}

Digests are computed by the toolkit (never hand-rolled):
  documents_digest = compute_documents_digest(wiki_dir)
  semantic_model_digest stays None (V3 authority is DocumentationModel).

Output: <bundle_out> validated via validate_bundle_shape.
"""
import json, sys

sys.path.insert(0, r"C:/Users/howie/Desktop/MyProject/MakeWiki.skills/src")

from pathlib import Path
from makewiki_skills.verification.semantic_audit import (
    SemanticAuditBundle,
    SemanticAuditVerdict,
    compute_documents_digest,
    validate_bundle_shape,
)

def build(verdicts_in, wiki_dir, bundle_out, auditor="llm_auditor"):
    wiki = Path(wiki_dir)
    doc_paths = sorted(p for p in wiki.rglob("*.md"))
    digest = compute_documents_digest(doc_paths)
    verdicts = [
        SemanticAuditVerdict(
            review_item_id=v["review_item_id"],
            layer=v["review_item_id"].split(":", 1)[0],
            status=v["status"],
            rationale_summary=v["rationale_summary"],
            evidence_refs=list(v.get("evidence_refs", [])),
            confidence=v.get("confidence", "medium"),
        )
        for v in verdicts_in
    ]
    from datetime import datetime, timezone
    bundle = SemanticAuditBundle(
        schema_version="1",
        documents_digest=digest,
        semantic_model_digest=None,
        auditor=auditor,
        audited_at=datetime.now(timezone.utc).isoformat(),
        verdicts=verdicts,
    )
    validate_bundle_shape(bundle)
    out = Path(bundle_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(json.loads(bundle.model_dump_json()), indent=1, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"OK bundle written: {out} verdicts={len(verdicts)} digest={digest[:16]}...")

if __name__ == "__main__":
    src, wiki_dir, bundle_out = sys.argv[1], sys.argv[2], sys.argv[3]
    data = json.load(open(src, encoding="utf-8"))
    ids = [v["review_item_id"] for v in data["verdicts"]]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        print("DUPLICATE review_item_id in verdicts:", sorted(dup)[:5])
        sys.exit(1)
    build(data["verdicts"], wiki_dir, bundle_out, data.get("auditor", "llm_auditor"))
