"""Surface QR codes and links sitting in or beside flagged regions.

Where the link points is deliberately not evaluated — that judgment is the
reviewer's, so every hit is raised as needs_review rather than a violation.
"""

import re

import pymupdf
from PIL import Image
from pyzbar.pyzbar import decode as decode_qr

from .models import Finding, Region

_URL = re.compile(r'https?://[^\s<>"]+|www\.[^\s<>"]+', re.IGNORECASE)
_TRAILING_PUNCTUATION = '.,;:!?]}\'"'

# "Inside or directly beside" a region — enough to catch a QR code or caption that
# sits just outside the highlight the reviewer drew around it.
_ADJACENCY_PADDING = 15


def detect_qr_and_urls(pdf: pymupdf.Document, regions: list[Region]) -> list[Finding]:
    findings: list[Finding] = []
    for region in regions:
        page = pdf[region.page - 1]
        findings.extend(_plain_text_urls(region))
        findings.extend(_link_annotations(page, region))
        findings.extend(_qr_codes(page, region))
    return findings


def _plain_text_urls(region: Region) -> list[Finding]:
    return [
        _flag(region, url, f"URL found in flagged region: {url}")
        for url in (_trim(match.group(0)) for match in _URL.finditer(region.text))
    ]


def _link_annotations(page: pymupdf.Page, region: Region) -> list[Finding]:
    findings = []
    search_area = _padded(region.bbox)
    for link in page.get_links():
        uri = link.get("uri")
        if uri and search_area.intersects(pymupdf.Rect(link["from"])):
            findings.append(_flag(
                region, uri, f"Hyperlink annotation found near flagged region: {uri}",
                bbox=tuple(pymupdf.Rect(link["from"])),
            ))
    return findings


def _qr_codes(page: pymupdf.Page, region: Region) -> list[Finding]:
    clip = _padded(region.bbox)
    clip.intersect(page.rect)
    if clip.is_empty:
        return []
    pixmap = page.get_pixmap(clip=clip, colorspace=pymupdf.csRGB, alpha=False)
    image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
    return [
        _flag(region, data, f"QR code detected in flagged region, decodes to: {data}")
        for data in (qr.data.decode("utf-8", errors="replace") for qr in decode_qr(image))
    ]


def _flag(region: Region, snippet: str, explanation: str, bbox=None) -> Finding:
    return Finding(
        rule_id="QR-LINK", confidence="needs_review", page=region.page,
        bbox=bbox or region.bbox, snippet=snippet, explanation=explanation, region_id=region.id,
    )


def _padded(bbox: tuple[float, float, float, float]) -> pymupdf.Rect:
    x0, y0, x1, y1 = bbox
    pad = _ADJACENCY_PADDING
    return pymupdf.Rect(x0 - pad, y0 - pad, x1 + pad, y1 + pad)


def _trim(url: str) -> str:
    """Drop punctuation that belongs to the sentence, not the URL."""
    while url:
        if url[-1] in _TRAILING_PUNCTUATION or (url[-1] == ")" and url.count(")") > url.count("(")):
            url = url[:-1]
        else:
            break
    return url
