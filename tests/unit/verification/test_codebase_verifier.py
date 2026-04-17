"""Tests for CodebaseVerifier — post-generation verification against the real codebase."""

from pathlib import Path

from makewiki_skills.documents import GeneratedDocument
from makewiki_skills.verification.codebase_verifier import CodebaseVerifier


def _doc(filename: str, content: str, lang: str = "en") -> GeneratedDocument:
    return GeneratedDocument(
        filename=filename,
        base_name=filename,
        language_code=lang,
        content=content,
    )


# ---------------------------------------------------------------------------
# Path verification
# ---------------------------------------------------------------------------


def test_existing_path_verified(tmp_path: Path):
    """A path that exists on disk should be verified."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("# main", encoding="utf-8")

    doc = _doc("README.md", "# App\n\nSee `./src/main.py` for details.\n")
    verifier = CodebaseVerifier(tmp_path)
    report = verifier.verify({"en": [doc]})

    path_checks = [c for c in report.checks if c.claim_type == "path"]
    assert len(path_checks) > 0
    assert all(c.verified for c in path_checks)


def test_missing_path_fails(tmp_path: Path):
    """A path that does not exist on disk should fail."""
    doc = _doc("README.md", "# App\n\nSee `./nonexistent/file.py` for details.\n")
    verifier = CodebaseVerifier(tmp_path)
    report = verifier.verify({"en": [doc]})

    path_checks = [c for c in report.checks if c.claim_type == "path"]
    assert len(path_checks) > 0
    assert any(not c.verified for c in path_checks)


# ---------------------------------------------------------------------------
# Command verification
# ---------------------------------------------------------------------------


def test_makefile_command_verified(tmp_path: Path):
    """Commands matching Makefile targets should be verified."""
    (tmp_path / "Makefile").write_text("serve:\n\tpython -m http.server\n", encoding="utf-8")

    doc = _doc("usage.md", "# Usage\n\n```bash\nmake serve\n```\n")
    verifier = CodebaseVerifier(tmp_path)
    report = verifier.verify({"en": [doc]})

    cmd_checks = [c for c in report.checks if c.claim_type == "command"]
    serve_check = next((c for c in cmd_checks if "serve" in c.claim_text), None)
    assert serve_check is not None
    assert serve_check.verified


def test_generic_tool_always_passes(tmp_path: Path):
    """Generic tool commands (git, pip, etc.) should always pass."""
    doc = _doc("install.md", "# Install\n\n```bash\npip install -e .\ngit clone <url>\n```\n")
    verifier = CodebaseVerifier(tmp_path)
    report = verifier.verify({"en": [doc]})

    cmd_checks = [c for c in report.checks if c.claim_type == "command"]
    assert all(c.verified for c in cmd_checks)


def test_unknown_command_fails(tmp_path: Path):
    """Commands not found in the project should fail."""
    # Empty project — no Makefile, no package.json, no pyproject.toml
    doc = _doc("usage.md", "# Usage\n\n```bash\nmyapp deploy --force\n```\n")
    verifier = CodebaseVerifier(tmp_path)
    report = verifier.verify({"en": [doc]})

    cmd_checks = [c for c in report.checks if c.claim_type == "command"]
    assert len(cmd_checks) > 0
    assert any(not c.verified for c in cmd_checks)


def test_placeholder_command_passes(tmp_path: Path):
    """Commands with <placeholders> should pass (they are templates)."""
    doc = _doc("usage.md", "# Usage\n\n```bash\nmyapp run <your-file>\n```\n")
    verifier = CodebaseVerifier(tmp_path)
    report = verifier.verify({"en": [doc]})

    cmd_checks = [c for c in report.checks if c.claim_type == "command"]
    placeholder_checks = [c for c in cmd_checks if "<your-file>" in c.claim_text]
    assert len(placeholder_checks) > 0
    assert all(c.verified for c in placeholder_checks)


# ---------------------------------------------------------------------------
# Config key verification
# ---------------------------------------------------------------------------


def test_config_key_found_in_yaml(tmp_path: Path):
    """Config keys that exist in project YAML should be verified."""
    (tmp_path / "config.yaml").write_text("server:\n  port: 8080\n  host: localhost\n", encoding="utf-8")

    doc = _doc("config.md", "# Config\n\nSet `server.port` to change the port.\n")
    verifier = CodebaseVerifier(tmp_path)
    report = verifier.verify({"en": [doc]})

    key_checks = [c for c in report.checks if c.claim_type == "config_key"]
    port_check = next((c for c in key_checks if c.claim_text == "server.port"), None)
    assert port_check is not None
    assert port_check.verified


def test_env_var_pattern_passes(tmp_path: Path):
    """UPPER_CASE env-var-style keys should be whitelisted."""
    doc = _doc("config.md", "# Config\n\nSet `DATABASE_URL` to your connection string.\n")
    verifier = CodebaseVerifier(tmp_path)
    report = verifier.verify({"en": [doc]})

    key_checks = [c for c in report.checks if c.claim_type == "config_key"]
    db_check = next((c for c in key_checks if c.claim_text == "DATABASE_URL"), None)
    assert db_check is not None
    assert db_check.verified


def test_unknown_config_key_fails(tmp_path: Path):
    """Config keys not in any config file should fail."""
    doc = _doc("config.md", "# Config\n\nSet `nosuch.key` to enable the feature.\n")
    verifier = CodebaseVerifier(tmp_path)
    report = verifier.verify({"en": [doc]})

    key_checks = [c for c in report.checks if c.claim_type == "config_key"]
    bad_check = next((c for c in key_checks if c.claim_text == "nosuch.key"), None)
    assert bad_check is not None
    assert not bad_check.verified


# ---------------------------------------------------------------------------
# Report-level assertions
# ---------------------------------------------------------------------------


def test_score_all_pass(tmp_path: Path):
    """Score should be 1.0 when all checks pass."""
    doc = _doc("install.md", "# Install\n\n```bash\npip install -e .\n```\n")
    verifier = CodebaseVerifier(tmp_path)
    report = verifier.verify({"en": [doc]})

    assert report.score == 1.0
    assert report.passed


def test_score_reflects_failures(tmp_path: Path):
    """Score should drop when there are failures."""
    doc = _doc("usage.md", "# Usage\n\n```bash\nmyapp nonexistent\n```\n\nSee `./missing.txt`.\n")
    verifier = CodebaseVerifier(tmp_path)
    report = verifier.verify({"en": [doc]})

    assert report.failed_count > 0
    assert report.score < 1.0
    assert not report.passed


def test_multi_language_verification(tmp_path: Path):
    """Verification should cover documents from all languages."""
    (tmp_path / "Makefile").write_text("serve:\n\techo ok\n", encoding="utf-8")

    en_doc = _doc("usage.md", "# Usage\n\n```bash\nmake serve\n```\n", lang="en")
    zh_doc = _doc("usage.zh-CN.md", "# 使用\n\n```bash\nmake serve\n```\n", lang="zh-CN")
    verifier = CodebaseVerifier(tmp_path)
    report = verifier.verify({"en": [en_doc], "zh-CN": [zh_doc]})

    # Both documents' commands should be checked
    cmd_checks = [c for c in report.checks if c.claim_type == "command"]
    assert len(cmd_checks) >= 2
    assert all(c.verified for c in cmd_checks if "serve" in c.claim_text)
