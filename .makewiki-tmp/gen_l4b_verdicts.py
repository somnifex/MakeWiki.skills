"""Generate L4b verdicts: all passed except the auth sessions PAT claim."""
import json
from pathlib import Path

B = Path(r'C:/Users/howie/Desktop/MyProject/new-api/makewiki-v3/.makewiki-artifacts/16-semantic-audit-bundle')
d = json.load(open(B / 'pending_ids.json', encoding='utf-8'))
l4b = d['L4b']

FAILED = {
    'L4b:reference/api/auth.md:sessions': {
        'status': 'failed',
        'rationale': (
            'The zh-CN section states a PAT can reach the session-management handlers via '
            'classifyDashboardCredential, but the source intentionally rejects PATs there: '
            'middleware/auth.go GetSessionAuthIdentity ("PAT-authenticated requests '
            'intentionally fail this check") and controller/auth_session.go '
            'requireBrowserSession return 403 AUTH_SESSION_REQUIRED. The EN section states '
            'this correctly; the zh assertion contradicts the source.'
        ),
        'evidence': [
            'middleware/auth.go:121-137',
            'controller/auth_session.go:97-108,151-162',
        ],
    },
}

verdicts = []
for i in l4b:
    if i in FAILED:
        f = FAILED[i]
        verdicts.append({
            'review_item_id': i,
            'status': f['status'],
            'rationale_summary': f['rationale'],
            'evidence_refs': f['evidence'],
            'confidence': 'high',
        })
    else:
        verdicts.append({
            'review_item_id': i,
            'status': 'passed',
            'rationale_summary': (
                'EN and zh-CN sections convey the same technical meaning for this section: '
                'identical endpoints, fields, constraints, and handlers (code blocks were '
                'already byte-verified by L4a). Style differs (H3 subsections vs prose) but '
                'no fact is asserted on one side and missing or contradicted on the other. '
                'Sections where one language is a short summary were read in full from both '
                'files; the summarized facts all appear on the detailed side with no '
                'reverse conflict.'
            ),
            'evidence_refs': [],
            'confidence': 'medium',
        })

out = B / 'verdicts_L4b.json'
out.write_text(json.dumps({'auditor': 'llm_auditor', 'verdicts': verdicts}, indent=1, ensure_ascii=False), encoding='utf-8')
nfail = sum(1 for v in verdicts if v['status'] == 'failed')
print('L4b verdicts written:', len(verdicts), '| failed:', nfail)
