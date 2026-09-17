"""Turn a PDF into the two things every rule needs: flagged regions and ordered text."""

from dataclasses import replace
from typing import Iterator

import pymupdf

from .models import Region, TextSpan

# A reviewer marks content two ways: with their tool's text-markup feature, or by
# drawing a shape around it. Sticky notes and text boxes are the reviewer talking
# to their own team, not submitted content.
TEXT_MARKUP_SUBTYPES = {"Highlight", "Underline", "Squiggly", "StrikeOut"}
SHAPE_SUBTYPES = {"Square", "Circle"}
REVIEWER_NOTE_SUBTYPES = {"FreeText", "Text"}

_MERGE_IOU = 0.6
_DUPLICATE_IOU = 0.9

# A drawn box encloses content. A rule, underline or hairline is a rectangle with
# no area — Sample-06's header rule is 532pt wide and 0pt tall.
_MIN_BOX_SIDE = 10


# --------------------------------------------------------------------------- #
# Regions
# --------------------------------------------------------------------------- #

def extract_annotations(page: pymupdf.Page, page_number: int, id_counter: Iterator[int]) -> list[Region]:
    """Regions from the annotation layer, skipping the reviewer's own notes."""
    regions: list[Region] = []
    for annot in page.annots():
        subtype = annot.type[1]
        if subtype in TEXT_MARKUP_SUBTYPES:
            bbox = _quad_bbox(annot)
            regions.append(_region(page, page_number, bbox, "native_annotation", subtype, annot, id_counter))
        elif subtype in SHAPE_SUBTYPES:
            regions.append(_region(page, page_number, tuple(annot.rect), "hand_drawn", subtype, annot, id_counter))
    return regions


def extract_handdrawn_boxes(
    page: pymupdf.Page, page_number: int, existing_regions: list[Region], id_counter: Iterator[int],
) -> list[Region]:
    """Fallback for boxes drawn as plain vector paths rather than annotations.

    Three things are deliberately not regions:

    - Curved paths. A decorative blob reports a rectangular bounding box, so the
      path's own segments are inspected instead (Sample-04 page 1).
    - Solid fills with no outline. A reviewer draws an outline around content;
      a solid block of brand colour is page furniture. Sample-04's navigation tab
      bar is five filled rectangles repeated on every page — 21 of them, each
      containing real text, and none of them flagged by anyone.
    - Anything inside a reviewer's note. The note's own border is a stroked
      rectangle, and its text is already excluded from the text stream.
    - Rules and hairlines, which are rectangles with no area.
    """
    note_rects = [a.rect for a in page.annots() if a.type[1] in REVIEWER_NOTE_SUBTYPES]
    regions: list[Region] = []
    for drawing in page.get_drawings():
        items = drawing.get("items", [])
        rect = drawing.get("rect")
        if not items or rect is None or not _is_rectangular_path(items):
            continue
        if not _has_outline(drawing) or not _encloses_area(rect):
            continue
        bbox = (rect.x0, rect.y0, rect.x1, rect.y1)
        if _sits_inside_note(bbox, note_rects):
            continue
        color = tuple(drawing["color"]) if drawing.get("color") else None
        if _duplicates_annotation(bbox, color, page_number, existing_regions):
            continue
        regions.append(Region(
            id=f"region-{next(id_counter)}", page=page_number, bbox=bbox,
            text=page.get_textbox(pymupdf.Rect(bbox)), source="hand_drawn", subtype="Drawing", color=color,
        ))
    return regions


def merge_regions(regions: list[Region]) -> list[Region]:
    """Collapse regions covering the same content so it is reported once.

    A native annotation wins over a hand-drawn box on the same content: it carries
    the PDF tool's own deliberate semantics, while shape detection is a heuristic
    with real false-positive risk. The loser is recorded in `merged_from`.
    """
    remaining = list(regions)
    merged: list[Region] = []
    while remaining:
        current = remaining.pop(0)
        index = 0
        while index < len(remaining):
            other = remaining[index]
            if current.page == other.page and iou(current.bbox, other.bbox) >= _MERGE_IOU:
                current = _combine(current, other)
                remaining.pop(index)
                index = 0
            else:
                index += 1
        merged.append(current)
    return merged


def iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    inter = _intersection_area(a, b)
    union = _area(a) + _area(b) - inter
    return inter / union if union > 0 else 0.0


# --------------------------------------------------------------------------- #
# Text
# --------------------------------------------------------------------------- #

def build_text_spans(doc: pymupdf.Document) -> list[TextSpan]:
    """Every text block in the document, in reading order (page, then y, then x).

    Rules scan this rather than only the flagged regions: in Sample-01 the required
    first-mention form sits in an unflagged title, so a region-only scan would
    report violations for a compliant document.

    Text belonging to a reviewer's note is dropped. Those notes are drawn into the
    page content as well as stored on the annotation, so without this they would be
    scanned as if the submitter had written them (Sample-04's "Note to CHN: CHN
    content is located on slide 3" otherwise reports two CHN-1 violations).
    """
    spans: list[TextSpan] = []
    for page_index in range(len(doc)):
        page = doc[page_index]
        page_number = page_index + 1
        note_rects = [a.rect for a in page.annots() if a.type[1] in REVIEWER_NOTE_SUBTYPES]
        for x0, y0, x1, y1, text, _block_no, block_type in page.get_text("blocks"):
            bbox = (x0, y0, x1, y1)
            if block_type != 0 or not text.strip() or _sits_inside_note(bbox, note_rects):
                continue
            spans.append(TextSpan(page=page_number, bbox=bbox, text=text, order_key=(page_number, y0, x0)))
    spans.sort(key=lambda span: span.order_key)
    return spans


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _region(page, page_number, bbox, source, subtype, annot, id_counter) -> Region:
    stroke = (annot.colors or {}).get("stroke")
    return Region(
        id=f"region-{next(id_counter)}", page=page_number, bbox=bbox,
        text=page.get_textbox(pymupdf.Rect(bbox)), source=source, subtype=subtype,
        color=tuple(stroke) if stroke else None,
    )


def _quad_bbox(annot) -> tuple[float, float, float, float]:
    """Text markup stores one quad per covered line; take the enclosing box."""
    vertices = annot.vertices or []
    rects = [pymupdf.Quad(vertices[i:i + 4]).rect for i in range(0, len(vertices), 4)]
    if not rects:
        return tuple(annot.rect)
    return (
        min(r.x0 for r in rects), min(r.y0 for r in rects),
        max(r.x1 for r in rects), max(r.y1 for r in rects),
    )


def _is_rectangular_path(items: list[tuple]) -> bool:
    kinds = {item[0] for item in items}
    return "c" not in kinds and kinds.issubset({"re", "l"})


def _has_outline(drawing: dict) -> bool:
    """PyMuPDF's type is "s" (stroke), "f" (fill) or "fs" (both)."""
    return drawing.get("type") in ("s", "fs")


def _encloses_area(rect) -> bool:
    return (rect.x1 - rect.x0) >= _MIN_BOX_SIDE and (rect.y1 - rect.y0) >= _MIN_BOX_SIDE


def _duplicates_annotation(bbox, color, page_number: int, existing_regions: list[Region]) -> bool:
    return any(
        region.page == page_number and region.color == color and iou(bbox, region.bbox) >= _DUPLICATE_IOU
        for region in existing_regions
    )


def _combine(a: Region, b: Region) -> Region:
    if b.source == "native_annotation" and a.source != "native_annotation":
        canonical, absorbed = b, a
    else:
        canonical, absorbed = a, b
    union_bbox = (
        min(a.bbox[0], b.bbox[0]), min(a.bbox[1], b.bbox[1]),
        max(a.bbox[2], b.bbox[2]), max(a.bbox[3], b.bbox[3]),
    )
    return replace(
        canonical, bbox=union_bbox,
        merged_from=[*canonical.merged_from, absorbed.id, *absorbed.merged_from],
    )


def _sits_inside_note(bbox, note_rects, threshold: float = 0.5) -> bool:
    area = _area(bbox)
    if area <= 0:
        return False
    return any(
        _intersection_area(bbox, tuple(rect)) / area >= threshold
        for rect in note_rects
    )


def _area(bbox: tuple[float, float, float, float]) -> float:
    x0, y0, x1, y1 = bbox
    return max(0.0, x1 - x0) * max(0.0, y1 - y0)


def _intersection_area(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    return max(0.0, min(ax1, bx1) - max(ax0, bx0)) * max(0.0, min(ay1, by1) - max(ay0, by0))
