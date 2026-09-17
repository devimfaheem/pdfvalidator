import pymupdf
from PIL import Image

from pdfvalidator.extract import extract_annotations
from pdfvalidator.logo import compute_reference_hash, find_logo_matches


def test_finds_a_reproduced_logo_inside_a_flagged_region(tmp_path, ids):
    reference_path = tmp_path / "reference.png"
    Image.new("RGB", (64, 64), color=(20, 80, 200)).save(reference_path)

    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_image(pymupdf.Rect(72, 72, 136, 136), filename=str(reference_path))
    page.add_highlight_annot(pymupdf.Rect(70, 70, 138, 138))
    path = tmp_path / "sample.pdf"
    doc.save(path)
    doc.close()

    doc = pymupdf.open(path)
    matches = find_logo_matches(
        doc,
        extract_annotations(doc[0], page_number=1, id_counter=ids),
        compute_reference_hash(str(reference_path)),
    )
    doc.close()

    assert len(matches) == 1
    assert matches[0][1] == 0


def test_ignores_an_image_outside_every_flagged_region(tmp_path, ids):
    reference_path = tmp_path / "reference.png"
    Image.new("RGB", (64, 64), color=(20, 80, 200)).save(reference_path)

    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_image(pymupdf.Rect(72, 72, 136, 136), filename=str(reference_path))
    page.insert_text((72, 400), "Unrelated highlighted text.")
    page.add_highlight_annot(page.search_for("Unrelated highlighted text.")[0])
    path = tmp_path / "sample.pdf"
    doc.save(path)
    doc.close()

    doc = pymupdf.open(path)
    matches = find_logo_matches(
        doc,
        extract_annotations(doc[0], page_number=1, id_counter=ids),
        compute_reference_hash(str(reference_path)),
    )
    doc.close()

    assert matches == []
