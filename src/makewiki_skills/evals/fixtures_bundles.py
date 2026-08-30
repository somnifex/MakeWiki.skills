"""Deterministic fake-LLM run bundles for the hostless evals harness.

These represent the run *artifacts* a CORRECT full handoff would write for a
handful of canonical traps. They let ``--fixture prepare`` produce a run a
host-less CI can score end to end (Scout -> ReBattle -> Judge -> model ->
auditor -> gate) without a model host. They are NOT the proof that the real
pipeline behaves this way — that proof is the authoritative integration test —
they are only the harness's offline corpus.

Every bundle follows the run-artifact contract (:mod:`makewiki_skills.evals.artifact`)
and, critically, is a *correct* handoff: each required claim is surfaced, no
forbidden value is asserted, expected-UNKNOWN fields stay unasserted, and the
gate state is internally consistent (passed only when the audit is complete).
"""

# ---------------------------------------------------------------------------
# misleading-readme: README (3000) contradicts source (8080).
# Correct handoff: dispute surfaced, Judge accepts 8080, docs say 8080, the
# conflict is noted, and 3000 is never asserted as the default.
# ---------------------------------------------------------------------------

MISLEADING_README = {
    "trap": "misleading-readme",
    "run_id": "fixture-misleading",
    "evidence": {
        "facts": [
            {"id": "port_default_source", "semantic_key": "network.port.default", "value": "8080", "source": "app/server.py"},
            {"id": "port_readme_contradiction", "semantic_key": "network.port.default", "value": "3000", "source": "README.md"},
            {"id": "default_host", "semantic_key": "network.host.default", "value": "0.0.0.0", "source": "app/server.py"},
        ],
        "detected_packages": [],
    },
    "agent_claims": {
        "sets": [
            {
                "agent_id": "agent_red",
                "perspective": "user_experience",
                "claims": [
                    {"agent_id": "agent_red", "claim_type": "config", "semantic_key": "network.port.default",
                     "assertion": "default port is 3000", "value": "3000", "confidence": "low"}
                ],
            },
            {
                "agent_id": "agent_green",
                "perspective": "code_implementation",
                "claims": [
                    {"agent_id": "agent_green", "claim_type": "config", "semantic_key": "network.port.default",
                     "assertion": "default port is 8080 per app/server.py", "value": "8080",
                     "confidence": "high", "evidence_refs": ["app/server.py"]}
                ],
            },
        ]
    },
    "rebattle": {
        "discrepancies": [
            {"topic": "network.port.default", "participants": ["agent_red", "agent_green"],
             "source_values": {"agent_red": "3000", "agent_green": "8080"}}
        ]
    },
    "adjudications": {
        "rulings": [
            {"topic": "network.port.default", "ruling": "accepted", "final_assertion": "8080",
             "verified_via_codebase": True, "evidence_refs": ["app/server.py"],
             "adjudicator_reasoning": "source hard-codes DEFAULT_PORT=8080; README 3000 is stale"}
        ]
    },
    "semantic_model": {
        "dotenv": [],
        "user_tasks": [],
        "troubleshooting": [],
        "provenance": {"config": "llm"},
        "claims": [
            {"semantic_key": "network.port.default", "value": "8080", "claim_type": "config"}
        ],
    },
    "semantic_audit": {
        "auditor": "fake_llm_auditor",
        "documents_digest": "fixture",
        "verdicts": [
            {"review_item_id": "L3:README.md:config", "layer": "L3", "status": "passed"},
            {"review_item_id": "L4b:README.md:build", "layer": "L4b", "status": "passed"},
            {"review_item_id": "L5:README.md", "layer": "L5", "status": "passed"},
        ],
        "rejected": False,
        "rejection_reason": "",
    },
    "mechanical_report": {
        "total_checks": 5,
        "layers": [
            {"layer": "L0", "name": "Structure", "verdict": "passed", "checks": []},
            {"layer": "L1", "name": "Agents", "verdict": "passed", "checks": []},
            {"layer": "L2", "name": "Interface", "verdict": "passed", "checks": []},
            {"layer": "L4", "name": "Cross-lang", "verdict": "passed", "checks": [
                {"layer": "L4", "claim_type": "l4a_mechanical", "status": "passed",
                 "claim_text": "all technical blocks tagged", "detail": ""},
                {"layer": "L4", "claim_type": "l4a_mechanical", "status": "passed",
                 "claim_text": "stable block parity", "detail": ""},
                {"layer": "L4", "claim_type": "l4b_semantic", "status": "passed",
                 "review_item_id": "L4b:README.md:build", "detail": ""},
            ]},
            {"layer": "L3", "name": "Semantic", "verdict": "passed", "checks": [
                {"layer": "L3", "claim_type": "l3", "status": "passed", "review_item_id": "L3:README.md:config", "detail": ""}]},
            {"layer": "L5", "name": "Audit", "verdict": "passed", "checks": [
                {"layer": "L5", "claim_type": "l5", "status": "passed", "review_item_id": "L5:README.md", "detail": ""}]},
        ],
    },
    "quality_gate": {
        "verdict": "passed",
        "ci_exit_code": 0,
        "semantic_complete": True,
        "pending_llm_layers": [],
        "mechanical_passed": True,
    },
    "docs": {
        "README.md": (
            "# app\n\n"
            "By default the server listens on port **8080** (per `app/server.py`).\n\n"
            "> The README once claimed 3000; the source pins 8080, which is authoritative.\n"
        ),
    },
}


# ---------------------------------------------------------------------------
# ambiguous-install: only a pyproject with dev deps; no install instruction.
# Correct handoff: the deps are established, the exact install command is left
# UNKNOWN and never invented.
# ---------------------------------------------------------------------------

AMBIGUOUS_INSTALL = {
    "trap": "ambiguous-install",
    "run_id": "fixture-ambiguous",
    "evidence": {
        "facts": [
            {"id": "dev_deps", "semantic_key": "install.dependencies", "value": "pytest,ruff", "source": "pyproject.toml"}
        ],
        "detected_packages": [],
    },
    "agent_claims": {
        "sets": [
            {
                "agent_id": "agent_blue",
                "perspective": "code_implementation",
                "claims": [
                    {"agent_id": "agent_blue", "claim_type": "prerequisite", "semantic_key": "install.dependencies",
                     "assertion": "dev deps are pytest and ruff per pyproject", "value": "pytest,ruff",
                     "confidence": "high", "evidence_refs": ["pyproject.toml"]}
                ],
            }
        ]
    },
    "rebattle": {"discrepancies": []},
    "adjudications": {
        "rulings": [
            {"topic": "install.dependencies", "ruling": "accepted", "final_assertion": "pytest,ruff",
             "verified_via_codebase": True, "evidence_refs": ["pyproject.toml"],
             "adjudicator_reasoning": "pyproject.toml declares dev deps"}
        ]
    },
    "semantic_model": {
        "dotenv": [],
        "user_tasks": [],
        "troubleshooting": [],
        "provenance": {"install": "llm"},
        "claims": [
            {"semantic_key": "install.dependencies", "value": "pytest,ruff", "claim_type": "prerequisite"}
        ],
    },
    "semantic_audit": {
        "auditor": "fake_llm_auditor",
        "documents_digest": "fixture",
        "verdicts": [
            {"review_item_id": "L3:README.md:install", "layer": "L3", "status": "passed"},
            {"review_item_id": "L4b:README.md:install", "layer": "L4b", "status": "passed"},
            {"review_item_id": "L5:README.md", "layer": "L5", "status": "passed"},
        ],
        "rejected": False,
        "rejection_reason": "",
    },
    "mechanical_report": {
        "total_checks": 3,
        "layers": [
            {"layer": "L0", "name": "Structure", "verdict": "passed", "checks": []},
            {"layer": "L1", "name": "Agents", "verdict": "passed", "checks": []},
            {"layer": "L4", "name": "Cross-lang", "verdict": "passed", "checks": [
                {"layer": "L4", "claim_type": "l4a_mechanical", "status": "passed",
                 "claim_text": "all technical blocks tagged", "detail": ""}]},
            {"layer": "L3", "name": "Semantic", "verdict": "passed", "checks": [
                {"layer": "L3", "claim_type": "l3", "status": "passed", "review_item_id": "L3:README.md:install", "detail": ""}]},
            {"layer": "L5", "name": "Audit", "verdict": "passed", "checks": [
                {"layer": "L5", "claim_type": "l5", "status": "passed", "review_item_id": "L5:README.md", "detail": ""}]},
        ],
    },
    "quality_gate": {
        "verdict": "passed",
        "ci_exit_code": 0,
        "semantic_complete": True,
        "pending_llm_layers": [],
        "mechanical_passed": True,
    },
    "docs": {
        "README.md": (
            "# app\n\n"
            "Dev tooling requires pytest and ruff (per `pyproject.toml`).\n\n"
            "No installation method is documented in the repository; the exact "
            "install command is UNKNOWN and should be inspected further.\n"
        ),
    },
}
