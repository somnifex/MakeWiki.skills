"""Integration test - verify cross-language review catches injected inconsistency."""

from makewiki_skills.generator.language_generator import GeneratedDocument
from makewiki_skills.review.cross_language_reviewer import CrossLanguageReviewer


def test_cross_validate_catches_missing_command():
    """When EN has a command that ZH-CN doesn't, the reviewer must flag it."""
    en_readme = GeneratedDocument(
        filename="README.md",
        base_name="README.md",
        language_code="en",
        content=(
            "# MyApp\n\n"
            "## Commands\n\n"
            "```bash\n"
            "myapp serve --port 8080\n"
            "myapp build --output dist/\n"
            "myapp test --coverage\n"
            "```\n"
        ),
    )
    zh_readme = GeneratedDocument(
        filename="README.zh-CN.md",
        base_name="README.md",
        language_code="zh-CN",
        content=(
            "# MyApp\n\n"
            "## \u547d\u4ee4\n\n"
            "```bash\n"
            "myapp serve --port 8080\n"
            "myapp build --output dist/\n"
            "```\n"
            "# Note: myapp test is deliberately omitted here\n"
        ),
    )

    reviewer = CrossLanguageReviewer()
    result = reviewer.review({"en": [en_readme], "zh-CN": [zh_readme]})

    # The reviewer must detect that 'myapp test --coverage' is missing from zh-CN
    cmd_deltas = [d for d in result.fact_deltas if d.fact_type == "command"]
    missing_test = [d for d in cmd_deltas if "myapp test" in d.value]
    assert len(missing_test) >= 1
    assert "zh-CN" in missing_test[0].missing_from
    assert missing_test[0].severity == "critical"


def test_cross_validate_catches_missing_page():
    """When EN has a page that ZH-CN doesn't, it must be flagged."""
    en_docs = [
        GeneratedDocument(filename="README.md", base_name="README.md", language_code="en", content="# App\n"),
        GeneratedDocument(filename="installation.md", base_name="installation.md", language_code="en", content="# Install\n"),
        GeneratedDocument(filename="faq.md", base_name="faq.md", language_code="en", content="# FAQ\n"),
    ]
    zh_docs = [
        GeneratedDocument(filename="README.zh-CN.md", base_name="README.md", language_code="zh-CN", content="# App\n"),
        GeneratedDocument(filename="installation.zh-CN.md", base_name="installation.md", language_code="zh-CN", content="# Install\n"),
        # faq.md is deliberately missing
    ]

    reviewer = CrossLanguageReviewer()
    result = reviewer.review({"en": en_docs, "zh-CN": zh_docs})

    page_deltas = [d for d in result.fact_deltas if d.fact_type == "page"]
    assert any(d.value == "faq.md" and "zh-CN" in d.missing_from for d in page_deltas)


def test_cross_validate_no_false_positives_for_consistent_docs():
    """Two languages with identical structure and commands -> no critical issues."""
    content_template = (
        "# App\n\n"
        "## Install\n\n"
        "```bash\npip install myapp\n```\n\n"
        "## Usage\n\n"
        "```bash\nmyapp run\nmyapp status\n```\n"
    )
    en = GeneratedDocument(filename="README.md", base_name="README.md", language_code="en", content=content_template)
    zh = GeneratedDocument(filename="README.zh-CN.md", base_name="README.md", language_code="zh-CN", content=content_template)

    reviewer = CrossLanguageReviewer()
    result = reviewer.review({"en": [en], "zh-CN": [zh]})

    assert result.passed
    critical = [d for d in result.fact_deltas if d.severity == "critical"]
    assert len(critical) == 0
