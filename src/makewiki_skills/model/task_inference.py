"""Task inference engine - derive user-facing tasks from collected evidence."""

from __future__ import annotations

import re
import uuid

from makewiki_skills.model.semantic_model import Command, ConfigSection, UserTask
from makewiki_skills.scanner.evidence_registry import EvidenceRegistry
from makewiki_skills.scanner.project_detector import ProjectDetectionResult


_USER_TASK_PATTERNS: list[tuple[str, str, str]] = [
    (r"(?:^|\s)(?:serve|start|run|dev)(?:\s|$)", "Start the application", "Run the project locally."),
    (
        r"(?:docker compose|docker-compose)",
        "Start the application with Docker",
        "Run the project with the documented container workflow.",
    ),
    (
        r"(?:^|\s)(?:migrate|migration)(?:\s|$)",
        "Run database migrations",
        "Apply the database changes required before using the project.",
    ),
    (
        r"(?:^|\s)(?:login|auth|signin|sign-in)(?:\s|$)",
        "Sign in",
        "Authenticate before using the project.",
    ),
]

_DEVELOPER_COMMAND_PATTERNS: tuple[str, ...] = (
    r"(^|\s)(?:test|pytest|jest|mocha|vitest)(\s|$)",
    r"(^|\s)(?:lint|ruff|eslint|flake8|check)(\s|$)",
    r"(^|\s)(?:format|fmt|prettier|black)(\s|$)",
    r"(^|\s)(?:clean|coverage|bench|benchmark)(\s|$)",
    r"(^|\s)(?:build|compile|dist|release|publish)(\s|$)",
)

_INSTALL_COMMAND_PREFIXES: tuple[str, ...] = (
    "git clone ",
    "cd ",
    "pip install",
    "python -m pip install",
    "uv sync",
    "uv pip install",
    "poetry install",
    "npm install",
    "pnpm install",
    "yarn install",
    "cargo build",
    "go build",
)

_NON_EXECUTABLE_PREFIXES: set[str] = {
    "cd",
    "docker",
    "git",
    "go",
    "make",
    "npm",
    "pip",
    "pnpm",
    "poetry",
    "pytest",
    "python",
    "ruff",
    "uv",
    "yarn",
}


class TaskInferenceEngine:
    """Infer :class:`UserTask` objects from user-visible commands."""

    def infer(
        self,
        commands: list[Command],
        configuration: list[ConfigSection],
        detection: ProjectDetectionResult,
        registry: EvidenceRegistry,
    ) -> list[UserTask]:
        del configuration, registry

        tasks: list[UserTask] = []
        seen_titles: set[str] = set()
        executables = self._likely_executables(commands, detection)

        for cmd in sorted(commands, key=lambda item: self._priority(item, executables)):
            if self._skip_command(cmd.name):
                continue

            title, goal = self._match_known_task(cmd.name)
            if title is None:
                continue

            if title in seen_titles:
                continue

            seen_titles.add(title)
            tasks.append(
                UserTask(
                    task_id=uuid.uuid4().hex[:10],
                    title=title,
                    user_goal=goal,
                    steps=[f"Run `{cmd.name}`."],
                    commands=[cmd.name],
                    evidence=cmd.evidence,
                )
            )

        return tasks

    def _priority(self, command: Command, executables: set[str]) -> int:
        section = (command.section or "").lower()
        if any(keyword in section for keyword in ("usage", "example", "quick start", "getting started")):
            return 0
        if self._is_user_cli_command(command.name, executables):
            return 1
        if command.name.startswith(("docker compose", "docker-compose")):
            return 2
        if command.name.startswith("make "):
            return 4
        return 3

    @staticmethod
    def _match_known_task(command_name: str) -> tuple[str | None, str | None]:
        for pattern, title, goal in _USER_TASK_PATTERNS:
            if re.search(pattern, command_name, re.IGNORECASE):
                return title, goal
        return None, None

    @staticmethod
    def _skip_command(command_name: str) -> bool:
        normalized = command_name.strip().lower()
        if not normalized:
            return True
        if any(normalized.startswith(prefix) for prefix in _INSTALL_COMMAND_PREFIXES):
            return True
        if len(normalized.split()) == 1 and normalized not in {"docker compose", "docker-compose"}:
            return True
        return any(re.search(pattern, normalized, re.IGNORECASE) for pattern in _DEVELOPER_COMMAND_PATTERNS)

    @staticmethod
    def _likely_executables(
        commands: list[Command],
        detection: ProjectDetectionResult,
    ) -> set[str]:
        candidates: set[str] = set()
        if detection.project_name:
            candidates.add(detection.project_name.lower())

        for command in commands:
            parts = command.name.split()
            if not parts:
                continue
            head = parts[0].lower()
            if head not in _NON_EXECUTABLE_PREFIXES:
                candidates.add(head)

        return candidates

    @staticmethod
    def _is_user_cli_command(command_name: str, executables: set[str]) -> bool:
        normalized = command_name.strip().lower()
        if normalized.startswith(("docker compose", "docker-compose")):
            return True
        parts = normalized.split()
        return len(parts) >= 2 and parts[0] in executables
