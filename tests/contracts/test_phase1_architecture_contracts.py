"""Architecture Contract Tests for Phase 1 Refactor.

Invariants enforced:
1. Python plane has NO tier classification (Tier S/M/L, tier_override) or scheduling heuristics.
2. Python census emits raw facts only (no prescriptive agent/round recommendations).
3. Skill and Task specifications contain no hardcoded tier routing.
4. Python code does NOT spawn agents or make LLM calls.
5. ReBattle and Scout perspectives are open-ended strings.
6. Scanner/tool failures degrade gracefully with warning flags instead of halting.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from typer.testing import CliRunner

from makewiki_skills.cli import app
from makewiki_skills.config import AgentConfig, iter_config_models

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src" / "makewiki_skills"
SKILL_ROOT = PROJECT_ROOT

runner = CliRunner()


def test_no_tier_classification_in_python_src() -> None:
    """Python codebase must not contain Tier S/M/L logic or tier_override."""
    banned_patterns = [
        re.compile(r"\bTier\s+[SML]\b", re.IGNORECASE),
        re.compile(r"\btier_override\b"),
        re.compile(r"\bestimate_scan_time\b"),
        re.compile(r"\bScanTimeEstimate\b"),
    ]

    violations: list[str] = []
    for py_file in SRC_ROOT.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        for pat in banned_patterns:
            matches = pat.findall(text)
            if matches:
                violations.append(f"{py_file.relative_to(PROJECT_ROOT)}: found {matches}")

    assert not violations, "Found prohibited tier logic in Python src:\n" + "\n".join(violations)


def test_no_tier_fields_in_config_models() -> None:
    """Config models must not expose tier_override or tier fields."""
    for model in iter_config_models():
        assert "tier_override" not in model.model_fields, (
            f"{model.__name__} must not contain tier_override"
        )
        assert "tier" not in model.model_fields, (
            f"{model.__name__} must not contain tier"
        )

    assert "max_subagents" in AgentConfig.model_fields
    assert "max_parallelism" in AgentConfig.model_fields
    assert "max_audit_rounds" in AgentConfig.model_fields
    assert "safety_max_rounds" in AgentConfig.model_fields


def test_no_tier_orchestration_in_skill_and_task_docs() -> None:
    """Authoritative Skill and Task markdown files must not contain Tier S/M/L routing."""
    docs_to_check = [
        PROJECT_ROOT / "SKILL.md",
        *(PROJECT_ROOT / "tasks").glob("*.md"),
        *(PROJECT_ROOT / "subskills").rglob("SKILL.md"),
    ]

    tier_table_pat = re.compile(r"\|\s*\*\*Tier\s+[SML]\*\*", re.IGNORECASE)
    tier_override_pat = re.compile(r"\btier_override\b")

    violations: list[str] = []
    for doc in docs_to_check:
        if not doc.is_file():
            continue
        text = doc.read_text(encoding="utf-8")
        if tier_table_pat.search(text):
            violations.append(f"{doc.relative_to(PROJECT_ROOT)}: contains hardcoded Tier table")
        if tier_override_pat.search(text):
            violations.append(f"{doc.relative_to(PROJECT_ROOT)}: contains tier_override reference")

    assert not violations, "Found prohibited tier orchestration in docs:\n" + "\n".join(violations)


def test_census_cli_emits_raw_facts_only(tmp_path: Path) -> None:
    """Census CLI emits raw facts and forbids prescriptive scheduling recommendations."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname='test-pkg'\n", encoding="utf-8")
    (tmp_path / "main.py").write_text("print('hello')\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_main.py").write_text("def test_ok(): pass\n", encoding="utf-8")

    result = runner.invoke(app, ["census", str(tmp_path), "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)

    # Required factual keys
    assert "source_files" in data
    assert "languages" in data
    assert "manifests" in data
    assert "entrypoints" in data
    assert "configs" in data
    assert "tests" in data
    assert "monorepo_shape" in data
    assert "detected_ecosystems" in data
    assert "tool_failures_and_skips" in data

    # Strictly forbidden prescriptive keys
    banned_keys = {
        "tier",
        "recommended_subagents",
        "rebattle_rounds",
        "strategy",
        "subagent_budget",
        "scan_mode",
        "recommended_rounds",
    }
    assert not (banned_keys & set(data.keys())), f"Census emitted banned keys: {banned_keys & set(data.keys())}"


def test_rebattle_arena_does_not_enforce_fixed_rounds(tmp_path: Path) -> None:
    """rebattle-diff CLI works with 1, 2, 3 or more claim files dynamically without fixed round constraints."""
    claim_set_1 = {
        "agent_id": "debater_1",
        "perspective": "ast_truth",
        "claims": [
            {
                "claim_id": "c-1",
                "agent_id": "debater_1",
                "perspective": "ast_truth",
                "semantic_key": "cli.serve.port",
                "assertion": "Default port is 8080",
                "value": "8080",
            }
        ],
    }
    claim_set_2 = {
        "agent_id": "debater_2",
        "perspective": "recovery_scout",
        "claims": [
            {
                "claim_id": "c-2",
                "agent_id": "debater_2",
                "perspective": "recovery_scout",
                "semantic_key": "cli.serve.port",
                "assertion": "Default port is 9090",
                "value": "9090",
            }
        ],
    }

    f1 = tmp_path / "claims1.json"
    f2 = tmp_path / "claims2.json"
    f1.write_text(json.dumps(claim_set_1), encoding="utf-8")
    f2.write_text(json.dumps(claim_set_2), encoding="utf-8")

    result = runner.invoke(app, ["rebattle-diff", str(f1), str(f2)])
    assert result.exit_code == 0
    assert "cli.serve.port" in result.stdout


def test_scout_perspectives_are_open_ended_strings() -> None:
    """Scout perspectives in AgentClaim model must be open-ended strings (supporting dynamic synthesis)."""
    from makewiki_skills.model.rebattle import AgentClaim

    claim = AgentClaim(
        claim_id="c-123",
        agent_id="scout_dynamic_1",
        perspective="recovery_scout_custom_domain",
        semantic_key="test.key",
        assertion="Test assertion",
    )
    assert claim.perspective == "recovery_scout_custom_domain"


def test_python_plane_has_no_agent_spawning_or_llm_dispatch() -> None:
    """Python codebase must not attempt to spawn subagents, invoke LLMs, or schedule workflows."""
    banned_orchestration_patterns = [
        re.compile(r"\bopenai\b", re.IGNORECASE),
        re.compile(r"\banthropic\b", re.IGNORECASE),
        re.compile(r"\bspawn_subagent\b", re.IGNORECASE),
        re.compile(r"\bdispatch_agent\b", re.IGNORECASE),
    ]

    violations: list[str] = []
    for py_file in SRC_ROOT.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        for pat in banned_orchestration_patterns:
            matches = pat.findall(text)
            if matches:
                violations.append(f"{py_file.relative_to(PROJECT_ROOT)}: found {matches}")

    assert not violations, "Found prohibited orchestration or LLM client calls in Python src:\n" + "\n".join(violations)


def test_degraded_mechanical_status_on_scanner_failures(tmp_path: Path) -> None:
    """Scanner / census records tool warnings gracefully on unparseable files without crashing."""
    broken_py = tmp_path / "broken.py"
    broken_py.write_text("def broken_syntax(:\n", encoding="utf-8")

    result = runner.invoke(app, ["census", str(tmp_path), "--format", "json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["source_files"] >= 1
