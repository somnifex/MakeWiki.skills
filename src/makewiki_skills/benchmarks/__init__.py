"""Benchmark Library: Python toolkit (mechanical plane only).

This package owns the mechanical half of the Benchmark Reference Layer:

* :mod:`model` — pydantic schemas for the corpus and ReferenceProfile.
* :mod:`corpus` — load/validate the four-layer corpus, digest it, and
  generate the compact stage-1 index.
* :mod:`profile` — ReferenceProfile parsing, mechanical validation, and
  compact rendering.
* :mod:`leakage` — mechanical candidate scan for benchmark-provider terms
  in generated docs (review input, never a verdict).
* :mod:`acquire` — licensing-gated fetch of benchmark source pages.

It deliberately contains NO semantic selection: choosing which benchmarks
help a page is a cognitive decision owned by the Benchmark Selector
subagent (``tasks/select-benchmarks.md``).
"""

from __future__ import annotations

from makewiki_skills.benchmarks.corpus import (
    INDEX_FILENAME,
    Corpus,
    CorpusError,
    build_index,
    load_corpus,
    validate_corpus,
    write_index,
)
from makewiki_skills.benchmarks.leakage import (
    LeakageHit,
    collect_leak_terms,
    scan_leakage,
)
from makewiki_skills.benchmarks.model import (
    REFERENCE_PROFILE_SCHEMA_VERSION,
    BenchmarkPattern,
    NormalizedBenchmark,
    PatternRef,
    ReferenceEntry,
    ReferenceProfile,
    Registry,
    RegistryEntry,
    SourceRef,
    estimate_tokens,
)
from makewiki_skills.benchmarks.profile import (
    ADVISORY_RULES,
    ProfileError,
    RenderedProfile,
    load_reference_profile,
    render_reference_profile,
    validate_reference_profile,
)

__all__ = [
    "INDEX_FILENAME",
    "ADVISORY_RULES",
    "BenchmarkPattern",
    "Corpus",
    "CorpusError",
    "LeakageHit",
    "NormalizedBenchmark",
    "PatternRef",
    "ProfileError",
    "REFERENCE_PROFILE_SCHEMA_VERSION",
    "ReferenceEntry",
    "ReferenceProfile",
    "Registry",
    "RegistryEntry",
    "RenderedProfile",
    "SourceRef",
    "build_index",
    "collect_leak_terms",
    "estimate_tokens",
    "load_corpus",
    "load_reference_profile",
    "render_reference_profile",
    "scan_leakage",
    "validate_corpus",
    "validate_reference_profile",
    "write_index",
]
