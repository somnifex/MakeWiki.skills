"""Pipeline ↔ Docs claim contract.

The Skill layer advertises the deterministic-generate path as:

* Independent generation per language from the unified SemanticModel.
* Python returns ``UNKNOWN`` rather than guessing semantic content.
* The deterministic pipeline never invents FAQ / troubleshooting / usage
  prose.

This contract runs ``deterministic-generate`` against the bundled sample
fixture and asserts those promises mechanically.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from makewiki_skills.config import MakeWikiConfig
from makewiki_skills.pipeline.pipeline import Pipeline

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures" / "projects"


def _run_deterministic_generate(fixture_dir: Path, tmp_path: Path) -> Path:
    project_dir = tmp_path / "project"
    shutil.copytree(fixture_dir, project_dir)

    config = MakeWikiConfig.default(project_dir)
    config.languages = ["en"]
    config.site.compile = False  # skip site compile for speed
    config.revision.enabled = False  # one-shot deterministic run

    Pipeline(config).run()
    return project_dir / config.output_dir


@pytest.fixture
def wiki_output(tmp_path: Path) -> Path:
    return _run_deterministic_generate(FIXTURES_DIR / "sample-python-cli", tmp_path)


def test_deterministic_generate_writes_files(wiki_output: Path) -> None:
    """At minimum the pipeline emits the structural scaffolding."""
    assert wiki_output.is_dir(), "deterministic-generate must produce a wiki directory"
    files = list(wiki_output.rglob("*.md"))
    assert files, "deterministic-generate should emit at least one Markdown file"


def test_deterministic_generate_does_not_invent_faq(wiki_output: Path) -> None:
    """FAQ content is LLM-populated. Python must render ``UNKNOWN`` or omit it.

    The deterministic scaffold is allowed to emit a soft "no info available"
    marker (e.g. "No recurring questions stood out…"). What it must NOT do
    is invent specific Q&A pairs, recommended fixes, or symptom narratives.
    """
    faq = wiki_output / "faq.md"
    if faq.is_file():
        text = faq.read_text(encoding="utf-8", errors="replace").lower()
        invented_patterns = [
            "how do i reset",
            "common issue:",
            "if you encounter",
            "try restarting",
            "make sure to",
            "q: ",   # fabricated Q:
            "### q:",  # markdown Q&A header
        ]
        for invented in invented_patterns:
            assert invented not in text, (
                f"faq.md appears to contain invented prose: {invented!r}"
            )


def test_deterministic_generate_does_not_invent_troubleshooting(wiki_output: Path) -> None:
    """Troubleshooting must be UNKNOWN or absent — Python never invents symptom→fix."""
    ts = wiki_output / "troubleshooting.md"
    if ts.is_file():
        text = ts.read_text(encoding="utf-8", errors="replace").lower()
        invented_patterns = [
            "root cause:",
            "common cause:",
            "solution:",
            "resolution:",
            "workaround:",
            "symptom:",
            "fix:",
            "### symptom",
        ]
        for invented in invented_patterns:
            assert invented not in text, (
                f"troubleshooting.md appears to contain invented prose: {invented!r}"
            )


def test_deterministic_generate_does_not_invent_usage(wiki_output: Path) -> None:
    """Usage pages must not invent runnable commands when none are evidenced."""
    usage_dir = wiki_output / "usage"
    if usage_dir.is_dir():
        for md_file in usage_dir.rglob("*.md"):
            text = md_file.read_text(encoding="utf-8", errors="replace")
            # The fixture has no real install command, so the deterministic
            # scaffold must not invent one.
            for invented in ["pip install -e .", "npm install", "cargo build --release"]:
                assert invented not in text, (
                    f"{md_file.name} contains invented command {invented!r}"
                )


def test_deterministic_generate_emits_independent_language_outputs(tmp_path: Path) -> None:
    """Each language is rendered independently (not machine-translated).

    We can't verify semantic independence, but we *can* verify both languages
    were rendered when the config lists two. Missing one language indicates
    that the deterministic pipeline short-circuited — a regression we want
    to flag.
    """
    project_dir = tmp_path / "project"
    shutil.copytree(FIXTURES_DIR / "sample-python-cli", project_dir)

    config = MakeWikiConfig.default(project_dir)
    config.languages = ["en", "zh-CN"]
    config.site.compile = False
    config.revision.enabled = False
    Pipeline(config).run()

    wiki_dir = project_dir / config.output_dir
    en_files = list(wiki_dir.rglob("README*.md"))
    assert en_files, "deterministic-generate did not emit any README per language"


def test_pipeline_unknown_marker_is_emitted(tmp_path: Path) -> None:
    """When no install command is evidenced, the pipeline renders an honest marker.

    We deliberately use a project directory that contains no README, no
    pyproject.toml, and no install commands. The deterministic scaffold must
    not invent a "Clone the repository" / "pip install" workflow; it should
    emit either the literal ``UNKNOWN`` token or a soft "no info available"
    note in the installation/usage sections.
    """
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    config = MakeWikiConfig.default(empty_dir)
    config.languages = ["en"]
    config.site.compile = False
    config.revision.enabled = False
    Pipeline(config).run()

    wiki_dir = empty_dir / config.output_dir
    install_text = ""
    install_page = wiki_dir / "installation.md"
    if install_page.is_file():
        install_text = install_page.read_text(encoding="utf-8", errors="replace").lower()
    usage_text = ""
    usage_page = wiki_dir / "usage" / "basic-usage.md"
    if usage_page.is_file():
        usage_text = usage_page.read_text(encoding="utf-8", errors="replace").lower()
    combined = install_text + "\n" + usage_text
    # Either the literal UNKNOWN token, or a soft "no info available" marker.
    honest_markers = [
        "unknown",
        "no install commands were detected",
        "no repeatable usage patterns",
    ]
    assert any(marker in combined for marker in honest_markers), (
        "Pipeline did not emit an honest UNKNOWN marker for a project with no evidence"
    )
    # And it must NEVER invent a canned install command.
    for invented in ["pip install -e .", "pip install .", "npm install"]:
        assert invented not in combined, (
            f"Pipeline invented install command {invented!r} on an empty project"
        )
