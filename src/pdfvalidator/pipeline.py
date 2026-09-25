"""Extract regions and text, run every rule, build the report."""

import itertools
from pathlib import Path

import pymupdf

from .extract import build_text_spans, extract_annotations, extract_handdrawn_boxes, merge_regions
from .links import detect_qr_and_urls
from .logo import compute_reference_hash
from .models import ComplianceReport
from .report import build_report
from .rules import ALL_RULES, DocumentContext

REFERENCE_LOGO = Path(__file__).resolve().parents[2] / "assets" / "reference_logo" / "contoso_logo.png"


class UnreadablePDF(Exception):
    """The submission cannot be validated at all — not a PDF, missing, or locked.

    Distinct from a document that validates badly. Carries a message meant for a
    person, so a front end can show it without exposing a traceback.
    """


def open_pdf(pdf_path: str) -> pymupdf.Document:
    """Open a submission, or fail with something worth showing a reviewer.

    An encrypted PDF opens without complaint and only fails later when a page is
    read, so opening it successfully is not enough to know it can be validated.
    """
    try:
        doc = pymupdf.open(pdf_path)
    except Exception as exc:
        raise UnreadablePDF(f"Could not open '{Path(pdf_path).name}' as a PDF: {exc}") from exc

    if doc.needs_pass:
        doc.close()
        raise UnreadablePDF(f"'{Path(pdf_path).name}' is password-protected. Supply an unlocked copy.")
    return doc


def run_pipeline(pdf_path: str) -> ComplianceReport:
    doc = open_pdf(pdf_path)
    try:
        context = DocumentContext(
            text_spans=build_text_spans(doc),
            regions=_extract_regions(doc),
            pdf=doc,
            reference_logo_hash=compute_reference_hash(str(REFERENCE_LOGO)) if REFERENCE_LOGO.exists() else None,
        )

        findings = [finding for rule in ALL_RULES for finding in rule.check(context)]
        findings += detect_qr_and_urls(doc, context.regions)
        rule_ids = [rule.id for rule in ALL_RULES] + ["QR-LINK"]

        return build_report(Path(pdf_path).name, rule_ids, findings, context.regions)
    finally:
        doc.close()


def _extract_regions(doc: pymupdf.Document) -> list:
    ids = itertools.count()
    regions = []
    for page_index in range(len(doc)):
        page = doc[page_index]
        page_number = page_index + 1
        from_annotations = extract_annotations(page, page_number, ids)
        regions += from_annotations
        regions += extract_handdrawn_boxes(page, page_number, from_annotations, ids)
    return merge_regions(regions)
