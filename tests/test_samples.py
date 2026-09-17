"""End-to-end checks against the real sample packet.

Each expectation below was verified by reading the PDF itself, not by recording
whatever the pipeline happened to output.
"""

import itertools

import pymupdf
from conftest import SAMPLES_DIR

from pdfvalidator.extract import extract_annotations
from pdfvalidator.pipeline import run_pipeline


def _report(name: str):
    return run_pipeline(str(SAMPLES_DIR / name))


def _confirmed(report, rule_id: str):
    return [f for f in report.findings if f.rule_id == rule_id and f.confidence == "confirmed"]


def test_sample_01_flags_only_the_genuinely_incomplete_citation():
    """Citation #1 on page 1 omits "Accessed [date]"; citation #2 has it. That is a
    real omission in the file, and the only naming/category problem on the page —
    the title carries the correct first-mention form, and the Tier A definition is
    present in the footnote.
    """
    report = _report("CHN-Sample-01-Multi-Color-Highlights.pdf")

    citations = _confirmed(report, "CITATION")
    assert len(citations) == 1
    assert "access date" in citations[0].explanation
    assert "Breast Cancer" in citations[0].snippet

    for rule_id in ("CHN-1", "CHN-2", "CHN-3", "CAT-DEF", "DISCLAIMER"):
        assert _confirmed(report, rule_id) == []

    assert [f for f in report.findings if f.rule_id == "QR-LINK"]
    assert report.status == "FAIL"


def test_sample_02_flags_the_short_form_used_before_its_introduction():
    """The "CHN CLINICAL STANDARDS" badge appears above the footer citation that
    introduces the full form — a sequencing violation only visible in reading order.
    """
    report = _report("CHN-Sample-02-Single-Color-Tradeshow-Banner.pdf")
    assert _confirmed(report, "CHN-2")
    assert report.status == "FAIL"


def test_sample_03_flags_the_missing_trademark_symbol_across_pages():
    """Page 2 introduces the full form; page 3's heading is the 2nd occurrence and
    drops the ™. Catching it requires state carried across a page boundary.
    """
    report = _report("CHN-Sample-03-Multi-Page-Deck.pdf")
    assert _confirmed(report, "CHN-2")
    assert report.status == "FAIL"


def test_sample_04_extracts_the_drawn_box_and_ignores_the_reviewer_note():
    report = _report("CHN-Sample-04-Hand-Drawn-Boxes.pdf")

    # The note on page 1 says "Note to CHN: CHN content is located on slide 3".
    # Scanning it as body text would report two CHN-1 violations on page 1.
    assert not [f for f in _confirmed(report, "CHN-1") if f.page == 1]

    # Exactly what the reviewer marked: the drawn box and the highlight, both on
    # slide 3, as the note itself says. The deck's nav tab bar (five filled
    # rectangles per page, 21 in all) is page furniture, not flagged content.
    assert len(report.regions) == 2
    assert {r.page for r in report.regions} == {3}
    assert {r.source for r in report.regions} == {"hand_drawn", "native_annotation"}

    doc = pymupdf.open(str(SAMPLES_DIR / "CHN-Sample-04-Hand-Drawn-Boxes.pdf"))
    ids = itertools.count()
    regions = [r for i in range(len(doc)) for r in extract_annotations(doc[i], i + 1, ids)]
    doc.close()

    assert any(r.source == "hand_drawn" for r in regions)
    assert not any("Note to CHN" in r.text for r in regions)


def test_sample_05_logo_without_a_license_goes_to_a_reviewer():
    logo_findings = [f for f in _report("CHN-Sample-05-Logo-No-License.pdf").findings if f.rule_id == "LOGO-LICENSE"]
    assert logo_findings
    assert all(f.confidence == "needs_review" for f in logo_findings)


def test_sample_06_logo_with_a_license_is_provisionally_compliant():
    report = _report("CHN-Sample-06-Logo-With-License.pdf")

    logo_findings = [f for f in report.findings if f.rule_id == "LOGO-LICENSE"]
    assert logo_findings
    assert all(f.confidence == "confirmed" for f in logo_findings)

    # "agreement CHN-2026-014" is an identifier; it must not read as a bare mention.
    assert not [f for f in _confirmed(report, "CHN-1") if "CHN-2026-014" in f.snippet]
