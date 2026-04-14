"""Tests for EvidenceTool and evidence types."""

from makewiki_skills.toolkit.evidence import EvidenceFact, EvidenceLink, EvidenceTool


def test_evidence_link_creation():
    link = EvidenceLink(
        source_path="pyproject.toml",
        raw_text='name = "hello"',
        confidence="high",
        extraction_method="direct_read",
    )
    assert link.confidence == "high"
    assert link.source_path == "pyproject.toml"


def test_evidence_fact_best_confidence():
    fact = EvidenceFact(
        claim="Version is 1.0",
        fact_type="version",
        value="1.0",
        evidence=[
            EvidenceLink(source_path="a.toml", raw_text="v1.0", confidence="medium"),
            EvidenceLink(source_path="b.py", raw_text="1.0", confidence="high"),
        ],
    )
    assert fact.best_confidence == "high"


def test_evidence_fact_no_evidence():
    fact = EvidenceFact(claim="Unknown", fact_type="version", value="?")
    assert fact.best_confidence == "inferred"


def test_extract_commands():
    tool = EvidenceTool()
    content = '## Usage\n\n```bash\npip install foo\nfoo serve --port 8080\n```\n'
    facts = tool.extract_commands(content, "README.md")
    assert len(facts) == 2
    assert facts[0].value == "pip install foo"
    assert facts[1].value == "foo serve --port 8080"


def test_extract_commands_with_dollar_prefix():
    tool = EvidenceTool()
    content = '```bash\n$ npm install\n$ npm start\n```\n'
    facts = tool.extract_commands(content, "README.md")
    assert len(facts) == 2
    assert facts[0].value == "npm install"


def test_extract_config_keys():
    tool = EvidenceTool()
    data = {"server": {"host": "localhost", "port": 8080}, "debug": True}
    facts = tool.extract_config_keys(data, "config.yaml")
    keys = [f.value for f in facts]
    assert "server" in keys
    assert "server.host" in keys
    assert "debug" in keys


def test_extract_version():
    tool = EvidenceTool()
    content = '__version__ = "1.2.3"\n'
    fact = tool.extract_version(content, "app.py")
    assert fact is not None
    assert fact.value == "1.2.3"
    assert fact.fact_type == "version"


def test_extract_version_none():
    tool = EvidenceTool()
    fact = tool.extract_version("no version here", "app.py")
    assert fact is None


def test_extract_dependencies():
    tool = EvidenceTool()
    deps = ["typer>=0.12", "pydantic>=2.7", "jinja2"]
    facts = tool.extract_dependencies(deps, "pyproject.toml")
    names = [f.value for f in facts]
    assert "typer" in names
    assert "pydantic" in names
    assert "jinja2" in names


def test_merge_facts():
    facts = [
        EvidenceFact(
            claim="Cmd: run",
            fact_type="command",
            value="run",
            evidence=[EvidenceLink(source_path="a", raw_text="run", confidence="medium")],
        ),
        EvidenceFact(
            claim="Cmd: run",
            fact_type="command",
            value="run",
            evidence=[EvidenceLink(source_path="b", raw_text="run", confidence="high")],
        ),
        EvidenceFact(
            claim="Cmd: test",
            fact_type="command",
            value="test",
            evidence=[EvidenceLink(source_path="c", raw_text="test", confidence="medium")],
        ),
    ]
    merged = EvidenceTool.merge_facts(facts)
    assert len(merged) == 2
    run_fact = next(f for f in merged if f.value == "run")
    assert len(run_fact.evidence) == 2
