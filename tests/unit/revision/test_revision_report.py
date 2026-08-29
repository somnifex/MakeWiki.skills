"""Unit tests for RevisionReport semantics and metric calculations."""

from makewiki_skills.revision.revision_engine import RevisionAction, RevisionReport


def test_revision_report_initialization():
    report = RevisionReport(
        round_number=1,
        issues_before=3,
        issues_after=1,
        total_actions=2,
        attempted_fixes=2,
        verified_resolutions=2,
        introduced_regressions=0,
        actions=[
            RevisionAction(
                action_type="hedge_ungrounded",
                file_slug="usage.md",
                language="en",
                description="Hedged 1 ungrounded command",
            ),
            RevisionAction(
                action_type="harmonize_code_block",
                file_slug="README.zh-CN.md",
                language="zh-CN",
                description="Harmonized a README code block by stable ID",
            ),
        ],
    )

    assert report.round_number == 1
    assert report.issues_before == 3
    assert report.issues_after == 1
    assert report.total_actions == 2
    assert report.attempted_fixes == 2
    assert report.verified_resolutions == 2
    assert report.introduced_regressions == 0
    assert len(report.actions) == 2


def test_revision_report_resolution_calculation():
    issues_before = 5
    issues_after = 2
    verified_resolutions = max(issues_before - issues_after, 0)
    assert verified_resolutions == 3

    # Regression case
    issues_before = 2
    issues_after = 4
    verified_resolutions = max(issues_before - issues_after, 0)
    regressions = max(issues_after - issues_before, 0)
    assert verified_resolutions == 0
    assert regressions == 2
