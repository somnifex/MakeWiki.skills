"""Licensing-gated acquisition of benchmark source pages.

Mechanical plane: fetch, hash, and cache raw pages under
``<corpus>/sources/<provider>/`` with a sidecar metadata file. The registry
marks entries ``metadata-only`` by default; acquiring full prose is refused
unless the entry opts in with ``acquire: full`` and a recorded license or
usage note. Stdlib :mod:`urllib.request` only.
"""

from __future__ import annotations

import hashlib
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from makewiki_skills.benchmarks.corpus import (
    SOURCES_DIRNAME,
    CorpusError,
    load_corpus,
)

_USER_AGENT = (
    "MakeWiki.skills-benchmark-acquire/3.2 "
    "(+https://github.com/somnifex/MakeWiki.skills)"
)


@dataclass(frozen=True)
class AcquireResult:
    """Outcome of one acquisition attempt."""

    benchmark_id: str
    url: str
    status: str  # "written" | "exists" | "refused-metadata-only" | "error"
    output_path: str | None
    detail: str


def fetch_url(url: str, timeout: float) -> bytes:
    """Fetch raw bytes over HTTP(S). Isolated for test substitution."""
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload: bytes = response.read()
    return payload


def acquire_benchmarks(
    corpus_dir: Path,
    benchmark_ids: list[str],
    *,
    timeout: float = 30.0,
    force: bool = False,
) -> list[AcquireResult]:
    """Fetch source pages for ``benchmark_ids`` into the sources/ cache.

    Entries the registry marks ``metadata-only`` are ALWAYS refused —
    ``force`` only re-fetches pages whose entry is already ``acquire:
    full``. Unlocking a fetch is a curation decision made in the registry
    (flip the entry to ``acquire: full`` and record a license or usage
    note), so the licensing posture stays auditable in version control
    rather than bypassable from the command line.
    """
    corpus = load_corpus(Path(corpus_dir))
    results: list[AcquireResult] = []
    for benchmark_id in benchmark_ids:
        try:
            entry = corpus.entry(benchmark_id)
        except CorpusError as exc:
            results.append(
                AcquireResult(
                    benchmark_id=benchmark_id,
                    url="",
                    status="error",
                    output_path=None,
                    detail=str(exc),
                )
            )
            continue
        url = entry.source_url
        if entry.acquire != "full":
            results.append(
                AcquireResult(
                    benchmark_id=benchmark_id,
                    url=url,
                    status="refused-metadata-only",
                    output_path=None,
                    detail=(
                        "registry marks this entry metadata-only; full fetch "
                        "requires acquire: full plus a license/usage note"
                    ),
                )
            )
            continue
        dest_dir = corpus.root / SOURCES_DIRNAME / entry.provider
        dest = dest_dir / f"{benchmark_id}.raw"
        meta_path = dest_dir / f"{benchmark_id}.meta.yaml"
        if dest.exists() and not force:
            results.append(
                AcquireResult(
                    benchmark_id=benchmark_id,
                    url=url,
                    status="exists",
                    output_path=dest.relative_to(corpus.root).as_posix(),
                    detail="already fetched; pass force=True to re-fetch",
                )
            )
            continue
        try:
            payload = fetch_url(url, timeout)
        except Exception as exc:  # urllib raises a wide family of errors
            results.append(
                AcquireResult(
                    benchmark_id=benchmark_id,
                    url=url,
                    status="error",
                    output_path=None,
                    detail=f"{type(exc).__name__}: {exc}",
                )
            )
            continue
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(payload)
        meta = {
            "id": benchmark_id,
            "provider": entry.provider,
            "title": entry.title,
            "url": url,
            "retrieved_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload),
            "license_or_usage_note": entry.license_or_usage_note,
        }
        meta_path.write_text(
            yaml.safe_dump(meta, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        results.append(
            AcquireResult(
                benchmark_id=benchmark_id,
                url=url,
                status="written",
                output_path=dest.relative_to(corpus.root).as_posix(),
                detail="fetched; sidecar metadata written",
            )
        )
    return results
