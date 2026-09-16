"""ReferenceProfile: mechanical validation and compact rendering.

The mechanical plane only: it proves a Selector-authored profile is
well-formed (schema, known benchmark ids, no duplicates, per-page count
ceiling) and renders the small advisory payload a Writer or Reviewer reads.
Whether a benchmark is *semantically* right for a page is a cognitive
judgment and is never computed here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from makewiki_skills.benchmarks.corpus import Corpus, CorpusError
from makewiki_skills.benchmarks.model import (
    REFERENCE_PROFILE_SCHEMA_VERSION,
    ReferenceEntry,
    ReferenceProfile,
    estimate_tokens,
)

#: Fixed advisory rules rendered at the top of every ReferenceProfile. They
#: encode the authority order: evidence > PageSpec > ReferenceProfile >
#: benchmark examples.
ADVISORY_RULES = (
    "These references are advisory documentation examples, NOT evidence "
    "about the target project. Borrow only information shape, section "
    "sequencing, explanation strategy, progressive disclosure, example "
    "placement, and lookup experience. Never copy source-product facts, "
    "terminology, API/config values, defaults, limits, or factual claims. "
    "The target PageSpec stays authoritative; a benchmark's categories "
    "describe the reference document, never the target page."
)


class ProfileError(Exception):
    """A mechanical ReferenceProfile defect."""


def load_reference_profile(path: Path) -> ReferenceProfile:
    """Parse a Selector-authored ReferenceProfile YAML file."""
    path = Path(path)
    if not path.is_file():
        raise ProfileError(f"reference profile not found: {path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ProfileError(f"invalid YAML in {path}: {exc}") from exc
    try:
        return ReferenceProfile.model_validate(raw)
    except Exception as exc:
        raise ProfileError(f"invalid reference profile in {path}: {exc}") from exc


def validate_reference_profile(
    profile: ReferenceProfile,
    corpus: Corpus,
    *,
    max_examples_per_page: int,
) -> list[str]:
    """Mechanical profile checks; returns human-readable problems."""
    problems: list[str] = []
    if not profile.page_id:
        problems.append("page_id must not be empty")
    seen: set[str] = set()
    for ref in profile.references:
        try:
            corpus.entry(ref.benchmark_id)
        except CorpusError:
            problems.append(
                f"{profile.page_id}: references unknown benchmark "
                f"{ref.benchmark_id!r}"
            )
            continue
        if ref.benchmark_id in seen:
            problems.append(
                f"{profile.page_id}: duplicate reference to {ref.benchmark_id!r}"
            )
        seen.add(ref.benchmark_id)
    if len(profile.references) > max_examples_per_page:
        problems.append(
            f"{profile.page_id}: {len(profile.references)} references exceed "
            f"benchmark.max_examples_per_page={max_examples_per_page}"
        )
    return problems


@dataclass(frozen=True)
class RenderedProfile:
    """A rendered ReferenceProfile plus its mechanical budget verdict."""

    page_id: str
    markdown: str
    est_tokens: int
    within_budget: bool
    downgraded: list[str] = field(default_factory=list)


def _full_block(corpus: Corpus, benchmark_id: str) -> str:
    benchmark = corpus.normalized[benchmark_id]
    lines = [benchmark.summary, ""]
    if benchmark.information_shape:
        lines.append("Information shape: " + " -> ".join(benchmark.information_shape))
    if benchmark.suitable_intents:
        lines.append("Suitable intents: " + ", ".join(benchmark.suitable_intents))
    if benchmark.strong_traits:
        lines.append("Strong traits: " + "; ".join(benchmark.strong_traits) + ".")
    if benchmark.anti_patterns:
        lines.append(
            "Anti-patterns to avoid: " + "; ".join(benchmark.anti_patterns) + "."
        )
    registry_entry = corpus.entry(benchmark_id)
    for pattern_id in registry_entry.pattern_ids:
        pattern = corpus.patterns.get(pattern_id)
        if pattern is None:
            continue
        lines.append("")
        lines.append(f"Pattern {pattern.id}: {pattern.description}")
        if pattern.suitable_when:
            lines.append("- suitable when: " + "; ".join(pattern.suitable_when))
        if pattern.good_traits:
            lines.append("- good traits: " + ", ".join(pattern.good_traits))
        if pattern.anti_patterns:
            lines.append("- avoid: " + "; ".join(pattern.anti_patterns))
    return "\n".join(lines).strip()


def _compact_block(corpus: Corpus, benchmark_id: str) -> str:
    benchmark = corpus.normalized[benchmark_id]
    if benchmark.information_shape:
        shape = " -> ".join(benchmark.information_shape)
    else:
        shape = "n/a"
    return f"Information shape: {shape}"


def _copy_ban(do_not_copy: list[str]) -> str:
    text = (
        "Do NOT copy: source-product facts, terminology, API/config values, "
        "defaults, limits, or factual claims."
    )
    if do_not_copy:
        text += " Explicitly excluded: " + "; ".join(do_not_copy) + "."
    return text


def render_reference_profile(
    profile: ReferenceProfile,
    corpus: Corpus,
    *,
    max_reference_tokens: int,
) -> RenderedProfile:
    """Render the advisory payload for a Writer or Reviewer.

    Every reference starts at the full tier (summary + shape + pattern
    cards); while the payload exceeds ``max_reference_tokens``, the most
    recently selected references are downgraded to the compact tier (shape
    + borrow + copy-ban only). A payload that cannot fit even fully compact
    reports ``within_budget=False`` — a mechanical finding the caller turns
    into a blocking error. Downgrading references never shrinks target
    evidence.
    """
    tiers = ["full"] * len(profile.references)

    def reference_lines(ref: ReferenceEntry, tier: str) -> list[str]:
        entry = corpus.entry(ref.benchmark_id)
        lines = [f"## {ref.benchmark_id} ({entry.provider} — {entry.title})", ""]
        if tier == "full":
            lines.append(_full_block(corpus, ref.benchmark_id))
        else:
            lines.append(_compact_block(corpus, ref.benchmark_id))
        if ref.relevance:
            lines.append("")
            lines.append("Why selected: " + "; ".join(ref.relevance))
        if ref.borrow:
            lines.append("Borrow (presentation only): " + "; ".join(ref.borrow))
        lines.append(_copy_ban(ref.do_not_copy))
        lines.append("")
        return lines

    def assemble(current: list[str]) -> str:
        parts: list[str] = [
            f"# ReferenceProfile — {profile.page_id}",
            "",
            f"> Schema {REFERENCE_PROFILE_SCHEMA_VERSION}.",
            "",
            ADVISORY_RULES,
            "",
        ]
        for ref, tier in zip(profile.references, current):
            parts.extend(reference_lines(ref, tier))
        return "\n".join(parts).strip() + "\n"

    while True:
        text = assemble(tiers)
        if estimate_tokens(text) <= max_reference_tokens:
            break
        full_slots = [i for i, t in enumerate(tiers) if t == "full"]
        if not full_slots:
            break
        tiers[full_slots[-1]] = "compact"

    text = assemble(tiers)
    return RenderedProfile(
        page_id=profile.page_id,
        markdown=text,
        est_tokens=estimate_tokens(text),
        within_budget=estimate_tokens(text) <= max_reference_tokens,
        downgraded=[
            ref.benchmark_id
            for ref, tier in zip(profile.references, tiers)
            if tier == "compact"
        ],
    )
