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


# ---------------------------------------------------------------------------
# hidden-entrypoint: alias/mirror of hidden-entrypoints
# ---------------------------------------------------------------------------
HIDDEN_ENTRYPOINT = dict(HIDDEN_ENTRYPOINTS)
HIDDEN_ENTRYPOINT["trap"] = "hidden-entrypoint"
HIDDEN_ENTRYPOINT["run_id"] = "fixture-hidden-entrypoint"


# ---------------------------------------------------------------------------
# nested-monorepo: multi-tier workspace with distinct package responsibilities
# ---------------------------------------------------------------------------
NESTED_MONOREPO = {
    "trap": "nested-monorepo",
    "run_id": "fixture-nested-monorepo",
    "evidence": {
        "facts": [
            {"id": "core_pkg", "semantic_key": "monorepo.package.core", "value": "packages/core", "source": "packages/core/pyproject.toml"},
            {"id": "cli_pkg", "semantic_key": "monorepo.package.cli", "value": "packages/cli", "source": "packages/cli/pyproject.toml"},
            {"id": "web_pkg", "semantic_key": "monorepo.package.web", "value": "apps/web", "source": "apps/web/package.json"},
        ],
        "detected_packages": ["packages/core", "packages/cli", "apps/web"],
    },
    "agent_claims": {
        "sets": [
            {
                "agent_id": "agent_structure",
                "perspective": "structure",
                "claims": [
                    {"agent_id": "agent_structure", "claim_type": "package", "semantic_key": "monorepo.package.core",
                     "assertion": "packages/core is shared base", "value": "packages/core", "confidence": "high", "evidence_refs": ["packages/core/pyproject.toml"]},
                    {"agent_id": "agent_structure", "claim_type": "package", "semantic_key": "monorepo.package.cli",
                     "assertion": "packages/cli is cli binary", "value": "packages/cli", "confidence": "high", "evidence_refs": ["packages/cli/pyproject.toml"]},
                    {"agent_id": "agent_structure", "claim_type": "package", "semantic_key": "monorepo.package.web",
                     "assertion": "apps/web is web frontend", "value": "apps/web", "confidence": "high", "evidence_refs": ["apps/web/package.json"]},
                ],
            }
        ]
    },
    "rebattle": {"discrepancies": []},
    "adjudications": {
        "rulings": [
            {"topic": "monorepo.package.core", "ruling": "accepted", "final_assertion": "packages/core", "verified_via_codebase": True, "evidence_refs": ["packages/core/pyproject.toml"]},
            {"topic": "monorepo.package.cli", "ruling": "accepted", "final_assertion": "packages/cli", "verified_via_codebase": True, "evidence_refs": ["packages/cli/pyproject.toml"]},
            {"topic": "monorepo.package.web", "ruling": "accepted", "final_assertion": "apps/web", "verified_via_codebase": True, "evidence_refs": ["apps/web/package.json"]},
        ]
    },
    "semantic_model": {
        "dotenv": [],
        "user_tasks": [],
        "troubleshooting": [],
        "provenance": {"packages": "llm"},
        "claims": [
            {"semantic_key": "monorepo.package.core", "value": "packages/core", "claim_type": "package"},
            {"semantic_key": "monorepo.package.cli", "value": "packages/cli", "claim_type": "package"},
            {"semantic_key": "monorepo.package.web", "value": "apps/web", "claim_type": "package"},
        ],
    },
    "semantic_audit": {
        "auditor": "fake_llm_auditor",
        "documents_digest": "fixture",
        "verdicts": [
            {"review_item_id": "L3:README.md:monorepo", "layer": "L3", "status": "passed"},
            {"review_item_id": "L4b:README.md:packages", "layer": "L4b", "status": "passed"},
            {"review_item_id": "L5:README.md", "layer": "L5", "status": "passed"},
        ],
        "rejected": False,
        "rejection_reason": "",
    },
    "mechanical_report": {
        "total_checks": 4,
        "layers": [
            {"layer": "L0", "name": "Structure", "verdict": "passed", "checks": []},
            {"layer": "L1", "name": "Agents", "verdict": "passed", "checks": []},
            {"layer": "L2", "name": "Interface", "verdict": "passed", "checks": []},
            {"layer": "L4", "name": "Cross-lang", "verdict": "passed", "checks": [
                {"layer": "L4", "claim_type": "l4a_mechanical", "status": "passed", "claim_text": "stable block parity", "detail": ""},
            ]},
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
        "README.md": "# Monorepo\n\nPackages: packages/core, packages/cli, apps/web.\n",
    },
}


# ---------------------------------------------------------------------------
# config-override: DATABASE_URL env var overrides config.yaml
# ---------------------------------------------------------------------------
CONFIG_OVERRIDE = {
    "trap": "config-override",
    "run_id": "fixture-config-override",
    "evidence": {
        "facts": [
            {"id": "db_env", "semantic_key": "config.db.env_override", "value": "DATABASE_URL", "source": "app.py"},
            {"id": "db_yaml", "semantic_key": "config.db.default_host", "value": "localhost", "source": "config.yaml"},
        ],
        "detected_packages": [],
    },
    "agent_claims": {
        "sets": [
            {
                "agent_id": "agent_config",
                "perspective": "config",
                "claims": [
                    {"agent_id": "agent_config", "claim_type": "config", "semantic_key": "config.db.env_override",
                     "assertion": "DATABASE_URL overrides config.yaml", "value": "DATABASE_URL", "confidence": "high", "evidence_refs": ["app.py"]},
                    {"agent_id": "agent_config", "claim_type": "config", "semantic_key": "config.db.default_host",
                     "assertion": "default is localhost", "value": "localhost", "confidence": "high", "evidence_refs": ["config.yaml"]},
                ],
            }
        ]
    },
    "rebattle": {"discrepancies": []},
    "adjudications": {
        "rulings": [
            {"topic": "config.db.env_override", "ruling": "accepted", "final_assertion": "DATABASE_URL", "verified_via_codebase": True, "evidence_refs": ["app.py"]},
            {"topic": "config.db.default_host", "ruling": "accepted", "final_assertion": "localhost", "verified_via_codebase": True, "evidence_refs": ["config.yaml"]},
        ]
    },
    "semantic_model": {
        "dotenv": [],
        "user_tasks": [],
        "troubleshooting": [],
        "provenance": {"config": "llm"},
        "claims": [
            {"semantic_key": "config.db.env_override", "value": "DATABASE_URL", "claim_type": "config"},
            {"semantic_key": "config.db.default_host", "value": "localhost", "claim_type": "config"},
        ],
    },
    "semantic_audit": {
        "auditor": "fake_llm_auditor",
        "documents_digest": "fixture",
        "verdicts": [
            {"review_item_id": "L3:README.md:config", "layer": "L3", "status": "passed"},
            {"review_item_id": "L4b:README.md:config", "layer": "L4b", "status": "passed"},
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
            {"layer": "L2", "name": "Interface", "verdict": "passed", "checks": []},
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
        "README.md": "# Config\n\nDATABASE_URL environment variable overrides config.yaml host (default localhost).\n",
    },
}


# ---------------------------------------------------------------------------
# tool-failure-recovery: AST parser recovery on syntax error
# ---------------------------------------------------------------------------
TOOL_FAILURE_RECOVERY = {
    "trap": "tool-failure-recovery",
    "run_id": "fixture-tool-failure-recovery",
    "evidence": {
        "facts": [
            {"id": "serve_entry", "semantic_key": "app.entrypoint.serve", "value": "start_server", "source": "real_app.py"},
        ],
        "detected_packages": [],
    },
    "agent_claims": {
        "sets": [
            {
                "agent_id": "agent_recovery",
                "perspective": "recovery_scout",
                "claims": [
                    {"agent_id": "agent_recovery", "claim_type": "entrypoint", "semantic_key": "app.entrypoint.serve",
                     "assertion": "start_server in real_app.py", "value": "start_server", "confidence": "high", "evidence_refs": ["real_app.py"]},
                ],
            }
        ]
    },
    "rebattle": {"discrepancies": []},
    "adjudications": {
        "rulings": [
            {"topic": "app.entrypoint.serve", "ruling": "accepted", "final_assertion": "start_server", "verified_via_codebase": True, "evidence_refs": ["real_app.py"]},
        ]
    },
    "semantic_model": {
        "dotenv": [],
        "user_tasks": [],
        "troubleshooting": [],
        "provenance": {"app": "llm"},
        "claims": [
            {"semantic_key": "app.entrypoint.serve", "value": "start_server", "claim_type": "entrypoint"},
        ],
    },
    "semantic_audit": {
        "auditor": "fake_llm_auditor",
        "documents_digest": "fixture",
        "verdicts": [
            {"review_item_id": "L3:README.md:app", "layer": "L3", "status": "passed"},
            {"review_item_id": "L4b:README.md:app", "layer": "L4b", "status": "passed"},
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
            {"layer": "L2", "name": "Interface", "verdict": "passed", "checks": []},
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
        "README.md": "# Tool Failure Recovery\n\nstart_server runs on port 9000 per real_app.py.\n",
    },
}


# ---------------------------------------------------------------------------
# fork-residue: renamed fork cleanly identified
# ---------------------------------------------------------------------------
FORK_RESIDUE = {
    "trap": "fork-residue",
    "run_id": "fixture-fork-residue",
    "evidence": {
        "facts": [
            {"id": "pkg_name", "semantic_key": "package.name", "value": "modern-lib", "source": "pyproject.toml"},
        ],
        "detected_packages": [],
    },
    "agent_claims": {
        "sets": [
            {
                "agent_id": "agent_fork",
                "perspective": "fork_provenance",
                "claims": [
                    {"agent_id": "agent_fork", "claim_type": "identity", "semantic_key": "package.name",
                     "assertion": "package name is modern-lib", "value": "modern-lib", "confidence": "high", "evidence_refs": ["pyproject.toml"]},
                ],
            }
        ]
    },
    "rebattle": {"discrepancies": []},
    "adjudications": {
        "rulings": [
            {"topic": "package.name", "ruling": "accepted", "final_assertion": "modern-lib", "verified_via_codebase": True, "evidence_refs": ["pyproject.toml"]},
        ]
    },
    "semantic_model": {
        "dotenv": [],
        "user_tasks": [],
        "troubleshooting": [],
        "provenance": {"package": "llm"},
        "claims": [
            {"semantic_key": "package.name", "value": "modern-lib", "claim_type": "identity"},
        ],
    },
    "semantic_audit": {
        "auditor": "fake_llm_auditor",
        "documents_digest": "fixture",
        "verdicts": [
            {"review_item_id": "L3:README.md:identity", "layer": "L3", "status": "passed"},
            {"review_item_id": "L4b:README.md:identity", "layer": "L4b", "status": "passed"},
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
            {"layer": "L2", "name": "Interface", "verdict": "passed", "checks": []},
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
        "README.md": "# modern-lib\n\nInstall via `pip install modern-lib`.\n",
    },
}


# ---------------------------------------------------------------------------
# stale-example: API signature update (tls_mode vs secure)
# ---------------------------------------------------------------------------
STALE_EXAMPLE = {
    "trap": "stale-example",
    "run_id": "fixture-stale-example",
    "evidence": {
        "facts": [
            {"id": "connect_api", "semantic_key": "api.connect.param.tls_mode", "value": "tls_mode", "source": "src/client.py"},
        ],
        "detected_packages": [],
    },
    "agent_claims": {
        "sets": [
            {
                "agent_id": "agent_api",
                "perspective": "ast_truth",
                "claims": [
                    {"agent_id": "agent_api", "claim_type": "api", "semantic_key": "api.connect.param.tls_mode",
                     "assertion": "client.connect requires tls_mode", "value": "tls_mode", "confidence": "high", "evidence_refs": ["src/client.py"]},
                ],
            }
        ]
    },
    "rebattle": {"discrepancies": []},
    "adjudications": {
        "rulings": [
            {"topic": "api.connect.param.tls_mode", "ruling": "accepted", "final_assertion": "tls_mode", "verified_via_codebase": True, "evidence_refs": ["src/client.py"]},
        ]
    },
    "semantic_model": {
        "dotenv": [],
        "user_tasks": [],
        "troubleshooting": [],
        "provenance": {"api": "llm"},
        "claims": [
            {"semantic_key": "api.connect.param.tls_mode", "value": "tls_mode", "claim_type": "api"},
        ],
    },
    "semantic_audit": {
        "auditor": "fake_llm_auditor",
        "documents_digest": "fixture",
        "verdicts": [
            {"review_item_id": "L3:README.md:api", "layer": "L3", "status": "passed"},
            {"review_item_id": "L4b:README.md:api", "layer": "L4b", "status": "passed"},
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
            {"layer": "L2", "name": "Interface", "verdict": "passed", "checks": []},
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
        "README.md": "# Client\n\n```python\nclient.connect(tls_mode='strict')\n```\n",
    },
}


# ---------------------------------------------------------------------------
# unsupported-claim: unprovable feature properly hedged or dropped
# ---------------------------------------------------------------------------
UNSUPPORTED_CLAIM = {
    "trap": "unsupported-claim",
    "run_id": "fixture-unsupported-claim",
    "evidence": {
        "facts": [
            {"id": "real_fn", "semantic_key": "feature.basic", "value": "ping", "source": "scratch/core.py"},
        ],
        "detected_packages": [],
    },
    "agent_claims": {
        "sets": [
            {
                "agent_id": "agent_audit",
                "perspective": "epistemic_audit",
                "claims": [
                    {"agent_id": "agent_audit", "claim_type": "feature", "semantic_key": "feature.basic",
                     "assertion": "ping helper exists in scratch/core.py", "value": "ping", "confidence": "high", "evidence_refs": ["scratch/core.py"]},
                ],
            }
        ]
    },
    "rebattle": {"discrepancies": []},
    "adjudications": {
        "rulings": [
            {"topic": "feature.basic", "ruling": "accepted", "final_assertion": "ping", "verified_via_codebase": True, "evidence_refs": ["scratch/core.py"]},
        ]
    },
    "semantic_model": {
        "dotenv": [],
        "user_tasks": [],
        "troubleshooting": [],
        "provenance": {"feature": "llm"},
        "claims": [
            {"semantic_key": "feature.basic", "value": "ping", "claim_type": "feature"},
        ],
    },
    "semantic_audit": {
        "auditor": "fake_llm_auditor",
        "documents_digest": "fixture",
        "verdicts": [
            {"review_item_id": "L3:README.md:feature", "layer": "L3", "status": "passed"},
            {"review_item_id": "L4b:README.md:feature", "layer": "L4b", "status": "passed"},
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
            {"layer": "L2", "name": "Interface", "verdict": "passed", "checks": []},
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
        "README.md": "# App\n\nProvides basic_feature.\n",
    },
}


# ---------------------------------------------------------------------------
# multilingual-reorder: identical block IDs across reordered sections
# ---------------------------------------------------------------------------
MULTILINGUAL_REORDER = {
    "trap": "multilingual-reorder",
    "run_id": "fixture-multilingual-reorder",
    "evidence": {
        "facts": [
            {"id": "serve_cmd", "semantic_key": "cli.command.serve", "value": "service serve", "source": "src/service.py"},
        ],
        "detected_packages": [],
    },
    "agent_claims": {
        "sets": [
            {
                "agent_id": "agent_writer",
                "perspective": "multilingual",
                "claims": [
                    {"agent_id": "agent_writer", "claim_type": "command", "semantic_key": "cli.command.serve",
                     "assertion": "service serve starts the server", "value": "service serve", "confidence": "high", "evidence_refs": ["src/service.py"]},
                ],
            }
        ]
    },
    "rebattle": {"discrepancies": []},
    "adjudications": {
        "rulings": [
            {"topic": "cli.command.serve", "ruling": "accepted", "final_assertion": "service serve", "verified_via_codebase": True, "evidence_refs": ["src/service.py"]},
        ]
    },
    "semantic_model": {
        "dotenv": [],
        "user_tasks": [],
        "troubleshooting": [],
        "provenance": {"cli": "llm"},
        "claims": [
            {"semantic_key": "cli.command.serve", "value": "service serve", "claim_type": "command"},
        ],
    },
    "semantic_audit": {
        "auditor": "fake_llm_auditor",
        "documents_digest": "fixture",
        "verdicts": [
            {"review_item_id": "L3:README.md:serve", "layer": "L3", "status": "passed"},
            {"review_item_id": "L4b:README.md:serve", "layer": "L4b", "status": "passed"},
            {"review_item_id": "L5:README.md", "layer": "L5", "status": "passed"},
        ],
        "rejected": False,
        "rejection_reason": "",
    },
    "mechanical_report": {
        "total_checks": 4,
        "layers": [
            {"layer": "L0", "name": "Structure", "verdict": "passed", "checks": []},
            {"layer": "L1", "name": "Agents", "verdict": "passed", "checks": []},
            {"layer": "L2", "name": "Interface", "verdict": "passed", "checks": []},
            {"layer": "L4", "name": "Cross-lang", "verdict": "passed", "checks": [
                {"layer": "L4", "claim_type": "l4a_mechanical", "status": "passed", "claim_text": "stable block parity", "detail": ""},
            ]},
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
        "README.md": "# Service\n\n```bash\n[[id:service_serve]]\nservice serve\n```\n",
    },
}


# ---------------------------------------------------------------------------
# incomplete-scan: dynamic deepening discovers secondary plugins
# ---------------------------------------------------------------------------
INCOMPLETE_SCAN = {
    "trap": "incomplete-scan",
    "run_id": "fixture-incomplete-scan",
    "evidence": {
        "facts": [
            {"id": "auth_plug", "semantic_key": "plugin.auth.custom", "value": "CustomAuthPlugin", "source": "src/plugins/custom_auth.py"},
        ],
        "detected_packages": [],
    },
    "agent_claims": {
        "sets": [
            {
                "agent_id": "agent_plugins",
                "perspective": "plugins",
                "claims": [
                    {"agent_id": "agent_plugins", "claim_type": "plugin", "semantic_key": "plugin.auth.custom",
                     "assertion": "CustomAuthPlugin provides custom authentication", "value": "CustomAuthPlugin", "confidence": "high", "evidence_refs": ["src/plugins/custom_auth.py"]},
                ],
            }
        ]
    },
    "rebattle": {"discrepancies": []},
    "adjudications": {
        "rulings": [
            {"topic": "plugin.auth.custom", "ruling": "accepted", "final_assertion": "CustomAuthPlugin", "verified_via_codebase": True, "evidence_refs": ["src/plugins/custom_auth.py"]},
        ]
    },
    "semantic_model": {
        "dotenv": [],
        "user_tasks": [],
        "troubleshooting": [],
        "provenance": {"plugins": "llm"},
        "claims": [
            {"semantic_key": "plugin.auth.custom", "value": "CustomAuthPlugin", "claim_type": "plugin"},
        ],
    },
    "semantic_audit": {
        "auditor": "fake_llm_auditor",
        "documents_digest": "fixture",
        "verdicts": [
            {"review_item_id": "L3:README.md:plugins", "layer": "L3", "status": "passed"},
            {"review_item_id": "L4b:README.md:plugins", "layer": "L4b", "status": "passed"},
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
            {"layer": "L2", "name": "Interface", "verdict": "passed", "checks": []},
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
        "README.md": "# App Plugins\n\nCustomAuthPlugin in src/plugins/custom_auth.py.\n",
    },
}

