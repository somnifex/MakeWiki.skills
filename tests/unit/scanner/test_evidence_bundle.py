"""Tests for EvidenceBundle model."""

import json

import pytest

from makewiki_skills.scanner.evidence_bundle import EvidenceBundle, EvidenceBundleDetection
from makewiki_skills.scanner.evidence_registry import EvidenceRegistry
from makewiki_skills.scanner.project_detector import ProjectDetectionResult, ProjectType
from makewiki_skills.toolkit.evidence import EvidenceFact, EvidenceLink


@pytest.fixture
def sample_detection() -> ProjectDetectionResult:
    return ProjectDetectionResult(
        project_type=ProjectType.PYTHON_CLI,
        confidence=0.88,
        indicators_found=["pyproject.toml"],
        project_name="myapp",
        project_dir="/tmp/myapp",
    )


@pytest.fixture
def sample_facts() -> list[EvidenceFact]:
    return [
        EvidenceFact(
            claim="Command: myapp start",
            fact_type="command",
            value="myapp start",
            evidence=[
                EvidenceLink(
                    source_path="README.md",
                    line_range=(10, 10),
                    raw_text="myapp start",
                    confidence="medium",
                )
            ],
        ),
        EvidenceFact(
            claim="Config key: server.port",
            fact_type="config_key",
            value="server.port",
            evidence=[
                EvidenceLink(
                    source_path=".env.example",
                    raw_text="server.port = 8080",
                    confidence="high",
                )
            ],
        ),
        EvidenceFact(
            claim="Config comment for PORT: HTTP listen port",
            fact_type="config_comment",
            value="PORT",
            evidence=[
                EvidenceLink(
                    source_path=".env.example",
                    raw_text="HTTP listen port",
                    confidence="medium",
                    extraction_method="comment_extraction",
                )
            ],
        ),
    ]


class TestEvidenceBundleFromRegistry:
    def test_basic_bundle(
        self, sample_detection: ProjectDetectionResult, sample_facts: list[EvidenceFact]
    ) -> None:
        bundle = EvidenceBundle.from_registry(
            detection=sample_detection,
            facts=sample_facts,
            files_read=["README.md", ".env.example"],
        )

        assert bundle.detection.project_type == "python-cli"
        assert bundle.detection.confidence == 0.88
        assert bundle.detection.project_name == "myapp"
        assert bundle.total_facts == 3
        assert bundle.summary["command"] == 1
        assert bundle.summary["config_key"] == 1
        assert bundle.summary["config_comment"] == 1
        assert "myapp start" in bundle.commands_discovered
        assert "README.md" in bundle.files_read

    def test_facts_grouped_by_type(
        self, sample_detection: ProjectDetectionResult, sample_facts: list[EvidenceFact]
    ) -> None:
        bundle = EvidenceBundle.from_registry(
            detection=sample_detection,
            facts=sample_facts,
        )

        assert "command" in bundle.facts_by_type
        assert "config_key" in bundle.facts_by_type
        assert "config_comment" in bundle.facts_by_type
        assert len(bundle.facts_by_type["command"]) == 1
        assert bundle.facts_by_type["command"][0].value == "myapp start"

    def test_serializable_to_json(
        self, sample_detection: ProjectDetectionResult, sample_facts: list[EvidenceFact]
    ) -> None:
        bundle = EvidenceBundle.from_registry(
            detection=sample_detection,
            facts=sample_facts,
        )
        json_str = json.dumps(bundle.model_dump(), indent=2)
        parsed = json.loads(json_str)
        assert parsed["detection"]["project_type"] == "python-cli"
        assert parsed["total_facts"] == 3

    def test_empty_bundle(self, sample_detection: ProjectDetectionResult) -> None:
        bundle = EvidenceBundle.from_registry(
            detection=sample_detection,
            facts=[],
        )
        assert bundle.total_facts == 0
        assert bundle.summary == {}
        assert bundle.commands_discovered == []


class TestRegistryToBundle:
    def test_registry_to_evidence_bundle(
        self, sample_detection: ProjectDetectionResult, sample_facts: list[EvidenceFact]
    ) -> None:
        registry = EvidenceRegistry()
        registry.add_many(sample_facts)

        bundle = registry.to_evidence_bundle(
            detection=sample_detection,
            files_read=["README.md"],
        )

        assert bundle.total_facts == 3
        assert bundle.detection.project_name == "myapp"
        assert "README.md" in bundle.files_read
