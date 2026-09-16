"""Mechanical leakage-candidate scan over generated documentation.

A hit means "a benchmark provider's name appears in the generated docs" —
evidence for the Page Reviewer and the Final Semantic Auditor to adjudicate,
never a verdict by itself. The target project may genuinely integrate the
provider's product; Python only surfaces candidates with locations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from makewiki_skills.benchmarks.corpus import Corpus, CorpusError


@dataclass(frozen=True)
class LeakageHit:
    """One candidate occurrence of a benchmark provider term."""

    file: str  # posix relative path under the scanned wiki directory
    line: int
    term: str
    benchmarks: tuple[str, ...]  # benchmark ids whose provider maps to the term
    excerpt: str


def collect_leak_terms(
    corpus: Corpus, benchmark_ids: list[str]
) -> dict[str, tuple[str, ...]]:
    """Map benchmark id -> lowercased provider terms (provider + aliases)."""
    terms: dict[str, tuple[str, ...]] = {}
    for benchmark_id in benchmark_ids:
        entry = corpus.entry(benchmark_id)
        names = {entry.provider.lower()}
        for alias in entry.leak_terms:
            alias = alias.strip().lower()
            if alias:
                names.add(alias)
        terms[benchmark_id] = tuple(sorted(names))
    return terms


def scan_leakage(
    wiki_dir: Path,
    corpus: Corpus,
    benchmark_ids: list[str],
) -> list[LeakageHit]:
    """Scan ``*.md`` under ``wiki_dir`` for benchmark provider terms.

    Word-boundary, case-insensitive matching; hits are deduplicated per
    (file, line, term) and annotated with every benchmark whose provider
    maps to the term. Unknown benchmark ids raise :class:`CorpusError` —
    silently ignoring them would understate leakage.
    """
    known = set(corpus.benchmark_ids())
    unknown = [bid for bid in benchmark_ids if bid not in known]
    if unknown:
        raise CorpusError(
            "unknown benchmark ids in leakage scan: " + ", ".join(sorted(unknown))
        )
    per_benchmark = collect_leak_terms(corpus, benchmark_ids)
    term_owners: dict[str, list[str]] = {}
    for benchmark_id, terms in per_benchmark.items():
        for term in terms:
            term_owners.setdefault(term, []).append(benchmark_id)

    hits: list[LeakageHit] = []
    seen: set[tuple[str, int, str]] = set()
    for path in sorted(Path(wiki_dir).rglob("*.md")):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            hits.append(
                LeakageHit(
                    file=path.relative_to(wiki_dir).as_posix(),
                    line=0,
                    term="",
                    benchmarks=(),
                    excerpt=f"unreadable file: {exc}",
                )
            )
            continue
        for lineno, raw in enumerate(lines, start=1):
            lowered = raw.lower()
            for term, owners in term_owners.items():
                if re.search(rf"\b{re.escape(term)}\b", lowered):
                    key = (path.relative_to(wiki_dir).as_posix(), lineno, term)
                    if key in seen:
                        continue
                    seen.add(key)
                    hits.append(
                        LeakageHit(
                            file=key[0],
                            line=key[1],
                            term=term,
                            benchmarks=tuple(sorted(set(owners))),
                            excerpt=raw.strip()[:200],
                        )
                    )
    return hits
