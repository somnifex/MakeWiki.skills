"""Benchmark corpus: load, validate, digest, and compact-index (mechanical plane).

The corpus keeps four layers distinguishable on disk:

* ``registry.yaml`` — curated metadata (ids, providers, pointers, licensing).
* ``normalized/<id>.yaml`` — structural summaries of excellent pages.
* ``patterns/<id>.yaml`` — distilled, source-agnostic documentation patterns.
* ``sources/`` — raw fetched pages (local cache only; never required).
* ``index/benchmark-index.json`` — generated compact index (stage-1 input).

Everything here is mechanical proof: schema, id uniqueness, cross-links,
digest. Deciding which benchmark helps a page is cognitive work and lives in
``tasks/select-benchmarks.md``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel

from makewiki_skills.benchmarks.model import (
    BenchmarkPattern,
    NormalizedBenchmark,
    Registry,
    RegistryEntry,
    estimate_tokens,
)

REGISTRY_FILENAME = "registry.yaml"
NORMALIZED_DIRNAME = "normalized"
PATTERNS_DIRNAME = "patterns"
SOURCES_DIRNAME = "sources"
INDEX_DIRNAME = "index"
INDEX_FILENAME = "benchmark-index.json"
INDEX_SCHEMA_VERSION = 1
GENERATOR = "makewiki-skills benchmark-index v1"


class CorpusError(Exception):
    """A mechanical corpus defect: missing file, schema break, or bad link."""


def _read_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise CorpusError(f"invalid YAML in {path}: {exc}") from exc


def _validated(model_cls: type[BaseModel], raw: Any, label: str) -> Any:
    try:
        return model_cls.model_validate(raw)
    except Exception as exc:
        raise CorpusError(f"invalid {label}: {exc}") from exc


@dataclass(frozen=True)
class Corpus:
    """A loaded, cross-validated benchmark corpus."""

    root: Path
    registry: Registry
    normalized: dict[str, NormalizedBenchmark]
    patterns: dict[str, BenchmarkPattern]

    def entry(self, benchmark_id: str) -> RegistryEntry:
        for candidate in self.registry.benchmarks:
            if candidate.id == benchmark_id:
                return candidate
        raise CorpusError(f"unknown benchmark id: {benchmark_id!r}")

    def benchmark_ids(self) -> list[str]:
        return sorted(self.normalized)


def load_corpus(corpus_dir: Path) -> Corpus:
    """Load ``registry.yaml`` plus every referenced normalized/pattern file.

    Raises :class:`CorpusError` on the first missing or invalid file, and a
    combined report when cross-links (pattern ids, source_examples) dangle.
    """
    root = Path(corpus_dir)
    registry_path = root / REGISTRY_FILENAME
    if not registry_path.is_file():
        raise CorpusError(f"benchmark registry not found: {registry_path}")
    registry = _validated(Registry, _read_yaml(registry_path), f"registry {registry_path}")

    normalized: dict[str, NormalizedBenchmark] = {}
    for entry in registry.benchmarks:
        normalized_path = root / entry.normalized_path
        if not normalized_path.is_file():
            raise CorpusError(
                f"{entry.id}: normalized benchmark file missing: {entry.normalized_path}"
            )
        nb = _validated(
            NormalizedBenchmark,
            _read_yaml(normalized_path),
            f"normalized benchmark {normalized_path}",
        )
        if nb.id != entry.id:
            raise CorpusError(
                f"{entry.id}: {entry.normalized_path} declares id {nb.id!r}"
            )
        if nb.source.provider != entry.provider or nb.source.title != entry.title:
            raise CorpusError(
                f"{entry.id}: provider/title disagree between registry and "
                f"{entry.normalized_path}"
            )
        if nb.id in normalized:
            raise CorpusError(f"registry: duplicate benchmark id {nb.id!r}")
        normalized[nb.id] = nb

    patterns: dict[str, BenchmarkPattern] = {}
    for ref in registry.patterns:
        pattern_path = root / ref.path
        if not pattern_path.is_file():
            raise CorpusError(f"pattern {ref.id}: pattern file missing: {ref.path}")
        pattern = _validated(
            BenchmarkPattern, _read_yaml(pattern_path), f"pattern {pattern_path}"
        )
        if pattern.id != ref.id:
            raise CorpusError(f"pattern {ref.id}: {ref.path} declares id {pattern.id!r}")
        if pattern.id in patterns:
            raise CorpusError(f"registry: duplicate pattern id {pattern.id!r}")
        patterns[pattern.id] = pattern

    problems: list[str] = []
    for entry in registry.benchmarks:
        nb = normalized[entry.id]
        for pid in entry.pattern_ids + nb.pattern_ids:
            if pid not in patterns:
                problems.append(f"{entry.id}: references unknown pattern {pid!r}")
    known_benchmarks = set(normalized)
    for pattern in patterns.values():
        for example in pattern.source_examples:
            if example not in known_benchmarks:
                problems.append(
                    f"pattern {pattern.id}: source_examples references unknown "
                    f"benchmark {example!r}"
                )
    if problems:
        raise CorpusError(
            "benchmark corpus cross-link validation failed:\n"
            + "\n".join(f"  - {p}" for p in problems)
        )

    return Corpus(root=root, registry=registry, normalized=normalized, patterns=patterns)


def validate_corpus(corpus_dir: Path) -> list[str]:
    """Return every structural problem in a corpus (empty list = valid)."""
    try:
        load_corpus(corpus_dir)
    except CorpusError as exc:
        lines = [line.strip() for line in str(exc).splitlines()]
        found = [line.lstrip("- ").strip() for line in lines if line.startswith("- ")]
        return found or [str(exc)]
    return []


def corpus_digest(corpus_dir: Path) -> str:
    """Deterministic sha256 over the corpus CONTENT layers, path-sorted.

    Only ``registry.yaml``, ``normalized/*.yaml`` and ``patterns/*.yaml``
    feed the digest: ``sources/`` is a mutable local fetch cache and
    ``index/`` is generated output, so neither may change the digest (an
    acquisition must never stale the committed index).
    """
    root = Path(corpus_dir)
    hasher = hashlib.sha256()
    files = sorted(
        p
        for p in root.rglob("*")
        if p.is_file()
        and p.suffix in {".yaml", ".yml"}
        and SOURCES_DIRNAME not in p.parts
        and INDEX_DIRNAME not in p.parts
    )
    for path in files:
        hasher.update(path.relative_to(root).as_posix().encode("utf-8"))
        hasher.update(b"\x00")
        hasher.update(path.read_bytes())
        hasher.update(b"\x00")
    return hasher.hexdigest()


def build_index(corpus: Corpus) -> dict[str, Any]:
    """Assemble the compact stage-1 index as a plain JSON-ready dict.

    Deterministic: benchmarks sorted by id, patterns sorted by id, stable
    key order. Contains metadata only — never benchmark prose bodies.
    """

    def entry_view(entry: RegistryEntry) -> dict[str, Any]:
        nb = corpus.normalized[entry.id]
        return {
            "id": nb.id,
            "provider": nb.source.provider,
            "title": nb.source.title,
            "url": nb.source.url,
            "summary": nb.summary,
            "observed_archetypes": nb.observed_archetypes,
            "suitable_intents": nb.suitable_intents,
            "information_shape": nb.information_shape,
            "strong_traits": nb.strong_traits,
            "anti_patterns": nb.anti_patterns,
            "useful_for": nb.useful_for,
            "tags": nb.tags,
            "pattern_ids": sorted(set(entry.pattern_ids) | set(nb.pattern_ids)),
            "quality_notes": entry.quality_notes,
            "normalized_path": entry.normalized_path,
            "acquire": entry.acquire,
            "verification": nb.verification,
            "est_tokens": estimate_tokens(nb.render_text()),
        }

    def pattern_view(pattern: BenchmarkPattern) -> dict[str, Any]:
        return {
            "id": pattern.id,
            "description": pattern.description,
            "suitable_when": pattern.suitable_when,
            "information_shape": pattern.information_shape,
            "good_traits": pattern.good_traits,
            "anti_patterns": pattern.anti_patterns,
            "source_examples": [
                ex for ex in pattern.source_examples if ex in known_benchmarks
            ],
            "est_tokens": estimate_tokens(pattern.render_text()),
        }

    known_benchmarks = set(corpus.normalized)
    entries = sorted(corpus.registry.benchmarks, key=lambda e: e.id)
    benchmark_entries = [entry_view(e) for e in entries]
    pattern_entries = [
        pattern_view(corpus.patterns[pid]) for pid in sorted(corpus.patterns)
    ]
    return {
        "schema_version": INDEX_SCHEMA_VERSION,
        "generator": GENERATOR,
        "corpus_digest": corpus_digest(corpus.root),
        "counts": {
            "benchmarks": len(benchmark_entries),
            "patterns": len(pattern_entries),
        },
        "benchmarks": benchmark_entries,
        "patterns": pattern_entries,
    }


def write_index(index: dict[str, Any], output_path: Path) -> Path:
    """Write the index JSON (mkdir -p, deterministic formatting)."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return output_path
