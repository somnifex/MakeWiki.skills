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


# ---------------------------------------------------------------------------
# hidden-entrypoints: config lives in dot-directories (.env, .config/app.yml)
# and a CI/deploy entrypoint (.github/workflows). Correct handoff surfaces them
# rather than ignoring hidden paths; the required .env keys, the nested
# .config/app.yml settings, and the CI entrypoint are all asserted.
# ---------------------------------------------------------------------------

HIDDEN_ENTRYPOINTS = {
    "trap": "hidden-entrypoints",
    "run_id": "fixture-hidden-entrypoints",
    "evidence": {
        "facts": [
            {"id": "env_token", "semantic_key": "config.env.required", "value": "API_TOKEN", "source": ".env"},
            {"id": "env_db", "semantic_key": "config.env.required", "value": "DB_URL", "source": ".env"},
            {"id": "app_yml", "semantic_key": "config.app.settings", "value": "telemetry,workers", "source": ".config/app.yml"},
            {"id": "ci_wf", "semantic_key": "ci.entrypoint", "value": "ci workflow", "source": ".github/workflows/ci.yml"},
        ],
        "detected_packages": [],
    },
    "agent_claims": {
        "sets": [
            {
                "agent_id": "agent_green",
                "perspective": "code_implementation",
                "claims": [
                    {"agent_id": "agent_green", "claim_type": "config", "semantic_key": "config.env.required",
                     "assertion": ".env requires API_TOKEN, DB_URL, LOG_LEVEL", "value": "API_TOKEN,DB_URL,LOG_LEVEL",
                     "confidence": "high", "evidence_refs": [".env"]},
                    {"agent_id": "agent_green", "claim_type": "config", "semantic_key": "config.app.settings",
                     "assertion": ".config/app.yml declares telemetry and workers", "value": "telemetry,workers",
                     "confidence": "high", "evidence_refs": [".config/app.yml"]},
                    {"agent_id": "agent_green", "claim_type": "command", "semantic_key": "ci.entrypoint",
                     "assertion": "CI workflow exists at .github/workflows/ci.yml", "value": "ci workflow",
                     "confidence": "high", "evidence_refs": [".github/workflows/ci.yml"]},
                ],
            },
            {
                "agent_id": "agent_red",
                "perspective": "user_experience",
                "claims": [
                    {"agent_id": "agent_red", "claim_type": "config", "semantic_key": "config.env.required",
                     "assertion": "the service may have no configuration", "value": "",
                     "confidence": "low"},
                ],
            },
        ]
    },
    "rebattle": {
        "discrepancies": [
            {"topic": "config.env.required", "participants": ["agent_red", "agent_green"],
             "source_values": {"agent_red": "", "agent_green": "API_TOKEN,DB_URL,LOG_LEVEL"}},
            {"topic": "ci.entrypoint", "participants": ["agent_red", "agent_green"],
             "source_values": {"agent_red": "", "agent_green": "ci workflow"}},
        ]
    },
    "adjudications": {
        "rulings": [
            {"topic": "config.env.required", "ruling": "accepted", "final_assertion": "API_TOKEN,DB_URL,LOG_LEVEL",
             "verified_via_codebase": True, "evidence_refs": [".env"],
             "adjudicator_reasoning": ".env + .config/app.yml exist and define required keys; green is correct"},
            {"topic": "ci.entrypoint", "ruling": "accepted", "final_assertion": "ci workflow",
             "verified_via_codebase": True, "evidence_refs": [".github/workflows/ci.yml"],
             "adjudicator_reasoning": "the CI workflow entrypoint must be surfaced, not ignored"},
        ]
    },
    "semantic_model": {
        "dotenv": ["API_TOKEN", "DB_URL", "LOG_LEVEL"],
        "user_tasks": [],
        "troubleshooting": [],
        "provenance": {"config": "llm"},
        "claims": [
            {"semantic_key": "config.env.required", "value": "API_TOKEN,DB_URL,LOG_LEVEL", "claim_type": "config"},
            {"semantic_key": "config.app.settings", "value": "telemetry,workers", "claim_type": "config"},
            {"semantic_key": "ci.entrypoint", "value": "ci workflow", "claim_type": "command"},
        ],
    },
    "semantic_audit": {
        "auditor": "fake_llm_auditor",
        "documents_digest": "fixture",
        "verdicts": [
            {"review_item_id": "L3:README.md:config", "layer": "L3", "status": "passed"},
            {"review_item_id": "L3:README.md:entrypoint", "layer": "L3", "status": "passed"},
            {"review_item_id": "L4b:README.md:config", "layer": "L4b", "status": "passed"},
            {"review_item_id": "L5:README.md", "layer": "L5", "status": "passed"},
        ],
        "rejected": False,
        "rejection_reason": "",
    },
    "mechanical_report": {
        "total_checks": 6,
        "layers": [
            {"layer": "L0", "name": "Structure", "verdict": "passed", "checks": []},
            {"layer": "L1", "name": "Agents", "verdict": "passed", "checks": []},
            {"layer": "L2", "name": "Interface", "verdict": "passed", "checks": []},
            {"layer": "L4", "name": "Cross-lang", "verdict": "passed", "checks": [
                {"layer": "L4", "claim_type": "l4a_mechanical", "status": "passed",
                 "claim_text": "all technical blocks tagged", "detail": ""},
                {"layer": "L4", "claim_type": "l4b_semantic", "status": "passed",
                 "review_item_id": "L4b:README.md:config", "detail": ""},
            ]},
            {"layer": "L3", "name": "Semantic", "verdict": "passed", "checks": [
                {"layer": "L3", "claim_type": "l3", "status": "passed", "review_item_id": "L3:README.md:config", "detail": ""},
                {"layer": "L3", "claim_type": "l3", "status": "passed", "review_item_id": "L3:README.md:entrypoint", "detail": ""}]},
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
            "# service\n\n"
            "Reads configuration from `.env` (required keys: API_TOKEN, DB_URL, "
            "LOG_LEVEL) plus `.config/app.yml` (features.telemetry, "
            "server.workers).\n\n"
            "CI runs via `.github/workflows/ci.yml`.\n"
        ),
    },
}


# ---------------------------------------------------------------------------
# indirect-config: a config.yaml is overridden by a composed docker-compose.yml
# env. Correct handoff resolves the FINAL value via the override (port 8080,
# cache true), never asserting the stale base (port 5000, cache false).
# ---------------------------------------------------------------------------

INDIRECT_CONFIG = {
    "trap": "indirect-config",
    "run_id": "fixture-indirect-config",
    "evidence": {
        "facts": [
            {"id": "base_port", "semantic_key": "config.port.base", "value": "5000", "source": "config.yaml"},
            {"id": "compose_port", "semantic_key": "config.port.effective", "value": "8080", "source": "docker-compose.yml"},
            {"id": "compose_cache", "semantic_key": "config.cache.effective", "value": "true", "source": "docker-compose.yml"},
        ],
        "detected_packages": [],
    },
    "agent_claims": {
        "sets": [
            {
                "agent_id": "agent_red",
                "perspective": "user_experience",
                "claims": [
                    {"agent_id": "agent_red", "claim_type": "config", "semantic_key": "config.port.effective",
                     "assertion": "the default port is 5000 from config.yaml", "value": "5000", "confidence": "low"},
                ],
            },
            {
                "agent_id": "agent_green",
                "perspective": "code_implementation",
                "claims": [
                    {"agent_id": "agent_green", "claim_type": "config", "semantic_key": "config.port.effective",
                     "assertion": "docker-compose PORT=8080 overrides config.yaml 5000", "value": "8080",
                     "confidence": "high", "evidence_refs": ["docker-compose.yml"]},
                    {"agent_id": "agent_green", "claim_type": "config", "semantic_key": "config.cache.effective",
                     "assertion": "CACHE_ENABLED=true overrides features.cache=false", "value": "true",
                     "confidence": "high", "evidence_refs": ["docker-compose.yml"]},
                ],
            },
        ]
    },
    "rebattle": {
        "discrepancies": [
            {"topic": "config.port.effective", "participants": ["agent_red", "agent_green"],
             "source_values": {"agent_red": "5000", "agent_green": "8080"}},
            {"topic": "config.cache.effective", "participants": ["agent_red", "agent_green"],
             "source_values": {"agent_red": "false", "agent_green": "true"}},
        ]
    },
    "adjudications": {
        "rulings": [
            {"topic": "config.port.effective", "ruling": "accepted", "final_assertion": "8080",
             "verified_via_codebase": True, "evidence_refs": ["docker-compose.yml"],
             "adjudicator_reasoning": "docker-compose sets PORT=8080 which overrides the base 5000"},
            {"topic": "config.cache.effective", "ruling": "accepted", "final_assertion": "true",
             "verified_via_codebase": True, "evidence_refs": ["docker-compose.yml"],
             "adjudicator_reasoning": "CACHE_ENABLED=true overrides base cache=false"},
        ]
    },
    "semantic_model": {
        "dotenv": [],
        "user_tasks": [],
        "troubleshooting": [],
        "provenance": {"config": "llm"},
        "claims": [
            {"semantic_key": "config.port.effective", "value": "8080", "claim_type": "config"},
            {"semantic_key": "config.cache.effective", "value": "true", "claim_type": "config"},
        ],
    },
    "semantic_audit": {
        "auditor": "fake_llm_auditor",
        "documents_digest": "fixture",
        "verdicts": [
            {"review_item_id": "L3:README.md:port", "layer": "L3", "status": "passed"},
            {"review_item_id": "L3:README.md:cache", "layer": "L3", "status": "passed"},
            {"review_item_id": "L4b:README.md:config", "layer": "L4b", "status": "passed"},
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
                {"layer": "L4", "claim_type": "l4b_semantic", "status": "passed",
                 "review_item_id": "L4b:README.md:config", "detail": ""},
            ]},
            {"layer": "L3", "name": "Semantic", "verdict": "passed", "checks": [
                {"layer": "L3", "claim_type": "l3", "status": "passed", "review_item_id": "L3:README.md:port", "detail": ""},
                {"layer": "L3", "claim_type": "l3", "status": "passed", "review_item_id": "L3:README.md:cache", "detail": ""}]},
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
            "# svc\n\n"
            "The effective HTTP port is **8080** — docker-compose sets "
            "`PORT=8080`, overriding `config.yaml`'s base 5000.\n\n"
            "Caching is **enabled** (`CACHE_ENABLED=true` overrides "
            "`features.cache: false` in `config.yaml`).\n"
        ),
    },
}


# ---------------------------------------------------------------------------
# stale-readme: the README documents a default port (3000) that the real CLI
# parser contradicts (serve --port default 8080). Correct handoff trusts the
# source (8080), surfaces the conflict, and never asserts the stale 3000.
# ---------------------------------------------------------------------------

STALE_README = {
    "trap": "stale-readme",
    "run_id": "fixture-stale-readme",
    "evidence": {
        "facts": [
            {"id": "source_port", "semantic_key": "network.port.default", "value": "8080", "source": "app/echo_cli/main.py"},
            {"id": "readme_port", "semantic_key": "network.port.default", "value": "3000", "source": "README.md"},
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
                     "assertion": "the default port is 3000", "value": "3000", "confidence": "low"},
                ],
            },
            {
                "agent_id": "agent_green",
                "perspective": "code_implementation",
                "claims": [
                    {"agent_id": "agent_green", "claim_type": "config", "semantic_key": "network.port.default",
                     "assertion": "the serve --port default is 8080 per app/echo_cli/main.py", "value": "8080",
                     "confidence": "high", "evidence_refs": ["app/echo_cli/main.py"]},
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
             "verified_via_codebase": True, "evidence_refs": ["app/echo_cli/main.py"],
             "adjudicator_reasoning": "source pins 8080; README 3000 is stale"}
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
            "# echo-cli\n\n"
            "The `serve --port` default is **8080** (per `app/echo_cli/main.py`).\n\n"
            "> The README once claimed 3000; the source pins 8080, which is authoritative.\n"
        ),
    },
}


# ---------------------------------------------------------------------------
# monorepo-discovery: a two-package monorepo where per-package scoping matters.
# Correct handoff surfaces each package's own manifest + entrypoint and never
# misattributes a command across packages.
# ---------------------------------------------------------------------------

MONOREPO_DISCOVERY = {
    "trap": "monorepo-discovery",
    "run_id": "fixture-monorepo-discovery",
    "evidence": {
        "facts": [
            {"id": "svc_a_manifest", "semantic_key": "monorepo.manifests", "value": "svc-a", "source": "packages/svc-a/pyproject.toml"},
            {"id": "lib_b_manifest", "semantic_key": "monorepo.manifests", "value": "lib-b", "source": "packages/lib-b/pyproject.toml"},
            {"id": "svc_a_cli", "semantic_key": "packages.svc_a.cli", "value": "serve", "source": "packages/svc-a/svc_a/main.py"},
        ],
        "detected_packages": ["svc-a", "lib-b"],
    },
    "agent_claims": {
        "sets": [
            {
                "agent_id": "agent_green",
                "perspective": "code_implementation",
                "claims": [
                    {"agent_id": "agent_green", "claim_type": "command", "semantic_key": "packages.svc_a.cli",
                     "assertion": "svc-a exposes serve (--port 9000) scoped to packages/svc-a", "value": "serve",
                     "confidence": "high", "evidence_refs": ["packages/svc-a/svc_a/main.py"]},
                    {"agent_id": "agent_green", "claim_type": "command", "semantic_key": "packages.lib_b.entry",
                     "assertion": "lib-b entrypoint via packages/lib-b/pyproject.toml", "value": "lib-b",
                     "confidence": "high", "evidence_refs": ["packages/lib-b/pyproject.toml"]},
                    {"agent_id": "agent_green", "claim_type": "manifest", "semantic_key": "monorepo.manifests",
                     "assertion": "both packages have their own pyproject.toml", "value": "svc-a,lib-b",
                     "confidence": "high", "evidence_refs": ["packages/svc-a/pyproject.toml"]},
                ],
            },
        ]
    },
    "rebattle": {
        "discrepancies": [
            {"topic": "packages.lib_b.entry", "participants": ["agent_red", "agent_green"],
             "source_values": {"agent_red": "serve (root)", "agent_green": "lib-b (packages/lib-b)"}}
        ]
    },
    "adjudications": {
        "rulings": [
            {"topic": "packages.svc_a.cli", "ruling": "accepted", "final_assertion": "serve",
             "verified_via_codebase": True, "evidence_refs": ["packages/svc-a/svc_a/main.py"],
             "adjudicator_reasoning": "serve lives only in packages/svc-a"},
            {"topic": "packages.lib_b.entry", "ruling": "accepted", "final_assertion": "lib-b",
             "verified_via_codebase": True, "evidence_refs": ["packages/lib-b/pyproject.toml"],
             "adjudicator_reasoning": "lib-b entrypoint belongs to packages/lib-b, not svc-a"},
            {"topic": "monorepo.manifests", "ruling": "accepted", "final_assertion": "svc-a,lib-b",
             "verified_via_codebase": True, "evidence_refs": ["packages/svc-a/pyproject.toml"],
             "adjudicator_reasoning": "nested per-package manifests surfaced"},
        ]
    },
    "semantic_model": {
        "dotenv": [],
        "user_tasks": [],
        "troubleshooting": [],
        "provenance": {"packages": "llm"},
        "claims": [
            {"semantic_key": "packages.svc_a.cli", "value": "serve", "claim_type": "command"},
            {"semantic_key": "packages.lib_b.entry", "value": "lib-b", "claim_type": "command"},
            {"semantic_key": "monorepo.manifests", "value": "svc-a,lib-b", "claim_type": "manifest"},
        ],
    },
    "semantic_audit": {
        "auditor": "fake_llm_auditor",
        "documents_digest": "fixture",
        "verdicts": [
            {"review_item_id": "L3:README.md:packages", "layer": "L3", "status": "passed"},
            {"review_item_id": "L3:README.md:entrypoint", "layer": "L3", "status": "passed"},
            {"review_item_id": "L4b:README.md:packages", "layer": "L4b", "status": "passed"},
            {"review_item_id": "L5:README.md", "layer": "L5", "status": "passed"},
        ],
        "rejected": False,
        "rejection_reason": "",
    },
    "mechanical_report": {
        "total_checks": 6,
        "layers": [
            {"layer": "L0", "name": "Structure", "verdict": "passed", "checks": []},
            {"layer": "L1", "name": "Agents", "verdict": "passed", "checks": []},
            {"layer": "L2", "name": "Interface", "verdict": "passed", "checks": []},
            {"layer": "L4", "name": "Cross-lang", "verdict": "passed", "checks": [
                {"layer": "L4", "claim_type": "l4a_mechanical", "status": "passed",
                 "claim_text": "all technical blocks tagged", "detail": ""},
                {"layer": "L4", "claim_type": "l4b_semantic", "status": "passed",
                 "review_item_id": "L4b:README.md:packages", "detail": ""},
            ]},
            {"layer": "L3", "name": "Semantic", "verdict": "passed", "checks": [
                {"layer": "L3", "claim_type": "l3", "status": "passed", "review_item_id": "L3:README.md:packages", "detail": ""},
                {"layer": "L3", "claim_type": "l3", "status": "passed", "review_item_id": "L3:README.md:entrypoint", "detail": ""}]},
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
            "# platform\n\n"
            "- `packages/svc-a` exposes the `serve` command (default port 9000).\n"
            "- `packages/lib-b` exposes the `lib-b` entrypoint.\n"
            "Each package ships its own `pyproject.toml`.\n"
        ),
    },
}
