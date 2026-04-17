"""Filesystem-backed run and state management for the MakeWiki flow."""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from makewiki_skills.config import MakeWikiConfig
from makewiki_skills.orchestration.models import (
    ChildSkillReceipt,
    EvidenceIndex,
    EvidenceShard,
    PagePlan,
    RunJob,
    RunState,
    SemanticModelIndex,
)
from makewiki_skills.scanner.evidence_collector import CollectedEvidence
from makewiki_skills.scanner.project_detector import ProjectDetectionResult
from makewiki_skills.toolkit.evidence import EvidenceFact

TModel = TypeVar("TModel", bound=BaseModel)

_JOB_KIND_ORDER = {
    "llm-scan": 0,
    "surface-card": 1,
    "semantic-root": 2,
    "module-brief": 3,
    "workflow-brief": 4,
    "page-plan": 5,
    "page-write": 6,
    "page-repair": 7,
}


@dataclass(frozen=True)
class RunLayout:
    """Resolved paths for a single run."""

    project_root: Path
    run_id: str
    state_root: Path
    run_root: Path
    evidence_dir: Path
    evidence_shards_dir: Path
    surface_cards_dir: Path
    briefs_dir: Path
    module_briefs_dir: Path
    workflow_briefs_dir: Path
    page_plans_dir: Path
    page_artifacts_dir: Path
    receipts_dir: Path
    traces_dir: Path
    state_file: Path
    evidence_index_file: Path
    project_brief_file: Path
    semantic_index_file: Path

    @classmethod
    def create(cls, project_root: Path, state_dir_name: str, run_id: str) -> "RunLayout":
        state_root = project_root / state_dir_name
        run_root = state_root / "runs" / run_id
        briefs_dir = run_root / "briefs"
        return cls(
            project_root=project_root,
            run_id=run_id,
            state_root=state_root,
            run_root=run_root,
            evidence_dir=run_root / "evidence",
            evidence_shards_dir=run_root / "evidence" / "shards",
            surface_cards_dir=run_root / "surface-cards",
            briefs_dir=briefs_dir,
            module_briefs_dir=briefs_dir / "modules",
            workflow_briefs_dir=briefs_dir / "workflows",
            page_plans_dir=run_root / "page-plans",
            page_artifacts_dir=run_root / "page-artifacts",
            receipts_dir=run_root / "receipts",
            traces_dir=run_root / "traces",
            state_file=run_root / "state.json",
            evidence_index_file=run_root / "evidence.index.json",
            project_brief_file=run_root / "project-brief.json",
            semantic_index_file=run_root / "semantic-model.index.json",
        )

    def ensure_dirs(self) -> None:
        for path in (
            self.evidence_dir,
            self.evidence_shards_dir,
            self.surface_cards_dir,
            self.module_briefs_dir,
            self.workflow_briefs_dir,
            self.page_plans_dir,
            self.page_artifacts_dir,
            self.receipts_dir,
            self.traces_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def rel_to_project(self, path: Path) -> str:
        return str(path.relative_to(self.project_root)).replace("\\", "/")


@dataclass(frozen=True)
class PlannedArtifactFile:
    """A file payload that can be materialized by the agent with Write/Edit."""

    target: Path
    relative_path: str
    content: str


class RunStore:
    """Prepare, resume, and refresh MakeWiki runs."""

    def __init__(self, config: MakeWikiConfig) -> None:
        self._config = config
        self._project_root = config.target_dir.resolve()
        self._state_root = self._project_root / config.orchestration.state_dir

    def latest_layout(self) -> RunLayout | None:
        runs_dir = self._state_root / "runs"
        if not runs_dir.is_dir():
            return None
        run_dirs = sorted((path for path in runs_dir.iterdir() if path.is_dir()), reverse=True)
        if not run_dirs:
            return None
        return RunLayout.create(
            self._project_root,
            self._config.orchestration.state_dir,
            run_dirs[0].name,
        )

    def load_state(self, layout: RunLayout) -> RunState:
        return self._load_model(layout.state_file, RunState)

    def load_evidence_index(self, layout: RunLayout) -> EvidenceIndex:
        return self._load_model(layout.evidence_index_file, EvidenceIndex)

    def load_semantic_index(self, layout: RunLayout) -> SemanticModelIndex | None:
        if not layout.semantic_index_file.is_file():
            return None
        return self._load_model(layout.semantic_index_file, SemanticModelIndex)

    def load_page_plans(self, layout: RunLayout) -> list[PagePlan]:
        plans: list[PagePlan] = []
        for plan_file in sorted(layout.page_plans_dir.glob("*.json")):
            plans.append(self._load_model(plan_file, PagePlan))
        return plans

    def prepare_run(
        self,
        detection: ProjectDetectionResult,
        collected: CollectedEvidence,
        persist: bool = True,
    ) -> tuple[RunLayout, RunState, EvidenceIndex, bool, list[PlannedArtifactFile]]:
        resumed = False
        latest = self.latest_layout()
        if (
            self._config.orchestration.resume
            and latest is not None
            and latest.state_file.is_file()
            and self._run_is_incomplete(self.load_state(latest))
            and self._resume_matches_config(self.load_state(latest))
        ):
            resumed = True
            return latest, self.load_state(latest), self.load_evidence_index(latest), resumed, []

        run_id = self._new_run_id()
        layout = RunLayout.create(self._project_root, self._config.orchestration.state_dir, run_id)
        if persist:
            layout.ensure_dirs()

        evidence_index, planned_files = self._prepare_evidence_artifacts(
            layout,
            detection,
            collected,
            persist=persist,
        )
        state = RunState(
            run_id=run_id,
            project_root=str(self._project_root),
            output_dir=self._config.output_dir,
            languages=list(self._config.languages),
            default_language=self._config.default_language,
            max_attempts=self._config.orchestration.max_attempts,
            jobs=self._seed_initial_jobs(evidence_index, layout),
        )
        if persist:
            self._write_model(layout.state_file, state)
        else:
            planned_files.append(self._planned_model(layout.state_file, state))
        return layout, state, evidence_index, resumed, planned_files

    def refresh_state(
        self,
        layout: RunLayout,
        languages: list[str] | None = None,
        persist: bool = True,
    ) -> tuple[RunState, SemanticModelIndex | None]:
        state = self.load_state(layout)
        semantic_index = self.load_semantic_index(layout)
        planned_languages = state.languages or languages or self._config.languages

        if semantic_index is not None:
            state.jobs = self._merge_semantic_jobs(
                state.jobs,
                semantic_index,
                layout,
                planned_languages,
            )

        latest_receipts = self._latest_receipts(layout)
        jobs_by_id = {job.job_id: job for job in state.jobs}
        for receipt in latest_receipts:
            job = jobs_by_id.get(receipt.job_id)
            if job is None:
                continue
            job.attempt = receipt.attempt
            job.artifact_path = receipt.artifact_path
            job.trace_path = receipt.trace_path
            job.error_code = receipt.error_code
            job.receipt_path = self._receipt_file_for(layout, receipt)
            if receipt.status == "done" and self._artifact_exists(receipt.artifact_path):
                job.status = "done"
            elif receipt.status == "done":
                job.status = "stale"
            else:
                job.status = "failed"

        for job in state.jobs:
            if job.status == "done" and job.artifact_path and not self._artifact_exists(job.artifact_path):
                job.status = "stale"
            if job.artifact_path is None:
                expected = self.expected_artifact_path(job, layout)
                if expected is not None:
                    job.artifact_path = expected

        state.updated_at = datetime.now(timezone.utc).isoformat()
        state.jobs = sorted(state.jobs, key=self._job_sort_key)
        if persist:
            self._write_model(layout.state_file, state)
        return state, semantic_index

    def scan_job_status(self, state: RunState) -> str | None:
        job = next((job for job in state.jobs if job.kind == "llm-scan"), None)
        return job.status if job is not None else None

    def ready_jobs(self, state: RunState, limit: int = 20) -> list[RunJob]:
        jobs_by_id = {job.job_id: job for job in state.jobs}
        ready: list[RunJob] = []
        for job in state.jobs:
            if job.status not in {"pending", "stale", "failed"}:
                continue
            if job.attempt >= state.max_attempts and job.status == "failed":
                continue
            if all(jobs_by_id.get(dep) is not None and jobs_by_id[dep].status == "done" for dep in job.depends_on):
                ready.append(job)
        return ready[:limit]

    def expected_artifact_path(self, job: RunJob, layout: RunLayout) -> str | None:
        if job.kind == "llm-scan":
            return layout.rel_to_project(layout.evidence_index_file)
        if job.kind == "surface-card" and job.source_ref:
            return layout.rel_to_project(layout.surface_cards_dir / f"{job.source_ref}.json")
        if job.kind == "semantic-root":
            return layout.rel_to_project(layout.semantic_index_file)
        if job.kind == "module-brief" and job.module_id:
            return layout.rel_to_project(layout.module_briefs_dir / f"{job.module_id}.json")
        if job.kind == "workflow-brief" and job.workflow_id:
            return layout.rel_to_project(layout.workflow_briefs_dir / f"{job.workflow_id}.json")
        if job.kind == "page-plan" and job.page_id:
            return layout.rel_to_project(layout.page_plans_dir / f"{job.page_id}.json")
        if job.kind in {"page-write", "page-repair"} and job.page_id and job.language_code:
            return layout.rel_to_project(
                layout.page_artifacts_dir / job.language_code / f"{job.page_id}.md"
            )
        return None

    def _prepare_evidence_artifacts(
        self,
        layout: RunLayout,
        detection: ProjectDetectionResult,
        collected: CollectedEvidence,
        persist: bool,
    ) -> tuple[EvidenceIndex, list[PlannedArtifactFile]]:
        grouped: dict[str, list[EvidenceFact]] = {}
        for fact in collected.facts:
            source_path = fact.evidence[0].source_path if fact.evidence else "misc/unknown"
            grouped.setdefault(source_path, []).append(fact)

        planned_files: list[PlannedArtifactFile] = []
        shards: list[EvidenceShard] = []
        for source_path, facts in sorted(grouped.items()):
            shard_id = self._make_shard_id(source_path)
            artifact_path = layout.evidence_shards_dir / f"{shard_id}.json"
            fact_types = sorted({fact.fact_type for fact in facts})
            shard = EvidenceShard(
                shard_id=shard_id,
                source_path=source_path,
                artifact_path=layout.rel_to_project(artifact_path),
                fact_types=fact_types,
                facts=facts,
            )
            if persist:
                self._write_model(artifact_path, shard)
            else:
                planned_files.append(self._planned_model(artifact_path, shard))
            shards.append(shard)

        evidence_index = EvidenceIndex(
            run_id=layout.run_id,
            project_root=str(self._project_root),
            project_name=detection.project_name,
            project_type=detection.project_type.value,
            detection_confidence=detection.confidence,
            artifact_dir=layout.rel_to_project(layout.evidence_dir),
            collection_mode=collected.collection_mode,
            fallback_reason=collected.fallback_reason,
            files_read=collected.raw_files_read,
            fact_summary=self._summarize_facts(collected.facts),
            shards=shards,
        )
        if persist:
            self._write_model(layout.evidence_index_file, evidence_index)
        else:
            planned_files.append(self._planned_model(layout.evidence_index_file, evidence_index))
        return evidence_index, planned_files

    def _seed_initial_jobs(self, evidence_index: EvidenceIndex, layout: RunLayout) -> list[RunJob]:
        if evidence_index.collection_mode == "llm-fallback":
            jobs = [
                RunJob(
                    job_id="llm-scan",
                    kind="llm-scan",
                    artifact_path=layout.rel_to_project(layout.evidence_index_file),
                ),
                RunJob(
                    job_id="semantic-root",
                    kind="semantic-root",
                    depends_on=["llm-scan"],
                    artifact_path=layout.rel_to_project(layout.semantic_index_file),
                ),
            ]
            return sorted(jobs, key=self._job_sort_key)

        jobs = [
            RunJob(
                job_id=f"surface-card:{shard.shard_id}",
                kind="surface-card",
                source_ref=shard.shard_id,
                artifact_path=layout.rel_to_project(layout.surface_cards_dir / f"{shard.shard_id}.json"),
            )
            for shard in evidence_index.shards
        ]
        jobs.append(
            RunJob(
                job_id="semantic-root",
                kind="semantic-root",
                depends_on=[job.job_id for job in jobs],
                artifact_path=layout.rel_to_project(layout.semantic_index_file),
            )
        )
        return sorted(jobs, key=self._job_sort_key)

    def _merge_semantic_jobs(
        self,
        jobs: list[RunJob],
        semantic_index: SemanticModelIndex,
        layout: RunLayout,
        languages: list[str],
    ) -> list[RunJob]:
        existing = {job.job_id: job for job in jobs}

        def ensure(job: RunJob) -> None:
            if job.job_id in existing:
                return
            existing[job.job_id] = job

        ensure(
            RunJob(
                job_id="semantic-root",
                kind="semantic-root",
                artifact_path=layout.rel_to_project(layout.semantic_index_file),
            )
        )

        for module in semantic_index.modules:
            ensure(
                RunJob(
                    job_id=f"module-brief:{module.id}",
                    kind="module-brief",
                    module_id=module.id,
                    depends_on=["semantic-root"],
                    artifact_path=layout.rel_to_project(layout.module_briefs_dir / f"{module.id}.json"),
                )
            )

        module_job_ids = {module.id: f"module-brief:{module.id}" for module in semantic_index.modules}
        for workflow in semantic_index.workflows:
            depends_on = ["semantic-root"]
            depends_on.extend(
                module_job_ids[module_id]
                for module_id in workflow.module_ids
                if module_id in module_job_ids
            )
            ensure(
                RunJob(
                    job_id=f"workflow-brief:{workflow.id}",
                    kind="workflow-brief",
                    workflow_id=workflow.id,
                    depends_on=depends_on,
                    artifact_path=layout.rel_to_project(
                        layout.workflow_briefs_dir / f"{workflow.id}.json"
                    ),
                )
            )

        workflow_job_ids = {
            workflow.id: f"workflow-brief:{workflow.id}" for workflow in semantic_index.workflows
        }
        for page in semantic_index.pages:
            depends_on = ["semantic-root"]
            if page.scope == "module":
                depends_on.extend(
                    module_job_ids[target_id]
                    for target_id in page.target_ids
                    if target_id in module_job_ids
                )
            if page.scope == "workflow":
                depends_on.extend(
                    workflow_job_ids[target_id]
                    for target_id in page.target_ids
                    if target_id in workflow_job_ids
                )
            ensure(
                RunJob(
                    job_id=f"page-plan:{page.id}",
                    kind="page-plan",
                    page_id=page.id,
                    depends_on=depends_on,
                    artifact_path=layout.rel_to_project(layout.page_plans_dir / f"{page.id}.json"),
                )
            )
            for language in languages:
                ensure(
                    RunJob(
                        job_id=f"page-write:{page.id}:{language}",
                        kind="page-write",
                        page_id=page.id,
                        language_code=language,
                        depends_on=[f"page-plan:{page.id}"],
                        artifact_path=layout.rel_to_project(
                            layout.page_artifacts_dir / language / f"{page.id}.md"
                        ),
                    )
                )

        return sorted(existing.values(), key=self._job_sort_key)

    def _latest_receipts(self, layout: RunLayout) -> list[ChildSkillReceipt]:
        latest: dict[str, ChildSkillReceipt] = {}
        for receipt_file in sorted(layout.receipts_dir.glob("*.json")):
            receipt = self._load_model(receipt_file, ChildSkillReceipt)
            current = latest.get(receipt.job_id)
            if current is None or receipt.attempt >= current.attempt:
                latest[receipt.job_id] = receipt
        return list(latest.values())

    def _receipt_file_for(self, layout: RunLayout, receipt: ChildSkillReceipt) -> str:
        candidate = layout.receipts_dir / f"{receipt.job_id.replace(':', '__')}.{receipt.attempt}.json"
        return layout.rel_to_project(candidate)

    def _artifact_exists(self, relative_path: str) -> bool:
        return (self._project_root / relative_path).exists()

    def _run_is_incomplete(self, state: RunState) -> bool:
        return any(job.status != "done" for job in state.jobs)

    def _resume_matches_config(self, state: RunState) -> bool:
        if state.output_dir != self._config.output_dir:
            return False
        if state.default_language != self._config.default_language:
            return False
        if state.languages and state.languages != self._config.languages:
            return False
        return True

    def _new_run_id(self) -> str:
        prefix = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"{prefix}-{uuid.uuid4().hex[:6]}"

    @staticmethod
    def _make_shard_id(source_path: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", source_path.lower()).strip("-") or "evidence"
        digest = hashlib.sha1(source_path.encode("utf-8")).hexdigest()[:8]
        return f"{slug[:48]}-{digest}"

    @staticmethod
    def _summarize_facts(facts: list[EvidenceFact]) -> dict[str, int]:
        summary: dict[str, int] = {}
        for fact in facts:
            summary[fact.fact_type] = summary.get(fact.fact_type, 0) + 1
        return summary

    @staticmethod
    def _job_sort_key(job: RunJob) -> tuple[int, str, str, str]:
        return (
            _JOB_KIND_ORDER.get(job.kind, 999),
            job.module_id or "",
            job.workflow_id or "",
            job.job_id,
        )

    @staticmethod
    def _load_model(path: Path, model_type: type[TModel]) -> TModel:
        return model_type.model_validate_json(path.read_text(encoding="utf-8"))

    @staticmethod
    def _write_model(path: Path, model: BaseModel) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(model.model_dump_json(indent=2), encoding="utf-8")

    def _planned_model(self, path: Path, model: BaseModel) -> PlannedArtifactFile:
        return PlannedArtifactFile(
            target=path,
            relative_path=self._project_relative(path),
            content=model.model_dump_json(indent=2),
        )

    def _project_relative(self, path: Path) -> str:
        return str(path.relative_to(self._project_root)).replace("\\", "/")
