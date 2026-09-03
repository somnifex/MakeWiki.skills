"""Merge L3/L4b/L5 verdict files into one validated SemanticAuditBundle."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, r"C:/Users/howie/Desktop/MyProject/MakeWiki.skills/src")

from makewiki_skills.verification.semantic_audit import (
    SemanticAuditBundle,
    compute_documents_digest,
    validate_bundle_shape,
)

B = Path(r'C:/Users/howie/Desktop/MyProject/new-api/makewiki-v3/.makewiki-artifacts/16-semantic-audit-bundle')
WIKI = Path(r'C:/Users/howie/Desktop/MyProject/new-api/makewiki-v3/makewiki')

pending = json.load(open(B / 'pending_ids.json', encoding='utf-8'))
valid_ids = set()
for ids in pending.values():
    valid_ids.update(ids)

verdicts = []
seen = set()
problems = []
for name in ['verdicts_L3.json', 'verdicts_L4b.json', 'verdicts_L5.json']:
    data = json.load(open(B / name, encoding='utf-8'))
    for v in data['verdicts']:
        rid = v['review_item_id']
        if rid in seen:
            problems.append('DUPLICATE ' + rid)
            continue
        seen.add(rid)
        if rid not in valid_ids:
            problems.append('UNKNOWN ' + rid)
            continue
        verdicts.append(v)

if problems:
    for p in problems[:10]:
        print(p)
    sys.exit(1)

missing = {}
for layer, ids in pending.items():
    m = [i for i in ids if i not in seen]
    if m:
        missing[layer] = m
if missing:
    for layer, m in missing.items():
        print(f'UNADJUDICATED {layer}: {len(m)}')
        for x in m[:8]:
            print('   ', x[:110])
    sys.exit(1)

doc_paths = sorted(WIKI.rglob('*.md'))
digest = compute_documents_digest(doc_paths)
bundle = SemanticAuditBundle(
    schema_version='1',
    documents_digest=digest,
    semantic_model_digest=None,
    auditor='llm_auditor',
    audited_at=datetime.now(timezone.utc).isoformat(),
    verdicts=[
        {
            'review_item_id': v['review_item_id'],
            'layer': v['review_item_id'].split(':', 1)[0],
            'status': v['status'],
            'rationale_summary': v['rationale_summary'],
            'evidence_refs': list(v.get('evidence_refs', [])),
            'confidence': v.get('confidence', 'medium'),
        }
        for v in verdicts
    ],
)
validate_bundle_shape(bundle)
OUT = B / 'semantic_audit.json'
OUT.write_text(json.dumps(json.loads(bundle.model_dump_json()), indent=1, ensure_ascii=False), encoding='utf-8')
nfail = sum(1 for v in verdicts if v['status'] == 'failed')
print(f'OK wrote {OUT.name}: {len(verdicts)} verdicts ({nfail} failed), digest {digest[:22]}')
