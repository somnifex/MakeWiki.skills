"""Functional tests for the Benchmark Library toolkit (mechanical plane)."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from makewiki_skills.benchmarks.acquire import acquire_benchmarks
from makewiki_skills.benchmarks.corpus import (
    REGISTRY_FILENAME,
    build_index,
    load_corpus,
    validate_corpus,
)
from makewiki_skills.benchmarks.leakage import scan_leakage
from makewiki_skills.benchmarks.profile import (
    load_reference_profile,
    render_reference_profile,
    validate_reference_profile,
)
from makewiki_skills.cli import app

REGISTRY_YAML = """\
benchmarks:
  - id: synth-search-concepts
    provider: synthco
    title: Search concepts
    source_url: https://example.com/search
    normalized_path: normalized/synth-search-concepts.yaml
    pattern_ids: [p-mental-model]
    tags: [search]
    quality_notes: [strong mental model]
    acquire: metadata-only
    license_or_usage_note: structural summary only
    leak_terms: [SynthCo]
patterns:
  - id: p-mental-model
    path: patterns/p-mental-model.yaml
"""

PATTERN_YAML = """\
id: p-mental-model
description: Establish a mental model before exposing tuning parameters.
suitable_when:
  - users must choose between strategies
information_shape:
  - problem
  - mental_model
  - tuning
good_traits:
  - concepts_before_parameters
anti_patterns:
  - parameter_dump
source_examples:
  - synth-search-concepts
"""

NORMALIZED_YAML = """\
id: synth-search-concepts
source:
  provider: synthco
  title: Search concepts
  url: https://example.com/search
summary: Explains strategy tradeoffs before exposing tuning parameters.
observed_archetypes:
  - concept
  - comparison
suitable_intents:
  - understand
  - choose
information_shape:
  - define_problem
  - establish_mental_model
  - compare_tradeoffs
strong_traits:
  - concepts_before_parameters
  - explicit_tradeoffs
anti_patterns:
  - parameter_dump
useful_for:
  - retrieval
  - tuning
tags:
  - search
pattern_ids:
  - p-mental-model
verification: unverified-structural-summary
"""


@pytest.fixture()
def corpus_dir(tmp_path: Path) -> Path:
    root = tmp_path / "corpus"
    (root / "patterns").mkdir(parents=True)
    (root / "normalized").mkdir()
    (root / "patterns" / "p-mental-model.yaml").write_text(PATTERN_YAML, encoding="utf-8")
    (root / "normalized" / "synth-search-concepts.yaml").write_text(
        NORMALIZED_YAML, encoding="utf-8"
    )
    (root / REGISTRY_FILENAME).write_text(REGISTRY_YAML, encoding="utf-8")
    return root


def test_load_and_validate_corpus(corpus_dir: Path):
    corpus = load_corpus(corpus_dir)
    assert corpus.benchmark_ids() == ["synth-search-concepts"]
    assert validate_corpus(corpus_dir) == []
    entry = corpus.entry("synth-search-concepts")
    assert entry.provider == "synthco"
    assert entry.acquire == "metadata-only"


def test_build_index_is_deterministic(corpus_dir: Path):
    corpus = load_corpus(corpus_dir)
    first = build_index(corpus)
    second = build_index(load_corpus(corpus_dir))
    assert first == second
    assert first["counts"] == {"benchmarks": 1, "patterns": 1}
    entry = first["benchmarks"][0]
    assert entry["id"] == "synth-search-concepts"
    assert entry["pattern_ids"] == ["p-mental-model"]
    assert first["corpus_digest"] == second["corpus_digest"]


def test_validate_corpus_reports_missing_pattern(corpus_dir: Path):
    (corpus_dir / "patterns" / "p-mental-model.yaml").unlink()
    problems = validate_corpus(corpus_dir)
    assert any("pattern p-mental-model" in p for p in problems)


def test_reference_profile_round_trip(corpus_dir: Path, tmp_path: Path):
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(
        "page_id: retrieval-engine\n"
        "references:\n"
        "  - benchmark_id: synth-search-concepts\n"
        "    relevance: [mental-model-first]\n"
        "    borrow: [explain strategies before parameters]\n"
        "    do_not_copy: [SynthCo terminology]\n",
        encoding="utf-8",
    )
    corpus = load_corpus(corpus_dir)
    profile = load_reference_profile(profile_path)
    assert validate_reference_profile(
        profile, corpus, max_examples_per_page=3
    ) == []
    rendered = render_reference_profile(
        profile, corpus, max_reference_tokens=5000
    )
    assert rendered.within_budget
    assert rendered.est_tokens > 0
    assert "synth-search-concepts" in rendered.markdown
    assert "SynthCo terminology" in rendered.markdown


def test_reference_profile_rejects_unknown_benchmark(corpus_dir: Path, tmp_path: Path):
    profile_path = tmp_path / "bad.yaml"
    profile_path.write_text(
        "page_id: x\nreferences:\n  - benchmark_id: nope\n", encoding="utf-8"
    )
    corpus = load_corpus(corpus_dir)
    profile = load_reference_profile(profile_path)
    problems = validate_reference_profile(
        profile, corpus, max_examples_per_page=3
    )
    assert any("unknown benchmark 'nope'" in p for p in problems)


def test_scan_leakage_finds_provider_terms(corpus_dir: Path, tmp_path: Path):
    corpus = load_corpus(corpus_dir)
    page = tmp_path / "retrieval-engine.md"
    page.write_text(
        "The SynthCo engine supports hybrid strategies.\n", encoding="utf-8"
    )
    hits = scan_leakage(tmp_path, corpus, ["synth-search-concepts"])
    assert [(h.file, h.line, h.term) for h in hits] == [
        ("retrieval-engine.md", 1, "synthco")
    ]


def test_acquire_refuses_metadata_only(corpus_dir: Path, monkeypatch):
    def boom(url: str, timeout: float) -> bytes:
        raise AssertionError("network fetch must not run for metadata-only")

    monkeypatch.setattr("makewiki_skills.benchmarks.acquire.fetch_url", boom)
    results = acquire_benchmarks(corpus_dir, ["synth-search-concepts"])
    assert [r.status for r in results] == ["refused-metadata-only"]


def test_corpus_digest_ignores_sources_and_index(tmp_path: Path):
    from makewiki_skills.benchmarks.corpus import corpus_digest

    root = tmp_path / "corpus"
    (root / "patterns").mkdir(parents=True)
    (root / "normalized").mkdir()
    (root / "patterns" / "p-mental-model.yaml").write_text(PATTERN_YAML, encoding="utf-8")
    (root / "normalized" / "synth-search-concepts.yaml").write_text(
        NORMALIZED_YAML, encoding="utf-8"
    )
    (root / REGISTRY_FILENAME).write_text(REGISTRY_YAML, encoding="utf-8")

    before = corpus_digest(root)
    (root / "sources" / "synthco").mkdir(parents=True)
    (root / "sources" / "synthco" / "synth-search-concepts.meta.yaml").write_text(
        "id: synth-search-concepts\nretrieved_at: '2026-01-01T00:00:00+00:00'\n",
        encoding="utf-8",
    )
    (root / "index").mkdir()
    (root / "index" / "benchmark-index.json").write_text("{}", encoding="utf-8")
    assert corpus_digest(root) == before, (
        "an acquisition must never stale the committed index digest"
    )


def test_cli_acquire_ids_without_corpus_positional(corpus_dir: Path, tmp_path, monkeypatch):
    """`benchmark-acquire <id>` must resolve the corpus from config, not choke
    on positional ambiguity (regression: typer variadic + trailing positional)."""

    (tmp_path / "makewiki.config.yaml").write_text(
        "benchmark:\n  corpus_path: corpus-under-test\n", encoding="utf-8"
    )
    corpus = tmp_path / "corpus-under-test"
    corpus.mkdir()
    (corpus / "patterns").mkdir()
    (corpus / "normalized").mkdir()
    (corpus / "patterns" / "p-mental-model.yaml").write_text(PATTERN_YAML, encoding="utf-8")
    (corpus / "normalized" / "synth-search-concepts.yaml").write_text(
        NORMALIZED_YAML, encoding="utf-8"
    )
    (corpus / REGISTRY_FILENAME).write_text(REGISTRY_YAML, encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["benchmark-acquire", "synth-search-concepts"])
    assert result.exit_code == 1  # refused-metadata-only, parsed correctly
    assert "refused-metadata-only" in result.output


def test_cli_leakage_fails_loudly_without_corpus(tmp_path, monkeypatch):

    profile = tmp_path / "p.yaml"
    profile.write_text(
        "page_id: x\nreferences:\n  - benchmark_id: synth-search-concepts\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)  # default corpus_path 'benchmarks' does not exist here
    result = CliRunner().invoke(
        app, ["benchmark-leakage", str(tmp_path), "--profile", str(profile)]
    )
    assert result.exit_code == 1, (
        "a missing corpus must fail loudly, never report a clean scan"
    )
