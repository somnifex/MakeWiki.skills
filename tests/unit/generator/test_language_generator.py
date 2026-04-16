"""Tests for LanguageGenerator."""

from makewiki_skills.config import MakeWikiConfig
from makewiki_skills.generator.language_generator import LanguageGenerator
from makewiki_skills.languages.registry import LanguageRegistry
from makewiki_skills.model.semantic_model import (
    Command,
    InstallStep,
    InstallationGuide,
    Prerequisite,
    ProjectIdentity,
    SemanticModel,
)
from makewiki_skills.scanner.project_detector import ProjectType


def _make_model() -> SemanticModel:
    return SemanticModel(
        identity=ProjectIdentity(name="test-app", version="1.0.0", description="A test application."),
        installation=InstallationGuide(
            prerequisites=[Prerequisite(name="Python", version_constraint=">=3.11")],
            steps=[
                InstallStep(order=1, title="Clone", commands=["git clone <url>", "cd test-app"]),
                InstallStep(order=2, title="Install", commands=["pip install -e ."]),
            ],
            verify_command="test-app --version",
        ),
        commands=[
            Command(name="test-app serve", description="Start the server"),
            Command(name="test-app build", description="Build the project"),
        ],
        project_type=ProjectType.PYTHON_CLI,
    )


def test_generate_english():
    LanguageRegistry.load_builtins()
    profile = LanguageRegistry.get("en")
    config = MakeWikiConfig.default()
    gen = LanguageGenerator()

    docs = gen.generate(_make_model(), profile, config)
    assert len(docs) >= 5  # README, getting-started, installation, configuration, usage, faq, troubleshooting
    filenames = [d.filename for d in docs]
    assert "README.md" in filenames
    assert "installation.md" in filenames

    # Check content is in English
    readme = next(d for d in docs if d.filename == "README.md")
    assert "test-app" in readme.content


def test_generate_chinese():
    LanguageRegistry.load_builtins()
    profile = LanguageRegistry.get("zh-CN")
    config = MakeWikiConfig.default()
    gen = LanguageGenerator()

    docs = gen.generate(_make_model(), profile, config)
    filenames = [d.filename for d in docs]
    assert "README.zh-CN.md" in filenames
    assert "installation.zh-CN.md" in filenames

    readme = next(d for d in docs if d.filename == "README.zh-CN.md")
    assert "test-app" in readme.content


def test_each_language_generates_independently():
    """Verify that EN and ZH-CN are generated from the same model independently."""
    LanguageRegistry.load_builtins()
    config = MakeWikiConfig.default()
    model = _make_model()
    gen = LanguageGenerator()

    en_docs = gen.generate(model, LanguageRegistry.get("en"), config)
    zh_docs = gen.generate(model, LanguageRegistry.get("zh-CN"), config)

    # Same number of documents
    assert len(en_docs) == len(zh_docs)

    # Same base names
    en_bases = sorted(d.base_name for d in en_docs)
    zh_bases = sorted(d.base_name for d in zh_docs)
    assert en_bases == zh_bases

    # Different filenames (language suffix)
    en_fnames = sorted(d.filename for d in en_docs)
    zh_fnames = sorted(d.filename for d in zh_docs)
    assert en_fnames != zh_fnames

    # Content is different (different language, not copies)
    en_readme = next(d for d in en_docs if d.base_name == "README.md")
    zh_readme = next(d for d in zh_docs if d.base_name == "README.md")
    assert en_readme.content != zh_readme.content


def test_language_suffix_naming():
    LanguageRegistry.load_builtins()
    profile = LanguageRegistry.get("ja")
    assert profile.get_filename("README.md") == "README.ja.md"
    assert profile.get_filename("getting-started.md") == "getting-started.ja.md"
    assert profile.get_filename("usage/basic-usage.md") == "usage/basic-usage.ja.md"


def test_emit_uncertainty_notes_disabled():
    """When emit_uncertainty_notes is False, uncertainty strings should be empty."""
    LanguageRegistry.load_builtins()
    profile = LanguageRegistry.get("en")
    config = MakeWikiConfig.default()
    config.emit_uncertainty_notes = False
    gen = LanguageGenerator()

    # Model with no configuration and no FAQ -> templates would normally emit uncertainty
    model = SemanticModel(
        identity=ProjectIdentity(name="bare-app"),
        installation=InstallationGuide(
            steps=[InstallStep(order=1, title="Install", commands=["npm install"])],
        ),
        commands=[],
        project_type=ProjectType.GENERIC,
    )

    docs = gen.generate(model, profile, config)

    # configuration.md should NOT contain the "No configuration items" message
    config_doc = next(d for d in docs if d.base_name == "configuration.md")
    assert "No configuration items" not in config_doc.content

    # faq.md should NOT contain the "No frequently asked questions" message
    faq_doc = next(d for d in docs if d.base_name == "faq.md")
    assert "No frequently asked questions" not in faq_doc.content


def test_emit_uncertainty_notes_enabled():
    """When emit_uncertainty_notes is True (default), uncertainty notes appear."""
    LanguageRegistry.load_builtins()
    profile = LanguageRegistry.get("en")
    config = MakeWikiConfig.default()
    gen = LanguageGenerator()

    model = SemanticModel(
        identity=ProjectIdentity(name="bare-app"),
        installation=InstallationGuide(
            steps=[InstallStep(order=1, title="Install", commands=["npm install"])],
        ),
        commands=[],
        project_type=ProjectType.GENERIC,
    )

    docs = gen.generate(model, profile, config)

    config_doc = next(d for d in docs if d.base_name == "configuration.md")
    assert "No configuration items" in config_doc.content
