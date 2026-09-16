"""Pydantic models for the Benchmark Library corpus and ReferenceProfile.

Mechanical containers only: schema, ids, cross-links, budgets, rendering.
None of these models decides which benchmark fits a page — that judgment
belongs to the LLM Benchmark Selector (cognitive plane,
`tasks/select-benchmarks.md`).

The four corpus layers stay distinguishable on disk:

```text
<corpus>/
├── registry.yaml            # curated metadata layer (ids, pointers, licensing)
├── normalized/<id>.yaml     # structural summaries of excellent pages
├── patterns/<id>.yaml       # distilled, source-agnostic documentation patterns
├── index/benchmark-index.json  # generated compact index (stage-1 ranking input)
└── sources/<provider>/      # raw fetched pages (local cache; licensing-aware)
```
"""

from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

#: Strict models: a typo'd key in a corpus YAML fails loudly at load time.
_STRICT = ConfigDict(extra="forbid")

#: Provenance marker for entries authored as structural summaries without a
#: fetched raw source. Redistributing a provider's prose requires a fetched,
#: license-cleared source (see `benchmarks/acquire.py`).
VERIFICATION_UNVERIFIED = "unverified-structural-summary"

REFERENCE_PROFILE_SCHEMA_VERSION = 1


def estimate_tokens(text: str) -> int:
    """Cheap deterministic token estimate (~4 characters per token)."""
    return math.ceil(len(text) / 4)


def _clean_list(values: list[str] | None) -> list[str]:
    """Drop empty/whitespace entries and duplicates, preserving order."""
    seen: set[str] = set()
    out: list[str] = []
    for value in values or []:
        item = value.strip()
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


class SourceRef(BaseModel):
    """Where a benchmark page came from (provenance, not content)."""

    model_config = _STRICT

    provider: str
    title: str
    url: str


class BenchmarkPattern(BaseModel):
    """A distilled documentation pattern, source-agnostic by construction.

    A pattern may be informed by several benchmarks across different
    categories; `source_examples` are provenance pointers, never a hard
    category binding (cross-category transfer is explicitly allowed).
    """

    model_config = _STRICT

    id: str
    description: str
    suitable_when: list[str] = Field(default_factory=list)
    information_shape: list[str] = Field(default_factory=list)
    good_traits: list[str] = Field(default_factory=list)
    anti_patterns: list[str] = Field(default_factory=list)
    source_examples: list[str] = Field(default_factory=list)

    def render_text(self) -> str:
        parts = [f"Pattern: {self.id}", self.description]
        if self.suitable_when:
            parts.append("Suitable when: " + "; ".join(self.suitable_when) + ".")
        if self.information_shape:
            parts.append("Shape: " + " -> ".join(self.information_shape))
        if self.good_traits:
            parts.append("Good traits: " + ", ".join(self.good_traits) + ".")
        if self.anti_patterns:
            parts.append("Avoid: " + "; ".join(self.anti_patterns) + ".")
        return "\n".join(parts)


class NormalizedBenchmark(BaseModel):
    """Structural summary of one excellent external page.

    ``observed_archetypes`` describes what THIS benchmark demonstrates. It is
    a retrieval/similarity hint only — never a target-page classification and
    never a generation constraint (cross-category transfer is allowed).
    """

    model_config = _STRICT

    id: str
    source: SourceRef
    summary: str
    observed_archetypes: list[str] = Field(default_factory=list)
    suitable_intents: list[str] = Field(default_factory=list)
    information_shape: list[str] = Field(default_factory=list)
    strong_traits: list[str] = Field(default_factory=list)
    anti_patterns: list[str] = Field(default_factory=list)
    useful_for: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    pattern_ids: list[str] = Field(default_factory=list)
    content_path: str | None = None
    retrieved_at: str | None = None
    license_or_usage_note: str | None = None
    #: Provenance honesty: seeded entries ship as
    #: ``unverified-structural-summary`` until a fetch backs them.
    verification: str = VERIFICATION_UNVERIFIED

    def render_text(self) -> str:
        lines = [
            f"Benchmark: {self.id} ({self.source.provider} — {self.source.title})",
            self.summary,
        ]
        if self.information_shape:
            lines.append("Information shape: " + " -> ".join(self.information_shape))
        if self.suitable_intents:
            lines.append("Suitable intents: " + ", ".join(self.suitable_intents))
        if self.strong_traits:
            lines.append("Strong traits: " + "; ".join(self.strong_traits))
        if self.anti_patterns:
            lines.append("Anti-patterns: " + "; ".join(self.anti_patterns))
        return "\n".join(lines)


class RegistryEntry(BaseModel):
    """One registry row: metadata + pointers into the other corpus layers."""

    model_config = _STRICT

    id: str
    provider: str
    title: str
    source_url: str = ""
    normalized_path: str
    pattern_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    quality_notes: list[str] = Field(default_factory=list)
    #: ``metadata-only`` (default): never fetch or store full prose — the
    #: licensing-safe default. ``full``: the page may be fetched into
    #: ``sources/`` under its stated terms.
    acquire: Literal["metadata-only", "full"] = "metadata-only"
    license_or_usage_note: str | None = None
    #: Extra provider names for the mechanical leakage scan.
    leak_terms: list[str] = Field(default_factory=list)


class PatternRef(BaseModel):
    """Registry pointer to one pattern card file."""

    model_config = _STRICT

    id: str
    path: str


class Registry(BaseModel):
    """The ``registry.yaml`` metadata layer."""

    model_config = _STRICT

    benchmarks: list[RegistryEntry] = Field(default_factory=list)
    patterns: list[PatternRef] = Field(default_factory=list)


class ReferenceEntry(BaseModel):
    """One selected benchmark inside a ReferenceProfile."""

    model_config = _STRICT

    benchmark_id: str
    relevance: list[str] = Field(default_factory=list)
    borrow: list[str] = Field(default_factory=list)
    do_not_copy: list[str] = Field(default_factory=list)


class ReferenceProfile(BaseModel):
    """The compact advisory selection handed to a Writer or Reviewer.

    Authored by the Benchmark Selector subagent; mechanically validated by
    ``verify-reference-profile``. Never a fact source for the target page.
    """

    model_config = _STRICT

    page_id: str
    language: str | None = None
    selected_by: str = "benchmark-selector"
    references: list[ReferenceEntry] = Field(default_factory=list)
    notes: str | None = None
