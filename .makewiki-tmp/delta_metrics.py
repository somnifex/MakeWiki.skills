"""Delta benchmark metric capture: run1 vs run2.

Captures METRIC 1-5 for the NewAPI delta benchmark:
 M1 Quality Gate signal (false path/config facts, unresolved critical, blocker ratio)
 M2 Revision efficiency (convergence agents needed, marker/block mismatches after round-1)
 M3 Integration defects (frontmatter/artifact paths/dispositions/markers/block drift)
 M4 Documentation quality (page granularity, coverage — from artifacts)
 M5 Agent cost (subtask counts from the delegation trace)
"""
import json, sys, os
from pathlib import Path

RUN1 = Path(r'C:/Users/howie/Desktop/MyProject/new-api/makewiki-v3/.makewiki-artifacts')
RUN2 = Path(r'C:/Users/howie/Desktop/MyProject/new-api/makewiki-v3-run2/.makewiki-artifacts')

def gate_metrics(verify_json):
    d = json.load(open(verify_json, encoding='utf-8'))
    rep, g = d['report'], d['quality_gate']
    l1 = [c for c in rep['layers']['L1']['checks'] if c['status'] == 'failed']
    paths = sum(1 for c in l1 if c['claim_type'] == 'path')
    cks = sum(1 for c in l1 if c['claim_type'] == 'config_key')
    l4 = [c for c in rep['layers']['L4']['checks'] if c['status'] == 'failed']
    l4_fact = sum(1 for c in l4 if c['claim_text'].startswith(('command', 'config_key', 'file_path', 'version')))
    return {
        'verdict': g['verdict'],
        'unresolved_critical': g.get('unresolved_critical'),
        'grounding': g.get('grounding_score'),
        'mechanical_score': g.get('mechanical_score'),
        'semantic_coverage': g.get('semantic_coverage'),
        'l1_failed': len(l1),
        'l1_path_failed': paths,
        'l1_config_failed': cks,
        'l4_failed': len(l4),
        'l4_fact_failed': l4_fact,
        'l0_failed': sum(1 for c in rep['layers']['L0']['checks'] if c['status'] == 'failed'),
        'l4a_failed': sum(1 for c in l4 if c['claim_type'] == 'l4a_mechanical' and 'Stable block' in c['claim_text']),
        'semantic_complete': g.get('semantic_complete'),
        'total_checks': sum(len(lr['checks']) for lr in rep['layers'].values()),
    }

if len(sys.argv) > 1 and sys.argv[1] == 'compare':
    m1 = gate_metrics(RUN1 / '16-semantic-audit-bundle' / 'verify_final.json')
    m2 = gate_metrics(RUN2 / '16-semantic-audit-bundle' / 'verify_final.json')
    print(f"{'metric':28} {'run1':>8} {'run2':>10}")
    for k in m1:
        print(f"{k:28} {str(m1[k]):>8} {str(m2.get(k, 'n/a')):>10}")
