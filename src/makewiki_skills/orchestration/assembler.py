"""Assemble final documentation from language-specific page artifacts."""

from __future__ import annotations

import re
from collections import OrderedDict

from makewiki_skills.config import MakeWikiConfig
from makewiki_skills.documents import GeneratedDocument
from makewiki_skills.orchestration.store import RunLayout, RunStore

_LOW_CONFIDENCE_MARKER_RE = re.compile(r"\{\{LOW_CONFIDENCE:([^}]+)\}\}")


class PageArtifactAssembler:
    """Load page plans and markdown artifacts, then build output documents."""

    def __init__(self, config: MakeWikiConfig) -> None:
        self._config = config

    def assemble(
        self,
        layout: RunLayout,
        store: RunStore,
    ) -> tuple[dict[str, list[GeneratedDocument]], list[str]]:
        documents: dict[str, list[GeneratedDocument]] = {}
        warnings: list[str] = []
        state = store.load_state(layout)
        jobs_by_id = {job.job_id: job for job in state.jobs}
        page_plans = sorted(store.load_page_plans(layout), key=lambda plan: plan.output_path)

        for language in self._config.languages:
            language_docs: list[GeneratedDocument] = []
            for plan in page_plans:
                plan_job = jobs_by_id.get(f"page-plan:{plan.page_id}")
                if plan_job is None or plan_job.status != "done":
                    warnings.append(
                        f"Skipping page plan {plan.page_id} for {language}: job is not done"
                    )
                    continue

                page_job = jobs_by_id.get(f"page-write:{plan.page_id}:{language}")
                if page_job is None or page_job.status != "done":
                    warnings.append(
                        f"Skipping page artifact for {language}:{plan.page_id}: page-write job is not done"
                    )
                    continue

                artifact_file = layout.page_artifacts_dir / language / f"{plan.page_id}.md"
                if not artifact_file.is_file():
                    warnings.append(
                        f"Missing page artifact for {language}:{plan.page_id} at {artifact_file}"
                    )
                    continue
                content = artifact_file.read_text(encoding="utf-8", errors="replace")
                content = self._normalize_low_confidence_markers(content)
                language_docs.append(
                    GeneratedDocument(
                        filename=_filename_for_language(
                            plan.output_path,
                            language,
                            self._config.default_language,
                        ),
                        base_name=plan.output_path,
                        language_code=language,
                        content=content,
                        word_count=len(content.split()),
                    )
                )
            documents[language] = language_docs

        return documents, warnings

    def _normalize_low_confidence_markers(self, content: str) -> str:
        if not self._config.render.annotate_low_confidence_footnotes:
            return _LOW_CONFIDENCE_MARKER_RE.sub("", content).strip() + "\n"

        note_ids: "OrderedDict[str, str]" = OrderedDict()

        def replace_marker(match: re.Match[str]) -> str:
            source_path = match.group(1).strip()
            if source_path not in note_ids:
                note_ids[source_path] = f"low-{len(note_ids) + 1}"
            return f"[^{note_ids[source_path]}]"

        normalized = _LOW_CONFIDENCE_MARKER_RE.sub(replace_marker, content)
        if note_ids:
            footnotes = [
                f"[^{note_id}]: Inferred by fallback scan from `{source_path}`."
                for source_path, note_id in note_ids.items()
            ]
            normalized = normalized.rstrip() + "\n\n" + "\n".join(footnotes) + "\n"
        else:
            normalized = normalized.rstrip() + "\n"
        return normalized


def _filename_for_language(base_name: str, language: str, default_language: str) -> str:
    if language == default_language:
        return base_name
    stem, dot, suffix = base_name.rpartition(".")
    if dot:
        return f"{stem}.{language}.{suffix}"
    return f"{base_name}.{language}"
