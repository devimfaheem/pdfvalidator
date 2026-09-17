"""Find reproductions of the CHN logo inside flagged regions."""

import io

import imagehash
import pymupdf
from PIL import Image

from .models import Region


def compute_reference_hash(reference_logo_path: str) -> imagehash.ImageHash:
    return imagehash.phash(Image.open(reference_logo_path))


def find_logo_matches(
    pdf: pymupdf.Document,
    regions: list[Region],
    reference_hash: imagehash.ImageHash,
    max_distance: int = 8,
) -> list[tuple[Region, int]]:
    """Images inside a flagged region whose perceptual hash is close to the reference.

    Perceptual hashing rather than byte comparison: a logo in a submitted document
    has usually been resized, recompressed, or re-exported on its way there.
    """
    matches = []
    for region in regions:
        page = pdf[region.page - 1]
        region_rect = pymupdf.Rect(region.bbox)
        for xref, *_ in page.get_images(full=True):
            if not any(region_rect.intersects(rect) for rect in page.get_image_rects(xref)):
                continue
            image = Image.open(io.BytesIO(pdf.extract_image(xref)["image"]))
            distance = reference_hash - imagehash.phash(image)
            if distance <= max_distance:
                matches.append((region, distance))
    return matches
