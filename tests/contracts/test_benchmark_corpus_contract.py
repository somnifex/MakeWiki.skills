"""Benchmark corpus contract: registry, cross-links, and index freshness.

The four corpus layers must stay separable (sources / normalized / patterns /
index), every registry pointer must resolve, and the committed compact index
must be exactly what the current corpus deterministically regenerates.
"""

from __future__ import annotations

import json
from pathlib import Path

from makewiki_skills.benchmarks.corpus import (
    INDEX_FILENAME,
    build_index,
    load_corpus,
    validate_corpus,
    write_index,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CORPUS_ROOT = PROJECT_ROOT / "benchmarks"


def test_benchmark_corpus_exists():
    assert (CORPUS_ROOT / "registry.yaml").is_file(), (
        "benchmarks/registry.yaml is the curation entry point and must exist"
    )


def test_corpus_validates_clean():
    problems = validate_corpus(CORPUS_ROOT)
    assert not problems, "benchmark corpus must validate cleanly: " + "; ".join(problems)


def test_registry_layers_are_separable():
    corpus = load_corpus(CORPUS_ROOT)
    assert corpus.benchmark_ids(), "registry must curate at least one benchmark"
    for entry_id in corpus.benchmark_ids():
        entry = corpus.entry(entry_id)
        assert entry.normalized_path.startswith("normalized/"), (
            f"{entry_id}: normalized layer must live under normalized/"
        )
        for pattern_id in entry.pattern_ids:
            assert pattern_id in corpus.patterns, (
                f"{entry_id}: unknown pattern {pattern_id}"
            )


def test_committed_index_matches_regeneration():
    corpus = load_corpus(CORPUS_ROOT)
    index = build_index(corpus)
    committed = json.loads(
        (CORPUS_ROOT / "index" / INDEX_FILENAME).read_text(encoding="utf-8")
    )
    assert committed == index, (
        "committed benchmarks/index/benchmark-index.json is stale; "
        "regenerate with: python scripts/run_toolkit.py benchmark-index benchmarks"
    )


def test_write_index_round_trips(tmp_path: Path):
    corpus = load_corpus(CORPUS_ROOT)
    index = build_index(corpus)
    out = write_index(index, tmp_path / "idx.json")
    assert json.loads(out.read_text(encoding="utf-8")) == index
