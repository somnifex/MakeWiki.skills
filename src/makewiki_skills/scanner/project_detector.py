"""Project type detection using file-indicator scoring."""

from __future__ import annotations

import json
import tomllib
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class ProjectType(str, Enum):
    PYTHON_CLI = "python-cli"
    PYTHON_LIBRARY = "python-library"
    PYTHON_SERVICE = "python-service"
    NODE_CLI = "node-cli"
    NODE_REACT = "node-react"
    NODE_LIBRARY = "node-library"
    RUST_CLI = "rust-cli"
    GO_CLI = "go-cli"
    GENERIC = "generic"


class DetectionRule(BaseModel):
    """A rule that contributes score when its indicators are found."""

    project_type: ProjectType
    indicators: list[str]
    weight: int = 10


class ProjectDetectionResult(BaseModel):
    project_type: ProjectType
    confidence: float = 0.0
    indicators_found: list[str] = Field(default_factory=list)
    project_name: str = ""
    project_dir: str = ""


class ScanTimeEstimate(BaseModel):
    """Estimated scan time for different modes."""

    total_files: int
    source_files: int
    doc_files: int
    estimated_quick_seconds: int
    estimated_standard_seconds: int
    estimated_deep_seconds: int
    recommended_mode: str  # "quick" | "standard" | "deep"


DEFAULT_RULES: list[DetectionRule] = [
    DetectionRule(project_type=ProjectType.PYTHON_CLI, indicators=["pyproject.toml"], weight=8),
    DetectionRule(project_type=ProjectType.PYTHON_CLI, indicators=["setup.py"], weight=6),
    DetectionRule(project_type=ProjectType.PYTHON_CLI, indicators=["setup.cfg"], weight=5),
    DetectionRule(project_type=ProjectType.PYTHON_LIBRARY, indicators=["pyproject.toml", "src/"], weight=7),
    DetectionRule(project_type=ProjectType.PYTHON_SERVICE, indicators=["Dockerfile", "requirements.txt"], weight=8),
    DetectionRule(project_type=ProjectType.PYTHON_SERVICE, indicators=["manage.py"], weight=12),
    DetectionRule(project_type=ProjectType.NODE_REACT, indicators=["package.json", "src/App.tsx"], weight=15),
    DetectionRule(project_type=ProjectType.NODE_REACT, indicators=["package.json", "src/App.jsx"], weight=15),
    DetectionRule(project_type=ProjectType.NODE_REACT, indicators=["package.json", "src/App.js"], weight=12),
    DetectionRule(project_type=ProjectType.NODE_CLI, indicators=["package.json", "bin/"], weight=10),
    DetectionRule(project_type=ProjectType.NODE_LIBRARY, indicators=["package.json", "index.js"], weight=6),
    DetectionRule(project_type=ProjectType.NODE_LIBRARY, indicators=["package.json"], weight=4),
    DetectionRule(project_type=ProjectType.RUST_CLI, indicators=["Cargo.toml", "src/main.rs"], weight=15),
    DetectionRule(project_type=ProjectType.GO_CLI, indicators=["go.mod", "main.go"], weight=15),
]


class ProjectDetector:
    """Score-based project type detector."""

    def __init__(self, rules: list[DetectionRule] | None = None) -> None:
        self._rules = rules or DEFAULT_RULES

    def detect(self, project_dir: Path) -> ProjectDetectionResult:
        root = Path(project_dir).resolve()
        scores: dict[ProjectType, int] = {}
        indicators_hit: dict[ProjectType, list[str]] = {}

        for rule in self._rules:
            all_found = True
            for indicator in rule.indicators:
                if not (root / indicator).exists():
                    all_found = False
                    break
            if all_found:
                scores[rule.project_type] = scores.get(rule.project_type, 0) + rule.weight
                indicators_hit.setdefault(rule.project_type, []).extend(rule.indicators)

        if not scores:
            return ProjectDetectionResult(
                project_type=ProjectType.GENERIC,
                confidence=0.3,
                project_name=root.name,
                project_dir=str(root),
            )

        best_type = max(scores, key=scores.__getitem__)
        max_possible = sum(rule.weight for rule in self._rules if rule.project_type == best_type)
        confidence = min(scores[best_type] / max(max_possible, 1), 1.0)

        return ProjectDetectionResult(
            project_type=best_type,
            confidence=round(confidence, 2),
            indicators_found=sorted(set(indicators_hit.get(best_type, []))),
            project_name=self._detect_name(root),
            project_dir=str(root),
        )

    def _detect_name(self, root: Path) -> str:
        pyproject = root / "pyproject.toml"
        if pyproject.is_file():
            try:
                data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
                project_data = data.get("project")
                if isinstance(project_data, dict):
                    name = project_data.get("name")
                    if isinstance(name, str):
                        return name
            except Exception:
                pass

        package_json = root / "package.json"
        if package_json.is_file():
            try:
                data = json.loads(package_json.read_text(encoding="utf-8"))
                name = data.get("name")
                if isinstance(name, str):
                    return name
            except Exception:
                pass

        return root.name

    def estimate_scan_time(self, project_dir: Path) -> ScanTimeEstimate:
        """Estimate scan time based on project size."""
        root = Path(project_dir).resolve()

        # Count files (with reasonable limits to avoid hanging on huge projects)
        total_files = 0
        source_files = 0
        doc_files = 0

        # Use iterative approach with limit to avoid memory issues
        max_count = 10000
        for i, path in enumerate(root.rglob("*")):
            if i >= max_count:
                break
            if path.is_file():
                total_files += 1
                suffix = path.suffix.lower()
                if suffix in [".py", ".js", ".ts", ".jsx", ".tsx", ".rs", ".go"]:
                    source_files += 1
                elif suffix == ".md":
                    doc_files += 1

        # Estimate time (empirical values based on typical performance)
        base_time = 30  # seconds for basic setup
        doc_time = doc_files * 2  # 2 seconds per doc file
        source_time = source_files * 5  # 5 seconds per source file for AST analysis

        quick_time = int(base_time + (doc_files * 0.5))
        standard_time = int(base_time + doc_time + (source_files * 1))
        deep_time = int(base_time + doc_time + source_time + 60)  # +60 for external URLs

        # Recommend mode based on deep time estimate
        if deep_time > 1800:  # > 30 minutes
            recommended = "quick"
        elif deep_time > 600:  # > 10 minutes
            recommended = "standard"
        else:
            recommended = "standard"

        return ScanTimeEstimate(
            total_files=total_files,
            source_files=source_files,
            doc_files=doc_files,
            estimated_quick_seconds=quick_time,
            estimated_standard_seconds=standard_time,
            estimated_deep_seconds=deep_time,
            recommended_mode=recommended,
        )
