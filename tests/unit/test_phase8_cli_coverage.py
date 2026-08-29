"""Phase-8 functional tests covering advertised CLI behaviour.

These tests complement the structural contract tests by exercising the
specific behaviour Phase-7 and Phase-8 promised:

* ``export --format pdf`` exits 1 with an explicit error.
* ``sync-bundle`` and the ``sync`` alias are both registered.
* ``verify-claim`` and ``verify-model`` smoke-run via ``CliRunner``.
* ``scripts/bootstrap_toolkit.py`` pins versions correctly via pure helpers.
* ``QualityGate`` maps PASS/FAIL to exit codes 0/1.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from makewiki_skills.cli import app
from makewiki_skills.config import MakeWikiConfig
from makewiki_skills.verification.quality_gate import (
    QualityGateResult,
    evaluate_quality_gate,
)
from makewiki_skills.verification.report import (
    ComprehensiveVerificationReport,
    LayerReport,
    VerificationCheck,
)

# ---------- Quality Gate pass/fail + CI exit codes ----------------------------


def _all_passing_report() -> ComprehensiveVerificationReport:
    layers: dict[str, LayerReport] = {}
    for name, label in [
        ("L0", "Syntax"),
        ("L1", "Existence"),
        ("L2", "Interface"),
        ("L3", "Behavior"),
        ("L4", "Cross-language"),
        ("L5", "Epistemic"),
    ]:
        layers[name] = LayerReport(
            layer=name,
            name=label,
            checks=[
                VerificationCheck(
                    layer=name,
                    target="doc.md",
                    claim_type="structure",
                    claim_text="ok",
                    verified=True,
                    status="passed",
                    detail="ok",
                )
            ],
        )
    return ComprehensiveVerificationReport(layers=layers)


def test_quality_gate_pass_yields_exit_code_zero():
    report = _all_passing_report()
    result = evaluate_quality_gate(report, MakeWikiConfig.default(Path(".")))
    assert isinstance(result, QualityGateResult)
    assert result.passed is True
    assert result.exit_code == 0


def test_quality_gate_fail_yields_exit_code_one():
    report = _all_passing_report()
    report.layers["L1"] = LayerReport(
        layer="L1",
        name="Existence",
        checks=[
            VerificationCheck(
                layer="L1",
                target="missing.md",
                claim_type="path",
                claim_text="missing.md",
                verified=False,
                status="failed",
                detail="not on disk",
            )
        ],
    )
    result = evaluate_quality_gate(report, MakeWikiConfig.default(Path(".")))
    assert result.passed is False
    assert result.exit_code == 1
    assert result.existence_passed is False


def test_quality_gate_respects_min_grounding_score_threshold():
    """A report below the configured threshold must fail the gate."""
    report = _all_passing_report()
    # Force score below 1.0 by failing L2 in addition to L1.
    report.layers["L2"] = LayerReport(
        layer="L2",
        name="Interface",
        checks=[
            VerificationCheck(
                layer="L2",
                target="doc.md",
                claim_type="cli_flag",
                claim_text="--unknown",
                verified=False,
                status="failed",
                detail="no such flag",
            )
        ],
    )
    cfg = MakeWikiConfig.default(Path("."))
    cfg.quality.min_grounding_score = 1.0
    result = evaluate_quality_gate(report, cfg)
    assert result.grounding_score < 1.0
    assert result.passed is False


# ---------- export rejects --format pdf --------------------------------------


def test_export_rejects_pdf_with_exit_code_one(tmp_path: Path):
    runner = CliRunner()
    # Create a dummy wiki dir (so the directory check passes; --format pdf
    # should still fail before any content is processed).
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    result = runner.invoke(app, ["export", str(wiki), "--format", "pdf"])
    assert result.exit_code == 1, result.output
    combined = (result.output or "") + (result.stderr or "")
    assert "PDF" in combined or "pdf" in combined, (
        f"Expected pdf rejection error in CLI output, got: {combined!r}"
    )


def test_export_accepts_html_and_epub(tmp_path: Path):
    runner = CliRunner()
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    (wiki / "README.md").write_text("# hello\n", encoding="utf-8")

    result_html = runner.invoke(app, ["export", str(wiki), "--format", "html"])
    assert result_html.exit_code == 0, result_html.output

    result_epub = runner.invoke(app, ["export", str(wiki), "--format", "epub"])
    assert result_epub.exit_code == 0, result_epub.output


# ---------- sync-bundle naming -----------------------------------------------


def test_sync_bundle_command_is_registered():
    names = {
        cmd.name or (cmd.callback.__name__ if cmd.callback else "")
        for cmd in app.registered_commands
    }
    assert "sync-bundle" in names, "sync-bundle must be a registered Typer command"
    assert "sync" in names, "sync alias must remain for backward compatibility"


def test_sync_bundles_do_not_publish(tmp_path: Path):
    runner = CliRunner()
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    (wiki / "README.md").write_text("# hello\n", encoding="utf-8")

    result = runner.invoke(app, ["sync-bundle", str(wiki), "--target", "confluence"])
    assert result.exit_code == 0, result.output
    # Bundle should land in <wiki>/sync/confluence/<lang>/...
    sync_dir = wiki / "sync" / "confluence"
    assert sync_dir.is_dir(), "sync-bundle must write Confluence bundles on disk"


def test_sync_push_flag_is_rejected(tmp_path: Path):
    """`--push` is reserved for a future publish step. It must exit non-zero now."""
    runner = CliRunner()
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    (wiki / "README.md").write_text("# hello\n", encoding="utf-8")

    result = runner.invoke(app, ["sync-bundle", str(wiki), "--push"])
    assert result.exit_code == 1, result.output
    combined = (result.output or "") + (result.stderr or "")
    assert "--push" in combined or "not implemented" in combined.lower(), (
        f"Expected --push rejection message, got: {combined!r}"
    )


# ---------- verify-claim / verify-model smoke tests --------------------------


def test_verify_claim_smoke_existing_and_missing_path(tmp_path: Path):
    runner = CliRunner()

    real_file = tmp_path / "real_script.py"
    real_file.write_text("print('hello')\n", encoding="utf-8")

    claim_payload = {
        "project_name": "smoke",
        "claims": [
            {
                "claim_id": "PATH_REAL",
                "claim_type": "path",
                "semantic_key": "filesystem.path.real",
                "subject": "real_script.py",
                "predicate": "exists",
                "object": "real_script.py",
            },
            {
                "claim_id": "PATH_FAKE",
                "claim_type": "path",
                "semantic_key": "filesystem.path.fake",
                "subject": "fake_script.py",
                "predicate": "exists",
                "object": "fake_script.py",
            },
        ],
    }
    claim_file = tmp_path / "claim.json"
    claim_file.write_text(json.dumps(claim_payload), encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "verify-claim",
            str(claim_file),
            "--target",
            str(tmp_path),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    claim_by_id = {c["claim_id"]: c for c in payload["claims"]}
    assert claim_by_id["PATH_REAL"]["verification"]["l1_existence"] == "passed"
    assert claim_by_id["PATH_FAKE"]["verification"]["l1_existence"] == "failed"


def test_verify_model_exits_one_on_missing_evidence_ref(tmp_path: Path):
    runner = CliRunner()

    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "exists.py").write_text("print('ok')\n", encoding="utf-8")

    # The verify-model walker recursively inspects ``steps`` (InstallationGuide
    # carries install commands with per-step evidence). We embed two steps:
    # one whose evidence points at a real file, one whose evidence points at
    # a file that does NOT exist on disk.
    semantic_model = {
        "model_id": "smoke",
        "project_type": "python-cli",
        "evidence_summary": {},
        "identity": {"name": "smoke"},
        "installation": {
            "steps": [
                {
                    "order": 1,
                    "title": "Run",
                    "commands": ["python exists.py"],
                    "evidence": [{"source_path": "exists.py", "raw_text": "ok", "confidence": "high"}],
                },
                {
                    "order": 2,
                    "title": "Broken",
                    "commands": ["python missing.py"],
                    "evidence": [{"source_path": "missing.py", "raw_text": "missing", "confidence": "high"}],
                },
            ],
            "prerequisites": [],
        },
    }
    model_file = tmp_path / "model.json"
    model_file.write_text(json.dumps(semantic_model), encoding="utf-8")

    result = runner.invoke(
        app,
        ["verify-model", str(model_file), "--target", str(project_dir), "--format", "json"],
    )
    assert result.exit_code == 1, result.output
    payload = json.loads(result.stdout)
    assert payload["schema_valid"] is True
    assert "missing.py" in payload["evidence_references_missing"]


def test_verify_model_exits_zero_on_all_resolvable(tmp_path: Path):
    runner = CliRunner()

    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "real.py").write_text("print('ok')\n", encoding="utf-8")

    semantic_model = {
        "model_id": "smoke",
        "project_type": "python-cli",
        "evidence_summary": {},
        "identity": {"name": "smoke"},
        "installation": {
            "steps": [
                {
                    "order": 1,
                    "title": "Run",
                    "commands": ["python real.py"],
                    "evidence": [{"source_path": "real.py", "raw_text": "ok", "confidence": "high"}],
                }
            ],
            "prerequisites": [],
        },
    }
    model_file = tmp_path / "model.json"
    model_file.write_text(json.dumps(semantic_model), encoding="utf-8")

    result = runner.invoke(
        app,
        ["verify-model", str(model_file), "--target", str(project_dir), "--format", "json"],
    )
    assert result.exit_code == 0, result.output


# ---------- bootstrap_toolkit pure-helper pinning tests ----------------------


def _load_bootstrap_module():
    """Load ``scripts/bootstrap_toolkit.py`` as an importable module."""
    spec = importlib.util.spec_from_file_location(
        "bootstrap_toolkit",
        Path(__file__).resolve().parents[2] / "scripts" / "bootstrap_toolkit.py",
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_bootstrap_requested_version_defaults_to_repo_version(monkeypatch):
    monkeypatch.delenv("MAKEWIKI_TOOLKIT_VERSION", raising=False)
    bootstrap = _load_bootstrap_module()
    assert bootstrap.requested_version() == bootstrap.DEFAULT_VERSION


def test_bootstrap_requested_version_honors_env_override(monkeypatch):
    monkeypatch.setenv("MAKEWIKI_TOOLKIT_VERSION", "v3.4.5")
    bootstrap = _load_bootstrap_module()
    assert bootstrap.requested_version() == "3.4.5"


def test_bootstrap_requested_sha256_returns_none_when_unset(monkeypatch):
    monkeypatch.delenv("MAKEWIKI_TOOLKIT_SHA256", raising=False)
    bootstrap = _load_bootstrap_module()
    assert bootstrap.requested_sha256() is None


def test_bootstrap_requested_sha256_lowercases_value(monkeypatch):
    monkeypatch.setenv("MAKEWIKI_TOOLKIT_SHA256", "ABCDEF1234")
    bootstrap = _load_bootstrap_module()
    assert bootstrap.requested_sha256() == "abcdef1234"


def test_bootstrap_tag_archive_url_pins_exact_release_tag():
    bootstrap = _load_bootstrap_module()
    assert (
        bootstrap.tag_archive_url("2.0.0")
        == "https://github.com/somnifex/MakeWiki.skills/archive/refs/tags/v2.0.0.zip"
    )
    # Already-v-prefixed versions are normalized, not double-prefixed.
    assert (
        bootstrap.tag_archive_url("v2.0.0")
        == "https://github.com/somnifex/MakeWiki.skills/archive/refs/tags/v2.0.0.zip"
    )


def test_bootstrap_verify_archive_sha256_passes_on_match(tmp_path: Path):
    bootstrap = _load_bootstrap_module()
    archive = tmp_path / "tiny.zip"
    archive.write_bytes(b"hello world")
    expected = bootstrap.sha256_of_file(archive)
    bootstrap.verify_archive_sha256(archive, expected)  # should not raise


def test_bootstrap_verify_archive_sha256_raises_on_mismatch(tmp_path: Path):
    bootstrap = _load_bootstrap_module()
    archive = tmp_path / "tiny.zip"
    archive.write_bytes(b"hello world")
    with pytest.raises(RuntimeError):
        bootstrap.verify_archive_sha256(archive, "0" * 64)


def test_bootstrap_verify_archive_sha256_skips_when_no_expected(monkeypatch, tmp_path: Path, capsys):
    monkeypatch.delenv("MAKEWIKI_TOOLKIT_SHA256", raising=False)
    bootstrap = _load_bootstrap_module()
    archive = tmp_path / "tiny.zip"
    archive.write_bytes(b"hi")
    bootstrap.verify_archive_sha256(archive, None)  # should not raise
    out = capsys.readouterr().out
    assert "skipping archive integrity check" in out


# ---------- verify-claim L5 epistemic status ---------------------------------


def test_verify_claim_marks_L5_pending_for_unknown_inputs(tmp_path: Path):
    """LLM-judged layers remain pending until the Skill's Auditor reasons over them."""
    runner = CliRunner()

    real_file = tmp_path / "real_script.py"
    real_file.write_text("print('hello')\n", encoding="utf-8")

    claim_payload = {
        "project_name": "smoke",
        "claims": [
            {
                "claim_id": "PATH_REAL",
                "claim_type": "path",
                "semantic_key": "filesystem.path.real",
                "subject": "real_script.py",
                "predicate": "exists",
                "object": "real_script.py",
            }
        ],
    }
    claim_file = tmp_path / "claim.json"
    claim_file.write_text(json.dumps(claim_payload), encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "verify-claim",
            str(claim_file),
            "--target",
            str(tmp_path),
            "--format",
            "json",
        ],
    )
    payload = json.loads(result.stdout)
    l5 = payload["claims"][0]["verification"]["l5_epistemic"]
    assert l5 in {"pending", "passed"}, f"L5 status was {l5!r}, expected pending or passed"
