"""Shared builders. Rule tests use plain text spans; extraction tests use real PDFs."""

import itertools
from pathlib import Path

import pymupdf
import pytest

from pdfvalidator.models import Region, TextSpan
from pdfvalidator.rules import DocumentContext

SAMPLES_DIR = Path(__file__).resolve().parents[1] / "CHN Generated Samples"


@pytest.fixture
def ids():
    return itertools.count()


def span(text: str, page: int = 1, index: int = 0) -> TextSpan:
    top = index * 20
    return TextSpan(page=page, bbox=(0, top, 400, top + 15), text=text, order_key=(page, top, 0))


def context(*texts: str) -> DocumentContext:
    """A document whose text is these blocks, in order, all on page 1."""
    return DocumentContext(text_spans=[span(t, index=i) for i, t in enumerate(texts)], regions=[])


def paged_context(*blocks: tuple[int, str]) -> DocumentContext:
    """A document whose text is these (page, text) blocks."""
    spans = [span(text, page=page, index=i) for i, (page, text) in enumerate(blocks)]
    return DocumentContext(text_spans=spans, regions=[])


def region(id_: str = "r1", page: int = 1, bbox=(0, 0, 100, 20), text: str = "CHN content",
           source: str = "native_annotation") -> Region:
    return Region(id=id_, page=page, bbox=bbox, text=text, source=source, subtype="Highlight", color=None)


def build_pdf(tmp_path, lines: list[str], name: str = "doc.pdf", width: int = 900, height: int = 800) -> str:
    """A single-page PDF with one text line per entry.

    Wide by default so a long line (the disclaimer especially) is not clipped at
    the page edge, which would silently change what the rules see.
    """
    doc = pymupdf.open()
    page = doc.new_page(width=width, height=height)
    y = 100
    for line in lines:
        page.insert_text((72, y), line, fontsize=10)
        y += 20
    path = tmp_path / name
    doc.save(path)
    doc.close()
    return str(path)
