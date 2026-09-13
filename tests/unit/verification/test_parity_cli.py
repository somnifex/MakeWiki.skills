"""CLI regression tests for `makewiki parity` exit semantics and summary.

Covers the honest terminal-state contract: verdict `pending` (mechanical
checks clean, aligned passages ready for the LLM Auditor) is parity's normal
completion — exit 0; only a real failed check exits 1. The human summary must
name the real verdict and the failed count (never a bare "FAIL <passed>/<total>").
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from typer.testing import CliRunner

from makewiki_skills.cli import app


def _plain(text: str) -> str:
    """Strip Rich/Typer ANSI colour codes from rendered output."""
    return re.sub(r"\x1b\[[0-9;]*m", "", text or "")


_ALIGNED_BODY = (
    "<!-- makewiki:section=overview -->\n## Overview\n\n"
    "[[id:run-cmd]]\n```bash\necho aligned\n```\n"
)

_DIVERGED_BODY = (
    "<!-- makewiki:section=overview -->\n## Overview\n\n"
    "[[id:run-cmd]]\n```bash\necho diverged\n```\n"
)


def _write_pair(wiki: Path, en: str, zh: str) -> None:
    wiki.mkdir(parents=True, exist_ok=True)
    (wiki / "guide.md").write_text(en, encoding="utf-8")
    (wiki / "guide.zh-CN.md").write_text(zh, encoding="utf-8")


def test_parity_pending_exits_zero_with_honest_json(tmp_path: Path):
    """Verdict `pending` (mechanical checks clean, aligned passages ready for
    the LLM Auditor) exits 0 — it is parity's normal terminal state, not a
    failure."""
    wiki = tmp_path / "wiki"
    _write_pair(wiki, _ALIGNED_BODY, _ALIGNED_BODY)

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["parity", str(tmp_path), "--wiki-dir", str(wiki), "--format", "json"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["l4"]["verdict"] == "pending"
    assert payload["l4"]["failed_count"] == 0
    assert payload["aligned_passages"], "aligned passages must be emitted for the LLM Auditor"


def test_parity_pending_human_summary_names_verdict_and_failed_count(tmp_path: Path):
    """The human summary names the real verdict and failed count — never a
    bare passed-count next to FAIL ("FAIL 49/223")."""
    wiki = tmp_path / "wiki"
    _write_pair(wiki, _ALIGNED_BODY, _ALIGNED_BODY)

    runner = CliRunner()
    result = runner.invoke(app, ["parity", str(tmp_path), "--wiki-dir", str(wiki)])
    plain = _plain(result.output)
    assert result.exit_code == 0, plain
    assert "PENDING" in plain, plain
    assert "0 failed" in plain, plain
    assert "ready for LLM prose review" in plain, plain


def test_parity_failed_exits_one_and_lists_failures(tmp_path: Path):
    """A real cross-language block divergence is FAILED with exit 1."""
    wiki = tmp_path / "wiki"
    _write_pair(wiki, _ALIGNED_BODY, _DIVERGED_BODY)

    runner = CliRunner()
    result = runner.invoke(app, ["parity", str(tmp_path), "--wiki-dir", str(wiki)])
    plain = _plain(result.output)
    assert result.exit_code == 1, plain
    assert "FAILED" in plain, plain
    # Honest summary format: real failed count first, then passed / total.
    assert re.search(r"\d+ failed, \d+ passed / \d+ checks", plain), plain
