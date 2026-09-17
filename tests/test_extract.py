import pymupdf

from conftest import SAMPLES_DIR
from pdfvalidator.extract import (
    build_text_spans,
    extract_annotations,
    extract_handdrawn_boxes,
    iou,
    merge_regions,
)
from pdfvalidator.models import Region


def _region(id_, page, bbox, source, text="CHN content"):
    return Region(id=id_, page=page, bbox=bbox, text=text, source=source, subtype="x", color=None)


# --------------------------------------------------------------------------- #
# Annotations
# --------------------------------------------------------------------------- #

def test_extracts_highlight_and_square_but_not_reviewer_note(tmp_path, ids):
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 100), "Contoso Health Network content for review.")
    page.add_highlight_annot(page.search_for("Contoso Health Network content for review.")[0])
    page.add_rect_annot(pymupdf.Rect(72, 150, 300, 180))
    page.add_freetext_annot(pymupdf.Rect(72, 200, 300, 220), "Note to team: see above")
    path = tmp_path / "sample.pdf"
    doc.save(path)
    doc.close()

    doc = pymupdf.open(path)
    regions = extract_annotations(doc[0], page_number=1, id_counter=ids)
    doc.close()

    assert {r.subtype for r in regions} == {"Highlight", "Square"}
    highlight = next(r for r in regions if r.subtype == "Highlight")
    assert "Contoso Health Network" in highlight.text
    assert highlight.source == "native_annotation"
    assert next(r for r in regions if r.subtype == "Square").source == "hand_drawn"


# --------------------------------------------------------------------------- #
# Hand-drawn boxes
# --------------------------------------------------------------------------- #

def test_handdrawn_captures_rectangles_and_skips_curves(tmp_path, ids):
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 100), "CHN Clinical Standards guidance text.")
    page.draw_rect(pymupdf.Rect(72, 90, 300, 120), color=(1, 0, 0))
    page.draw_circle((400, 400), 30, color=(0.5, 0, 0.5))
    path = tmp_path / "sample.pdf"
    doc.save(path)
    doc.close()

    doc = pymupdf.open(path)
    regions = extract_handdrawn_boxes(doc[0], page_number=1, existing_regions=[], id_counter=ids)
    doc.close()

    assert len(regions) == 1
    assert "CHN Clinical Standards" in regions[0].text


def test_handdrawn_skips_the_repaint_of_a_square_annotation(tmp_path, ids):
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 100), "Sample text inside a reviewer box.")
    square = page.add_rect_annot(pymupdf.Rect(72, 90, 300, 120))
    square.set_colors(stroke=(1, 0, 0))
    square.update()
    path = tmp_path / "sample.pdf"
    doc.save(path)
    doc.close()

    doc = pymupdf.open(path)
    from_annotations = extract_annotations(doc[0], page_number=1, id_counter=ids)
    handdrawn = extract_handdrawn_boxes(doc[0], page_number=1, existing_regions=from_annotations, id_counter=ids)
    doc.close()

    assert len(from_annotations) == 1
    assert handdrawn == []


# --------------------------------------------------------------------------- #
# Merge and precedence
# --------------------------------------------------------------------------- #

def test_iou_of_identical_boxes_is_one():
    assert iou((0, 0, 10, 10), (0, 0, 10, 10)) == 1.0


def test_iou_of_disjoint_boxes_is_zero():
    assert iou((0, 0, 10, 10), (20, 20, 30, 30)) == 0.0


def test_overlapping_regions_merge_with_native_annotation_winning():
    merged = merge_regions([
        _region("h1", 1, (5, 0, 105, 20), "hand_drawn"),
        _region("n1", 1, (0, 0, 100, 20), "native_annotation"),
    ])
    assert len(merged) == 1
    assert merged[0].id == "n1"
    assert merged[0].source == "native_annotation"
    assert "h1" in merged[0].merged_from
    assert merged[0].bbox == (0, 0, 105, 20)


def test_non_overlapping_regions_stay_separate():
    merged = merge_regions([
        _region("a", 1, (0, 0, 10, 10), "native_annotation"),
        _region("b", 1, (200, 200, 210, 210), "native_annotation"),
    ])
    assert len(merged) == 2


# --------------------------------------------------------------------------- #
# Text spans
# --------------------------------------------------------------------------- #

def test_spans_are_ordered_by_page_then_position(tmp_path):
    doc = pymupdf.open()
    page1 = doc.new_page()
    page1.insert_text((72, 300), "Second block on page 1.")
    page1.insert_text((72, 100), "First block on page 1.")
    doc.new_page().insert_text((72, 100), "Block on page 2.")
    path = tmp_path / "sample.pdf"
    doc.save(path)
    doc.close()

    doc = pymupdf.open(path)
    order = [s.text.strip() for s in build_text_spans(doc)]
    doc.close()

    assert order.index("First block on page 1.") < order.index("Second block on page 1.")
    assert order.index("Second block on page 1.") < order.index("Block on page 2.")


def test_reviewer_note_text_is_excluded_from_the_text_stream(tmp_path):
    """A FreeText note is painted into the page content as well as stored on the
    annotation. Without excluding it, the reviewer's own words are scanned as if
    the submitter wrote them — the cause of two false CHN-1 findings in Sample-04.
    """
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 100), "Submitted body content.")
    page.add_freetext_annot(pymupdf.Rect(72, 200, 400, 240), "Note to CHN: CHN content is on slide 3.")
    path = tmp_path / "sample.pdf"
    doc.save(path)
    doc.close()

    doc = pymupdf.open(path)
    texts = " ".join(s.text for s in build_text_spans(doc))
    doc.close()

    assert "Submitted body content." in texts
    assert "Note to CHN" not in texts


def test_sample_04_reviewer_note_is_not_scanned_as_body_text():
    """The same exclusion, against the real packet rather than a synthetic PDF."""
    doc = pymupdf.open(str(SAMPLES_DIR / "CHN-Sample-04-Hand-Drawn-Boxes.pdf"))
    texts = " ".join(s.text for s in build_text_spans(doc))
    doc.close()

    assert "Note to CHN" not in texts
