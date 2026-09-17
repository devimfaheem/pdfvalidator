from conftest import region

from pdfvalidator.models import ComplianceReport, Finding
from pdfvalidator.report import build_report, render_markdown, to_dict

ALL_RULE_IDS = ["NAMING-SEQUENCE", "CAT-DEF", "CITATION", "DISCLAIMER", "LOGO-LICENSE", "QR-LINK"]


def _finding(rule_id: str, confidence: str = "confirmed", page: int = 1) -> Finding:
    return Finding(
        rule_id=rule_id, confidence=confidence, page=page, bbox=None,
        snippet="snippet", explanation="explanation",
    )


# --------------------------------------------------------------------------- #
# Status
# --------------------------------------------------------------------------- #

def test_pass_when_there_are_no_findings():
    report = build_report("doc.pdf", ALL_RULE_IDS, [])
    assert report.status == "PASS"
    assert report.rules_checked == 6
    assert report.rules_violated == 0
    assert report.needs_review_count == 0


def test_fail_when_a_violation_is_confirmed():
    report = build_report("doc.pdf", ALL_RULE_IDS, [_finding("CHN-1")])
    assert report.status == "FAIL"
    assert report.rules_violated == 1


def test_needs_review_when_only_flags_are_present():
    report = build_report("doc.pdf", ALL_RULE_IDS, [_finding("QR-LINK", "needs_review")])
    assert report.status == "NEEDS_REVIEW"
    assert report.needs_review_count == 1


def test_a_licensed_logo_is_compliance_not_a_violation():
    report = build_report("doc.pdf", ALL_RULE_IDS, [_finding("LOGO-LICENSE")])
    assert report.status == "PASS"
    assert report.rules_violated == 0


# --------------------------------------------------------------------------- #
# Markdown
# --------------------------------------------------------------------------- #

def test_markdown_includes_status_counts_and_sections():
    report = ComplianceReport(
        document="sample.pdf", status="FAIL", rules_checked=6, rules_violated=1, needs_review_count=1,
        findings=[_finding("CHN-1"), _finding("QR-LINK", "needs_review", page=3)],
    )
    markdown = render_markdown(report)

    assert "FAIL" in markdown
    assert "Rules checked: 6" in markdown
    assert "## Violations" in markdown
    assert "## Needs Human Review" in markdown
    assert "CHN-1" in markdown
    assert "QR-LINK" in markdown


def test_markdown_separates_a_compliant_logo_from_violations():
    """A reviewer skimming for problems must not meet good news under a heading
    that reads like a violation."""
    report = ComplianceReport(
        document="sample.pdf", status="FAIL", rules_checked=6, rules_violated=1, needs_review_count=0,
        findings=[_finding("CHN-1"), _finding("LOGO-LICENSE")],
    )
    markdown = render_markdown(report)

    assert "## Violations" in markdown
    assert "## Checked and Compliant" in markdown
    assert markdown.index("## Violations") < markdown.index("## Checked and Compliant")


# --------------------------------------------------------------------------- #
# Task 1 output and unevaluable regions
# --------------------------------------------------------------------------- #

def test_extracted_regions_are_carried_into_the_report():
    """Task 6 summarizes Tasks 1-4, so the regions Task 1 found belong in it —
    they are also what a finding's region_id points at."""
    regions = [region("r1", text="CHN Clinical Standards"), region("r2", page=2, text="more content")]
    report = build_report("doc.pdf", ALL_RULE_IDS, [], regions)

    assert len(report.regions) == 2
    assert [r["id"] for r in to_dict(report)["regions"]] == ["r1", "r2"]


def test_region_without_text_counts_as_not_evaluable():
    """The submitter marked something unreadable, so no rule could judge it. That
    is not a pass — it goes to a human."""
    report = build_report("doc.pdf", ALL_RULE_IDS, [], [region("r1", text="   ")])

    assert report.regions_unevaluated == 1
    assert report.status == "NEEDS_REVIEW"


def test_regions_with_text_are_all_evaluable():
    report = build_report("doc.pdf", ALL_RULE_IDS, [], [region("r1", text="CHN content")])

    assert report.regions_unevaluated == 0
    assert report.status == "PASS"


def test_markdown_lists_regions_with_their_detection_method():
    regions = [
        region("r1", text="native highlighted text", source="native_annotation"),
        region("r2", page=3, text="boxed text", source="hand_drawn"),
    ]
    markdown = render_markdown(build_report("doc.pdf", ALL_RULE_IDS, [], regions))

    assert "## Flagged Regions" in markdown
    assert "native annotation" in markdown
    assert "hand-drawn box" in markdown
    assert "Regions that could not be evaluated with confidence: 0" in markdown


def test_markdown_flags_an_unreadable_region_in_the_table():
    markdown = render_markdown(build_report("doc.pdf", ALL_RULE_IDS, [], [region("r1", text="")]))

    assert "could not be evaluated" in markdown
    assert "Regions that could not be evaluated with confidence: 1" in markdown


def test_markdown_states_when_nothing_was_found():
    report = ComplianceReport(
        document="sample.pdf", status="PASS", rules_checked=6, rules_violated=0,
        needs_review_count=0, findings=[],
    )
    assert "No findings" in render_markdown(report)
