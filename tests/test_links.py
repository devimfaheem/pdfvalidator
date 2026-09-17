import pymupdf

from pdfvalidator.extract import extract_annotations
from pdfvalidator.links import detect_qr_and_urls


def _highlighted_pdf(tmp_path, text: str, add_link_rect=None, link_uri=None):
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 100), text)
    quad = page.search_for(text)[0]
    page.add_highlight_annot(quad)
    if link_uri:
        rect = add_link_rect(quad) if add_link_rect else quad
        page.insert_link({"kind": pymupdf.LINK_URI, "from": rect, "uri": link_uri})
    path = tmp_path / "sample.pdf"
    doc.save(path)
    doc.close()
    return path


def _findings(path, ids):
    doc = pymupdf.open(path)
    findings = detect_qr_and_urls(doc, extract_annotations(doc[0], page_number=1, id_counter=ids))
    doc.close()
    return findings


def test_detects_plain_text_url_inside_a_flagged_region(tmp_path, ids):
    path = _highlighted_pdf(tmp_path, "Visit https://contosohealth.org for more info.")
    findings = _findings(path, ids)

    assert any("contosohealth.org" in f.snippet for f in findings)
    assert all(f.confidence == "needs_review" for f in findings)


def test_url_snippet_excludes_trailing_sentence_punctuation(tmp_path, ids):
    path = _highlighted_pdf(tmp_path, "See our site at https://contosohealth.org.")
    urls = [f.snippet for f in _findings(path, ids) if "contosohealth.org" in f.snippet]

    assert urls
    assert all(url == "https://contosohealth.org" for url in urls)


def test_detects_hyperlink_annotation_inside_a_flagged_region(tmp_path, ids):
    path = _highlighted_pdf(
        tmp_path, "Click here for the CHN Clinical Standards.",
        link_uri="https://contosohealth.org/standards",
    )
    assert any("contosohealth.org/standards" in f.snippet for f in _findings(path, ids))


def test_detects_hyperlink_annotation_adjacent_to_a_flagged_region(tmp_path, ids):
    """"Directly beside" counts, not just "inside" — the link here does not overlap
    the highlight at all, it sits just to its right."""
    path = _highlighted_pdf(
        tmp_path, "Click here for the CHN Clinical Standards.",
        add_link_rect=lambda quad: pymupdf.Rect(quad.x1 + 5, quad.y0, quad.x1 + 60, quad.y1),
        link_uri="https://contosohealth.org/adjacent",
    )
    assert any("contosohealth.org/adjacent" in f.snippet for f in _findings(path, ids))
