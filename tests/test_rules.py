import pymupdf
from conftest import context, paged_context, region
from PIL import Image

from pdfvalidator.extract import extract_annotations
from pdfvalidator.logo import compute_reference_hash
from pdfvalidator.rules import (
    CategoryDefinitionRule,
    CitationFormatRule,
    DisclaimerRule,
    DocumentContext,
    LogoLicenseRule,
    NamingSequenceRule,
)

COMPLETE_CITATION = (
    "Referenced with permission from the Contoso Health Network Clinical Practice "
    "Standards (CHN Clinical Standards™) for General Testing Criteria V.2.2026. "
    "© Contoso Health Network, Inc. 2026. All rights reserved. Accessed March 4, 2026. "
    "To view the most recent version, go online to contosohealth.org."
)

TIER_A_DEFINITION = (
    "¹Tier A: Based upon high-quality evidence, there is uniform CHN panel "
    "consensus (≥85% support) that the approach is appropriate."
)


# --------------------------------------------------------------------------- #
# CHN-1 / CHN-2 / CHN-3
# --------------------------------------------------------------------------- #

def test_correct_chn_sequence_produces_no_findings():
    ctx = context(
        "Contoso Health Network® (CHN®) publishes clinical guidance.",
        "CHN reviews are widely used.",
    )
    assert NamingSequenceRule().check(ctx) == []


def test_bare_chn_before_first_mention_is_flagged():
    findings = NamingSequenceRule().check(context("CHN reviews are widely used."))
    assert [f.rule_id for f in findings] == ["CHN-1"]


def test_bare_chn_inside_a_standards_phrase_does_not_also_fire_chn1():
    findings = NamingSequenceRule().check(context("CHN Clinical Standards guide practice."))
    assert [f.rule_id for f in findings] == ["CHN-2"]


def test_correct_standards_sequence_produces_no_findings():
    ctx = context(
        "Contoso Health Network Clinical Practice Standards (CHN Clinical Standards™) guide practice.",
        "CHN Clinical Standards™ are updated yearly.",
        "CHN Clinical Standards remain the benchmark.",
    )
    assert NamingSequenceRule().check(ctx) == []


def test_chn3_flags_both_first_mentions_in_one_sentence():
    ctx = context(
        "Contoso Health Network® (CHN®) and the Contoso Health Network Clinical Practice "
        "Standards (CHN Clinical Standards™) were announced together today."
    )
    assert any(f.rule_id == "CHN-3" for f in NamingSequenceRule().check(ctx))


def test_citation_reproduction_is_not_counted_as_a_fresh_mention():
    ctx = context("Referenced with permission from earlier CHN materials for background context.")
    assert NamingSequenceRule().check(ctx) == []


def test_citation_reproductions_do_not_shift_the_occurrence_count():
    """Sample-01's shape: both citations respell the full standards name. Counting
    them would push the later short form to occurrence #5 and invent a violation.
    """
    ctx = context(
        "Contoso Health Network Clinical Practice Standards (CHN Clinical Standards™) for Breast Cancer.",
        "CHN Clinical Standards™ for Central Nervous System Cancers.",
        "1. " + COMPLETE_CITATION,
        "2. " + COMPLETE_CITATION,
        "Scan the code for the full CHN Clinical Standards excerpt.",
    )
    assert NamingSequenceRule().check(ctx) == []


def test_line_wrapped_first_mention_still_matches():
    ctx = context("Contoso Health Network Clinical Practice Standards (CHN Clinical\nStandards™) for Breast Cancer.")
    assert NamingSequenceRule().check(ctx) == []


def test_headline_introducing_both_forms_together_is_exempt():
    ctx = context("TWO CHN TIER A RECOMMENDATIONS FROM CONTOSO HEALTH NETWORK® (CHN®) FOR EXAMPLEDRUG (BRANDX®)")
    assert NamingSequenceRule().check(ctx) == []


def test_bare_chn_as_its_own_sentence_still_violates():
    ctx = context("CHN recommends this. It was founded by Contoso Health Network® (CHN®) in 1990.")
    assert [f.rule_id for f in NamingSequenceRule().check(ctx)] == ["CHN-1"]


def test_agreement_id_is_not_a_trademark_mention():
    """"CHN-2026-014" is an identifier, not a use of the mark. Sample-06 reported a
    false CHN-1 violation for it before the pattern excluded ID-shaped matches.
    """
    ctx = context("Logo used with permission per agreement CHN-2026-014.")
    assert NamingSequenceRule().check(ctx) == []


def test_hyphenated_word_after_chn_is_still_a_mention():
    ctx = context("CHN-approved materials must carry the mark.")
    assert [f.rule_id for f in NamingSequenceRule().check(ctx)] == ["CHN-1"]


# --------------------------------------------------------------------------- #
# Category definitions
# --------------------------------------------------------------------------- #

def test_exact_definition_passes():
    assert CategoryDefinitionRule().check(context(TIER_A_DEFINITION)) == []


def test_paraphrased_definition_is_flagged():
    findings = CategoryDefinitionRule().check(context("Tier A: This approach has strong panel support."))
    assert [f.rule_id for f in findings] == ["CAT-DEF"]


def test_no_finding_when_no_rating_is_stated():
    assert CategoryDefinitionRule().check(context("No rating mentioned here.")) == []


def test_definition_in_another_block_on_the_same_page_counts():
    assert CategoryDefinitionRule().check(paged_context((1, "TIER A"), (1, TIER_A_DEFINITION))) == []


def test_line_wrapped_definition_still_counts():
    wrapped = TIER_A_DEFINITION.replace("CHN panel ", "CHN panel\n")
    assert CategoryDefinitionRule().check(paged_context((1, "TIER A"), (1, wrapped))) == []


def test_definition_on_a_different_page_is_not_nearby():
    findings = CategoryDefinitionRule().check(paged_context((1, "TIER A"), (2, TIER_A_DEFINITION)))
    assert [f.rule_id for f in findings] == ["CAT-DEF"]


def test_one_finding_per_rating_per_page():
    """Five "Tier A" mentions on a page with no definition is one problem, not five."""
    ctx = paged_context(
        (1, "TIER A"), (1, "recommended as a Tier A option"), (1, "the only Tier A choice"),
    )
    assert len(CategoryDefinitionRule().check(ctx)) == 1


# --------------------------------------------------------------------------- #
# Citations
# --------------------------------------------------------------------------- #

def test_complete_citation_passes():
    assert CitationFormatRule().check(context(COMPLETE_CITATION)) == []


def test_missing_access_date_is_flagged():
    without_date = COMPLETE_CITATION.replace("Accessed March 4, 2026. ", "")
    findings = CitationFormatRule().check(context(without_date))
    assert len(findings) == 1
    assert "access date" in findings[0].explanation


def test_non_citation_text_is_ignored():
    assert CitationFormatRule().check(context("Just some regular content.")) == []


def test_line_wrapped_citation_lead_in_is_still_detected():
    wrapped = COMPLETE_CITATION.replace("Referenced with permission", "Referenced with\npermission")
    assert CitationFormatRule().check(context(wrapped)) == []

    incomplete = wrapped.replace("Accessed March 4, 2026. ", "")
    assert [f.rule_id for f in CitationFormatRule().check(context(incomplete))] == ["CITATION"]


# --------------------------------------------------------------------------- #
# Disclaimer
# --------------------------------------------------------------------------- #

def test_disclaimer_present_passes():
    text = (
        "Some content. CHN makes no warranties of any kind regarding this content, its use, "
        "or application, and disclaims any responsibility for its application or use in any way."
    )
    assert DisclaimerRule().check(context(text)) == []


def test_missing_disclaimer_is_a_document_level_finding():
    findings = DisclaimerRule().check(context("No disclaimer here."))
    assert len(findings) == 1
    assert findings[0].rule_id == "DISCLAIMER"
    assert findings[0].bbox is None


def test_line_wrapped_disclaimer_still_matches():
    text = (
        "CHN makes no warranties of any kind regarding this content, its use, or application, "
        "and disclaims any responsibility\nfor its application or use in any way."
    )
    assert DisclaimerRule().check(context(text)) == []


# --------------------------------------------------------------------------- #
# Logo / license
# --------------------------------------------------------------------------- #

def test_no_logo_findings_without_a_reference_hash():
    ctx = DocumentContext(text_spans=[], regions=[region()])
    assert LogoLicenseRule().check(ctx) == []


def _logo_pdf(tmp_path, license_gap_pt: float):
    """A logo in its own highlighted region, with the license caption placed a
    given distance below it — so only the nearby-margin behaviour is under test.
    """
    reference_path = tmp_path / "reference.png"
    Image.new("RGB", (64, 64), color=(20, 80, 200)).save(reference_path)

    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_image(pymupdf.Rect(72, 72, 136, 136), filename=str(reference_path))
    region_rect = pymupdf.Rect(10, 65, 300, 140)
    page.add_highlight_annot(region_rect)
    page.insert_text(
        (10, region_rect.y1 + license_gap_pt + 8),  # +8 for glyph ascent above the baseline
        "Logo used with permission per agreement CHN-2026-014.", fontsize=8,
    )
    path = tmp_path / "sample.pdf"
    doc.save(path)
    doc.close()
    return path, reference_path


def _check_logo(path, reference_path, ids):
    doc = pymupdf.open(path)
    ctx = DocumentContext(
        text_spans=[],
        regions=extract_annotations(doc[0], page_number=1, id_counter=ids),
        pdf=doc,
        reference_logo_hash=compute_reference_hash(str(reference_path)),
    )
    findings = LogoLicenseRule().check(ctx)
    doc.close()
    return findings


def test_license_reference_near_the_logo_is_compliant(tmp_path, ids):
    findings = _check_logo(*_logo_pdf(tmp_path, license_gap_pt=10), ids)
    assert [f.confidence for f in findings] == ["confirmed"]


def test_license_reference_too_far_away_is_left_for_review(tmp_path, ids):
    findings = _check_logo(*_logo_pdf(tmp_path, license_gap_pt=100), ids)
    assert [f.confidence for f in findings] == ["needs_review"]
