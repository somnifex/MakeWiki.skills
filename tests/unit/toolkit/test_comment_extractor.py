"""Tests for CommentExtractor."""

from pathlib import Path
from textwrap import dedent

import pytest

from makewiki_skills.toolkit.comment_extractor import CommentExtractor, ConfigComment


@pytest.fixture
def extractor() -> CommentExtractor:
    return CommentExtractor()


class TestEnvComments:
    def test_preceding_comment(self, extractor: CommentExtractor, tmp_path: Path) -> None:
        env_file = tmp_path / ".env.example"
        env_file.write_text(dedent("""\
            # Database connection string
            DATABASE_URL=postgres://localhost:5432/mydb

            # Secret key for session signing
            SECRET_KEY=change-me-in-production
        """))
        comments = extractor.extract_env_comments(env_file)
        assert len(comments) == 2
        assert comments[0].key == "DATABASE_URL"
        assert "Database connection string" in comments[0].comment_text
        assert comments[1].key == "SECRET_KEY"

    def test_multiline_preceding_comment(self, extractor: CommentExtractor, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text(dedent("""\
            # Redis host
            # Used for caching and session storage
            REDIS_URL=redis://localhost:6379
        """))
        comments = extractor.extract_env_comments(env_file)
        assert len(comments) == 1
        assert "Redis host" in comments[0].comment_text
        assert "caching" in comments[0].comment_text

    def test_inline_comment(self, extractor: CommentExtractor, tmp_path: Path) -> None:
        env_file = tmp_path / ".env.example"
        env_file.write_text("PORT=8080  # HTTP listen port\n")
        comments = extractor.extract_env_comments(env_file)
        assert any(c.comment_type == "inline" and "HTTP listen port" in c.comment_text for c in comments)

    def test_no_comments(self, extractor: CommentExtractor, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=value\nOTHER=stuff\n")
        comments = extractor.extract_env_comments(env_file)
        assert len(comments) == 0

    def test_blank_line_breaks_association(self, extractor: CommentExtractor, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text(dedent("""\
            # This comment is orphaned

            DB_HOST=localhost
        """))
        comments = extractor.extract_env_comments(env_file)
        assert len(comments) == 0


class TestYamlComments:
    def test_preceding_yaml_comment(self, extractor: CommentExtractor, tmp_path: Path) -> None:
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text(dedent("""\
            # Server listen port
            port: 8080
            # Database host address
            host: localhost
        """))
        comments = extractor.extract_yaml_comments(yaml_file)
        assert len(comments) == 2
        assert comments[0].key == "port"
        assert "Server listen port" in comments[0].comment_text

    def test_inline_yaml_comment(self, extractor: CommentExtractor, tmp_path: Path) -> None:
        yaml_file = tmp_path / "config.yml"
        yaml_file.write_text("timeout: 30  # seconds\n")
        comments = extractor.extract_yaml_comments(yaml_file)
        assert any(c.comment_type == "inline" and "seconds" in c.comment_text for c in comments)


class TestTomlComments:
    def test_preceding_toml_comment(self, extractor: CommentExtractor, tmp_path: Path) -> None:
        toml_file = tmp_path / "config.toml"
        toml_file.write_text(dedent("""\
            # Maximum retry attempts
            max_retries = 3
        """))
        comments = extractor.extract_toml_comments(toml_file)
        assert len(comments) == 1
        assert comments[0].key == "max_retries"
        assert "retry" in comments[0].comment_text.lower()


class TestIniComments:
    def test_preceding_ini_comment(self, extractor: CommentExtractor, tmp_path: Path) -> None:
        ini_file = tmp_path / "app.ini"
        ini_file.write_text(dedent("""\
            [server]
            ; Bind address for the HTTP server
            host = 0.0.0.0
        """))
        comments = extractor.extract_ini_comments(ini_file)
        assert len(comments) == 1
        assert comments[0].key == "host"


class TestAutoDetect:
    def test_auto_detect_env(self, extractor: CommentExtractor, tmp_path: Path) -> None:
        env_file = tmp_path / ".env.example"
        env_file.write_text("# Port\nPORT=3000\n")
        comments = extractor.extract_comments(env_file)
        assert len(comments) == 1

    def test_auto_detect_yaml(self, extractor: CommentExtractor, tmp_path: Path) -> None:
        yaml_file = tmp_path / "settings.yaml"
        yaml_file.write_text("# Debug mode\ndebug: false\n")
        comments = extractor.extract_comments(yaml_file)
        assert len(comments) == 1


class TestToEvidenceFacts:
    def test_converts_to_evidence_facts(self, extractor: CommentExtractor) -> None:
        comments = [
            ConfigComment(
                key="PORT",
                comment_text="HTTP listen port",
                source_path=".env.example",
                line_number=1,
            )
        ]
        facts = extractor.to_evidence_facts(comments)
        assert len(facts) == 1
        assert facts[0].fact_type == "config_comment"
        assert facts[0].value == "PORT"
        assert "HTTP listen port" in facts[0].evidence[0].raw_text
