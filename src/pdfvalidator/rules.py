"""The CHN rulebook. Every rule is deterministic — see README for why no LLM."""

import re
from dataclasses import dataclass
from typing import Protocol

import imagehash
import pymupdf

from .logo import find_logo_matches
from .models import Finding, Region, TextSpan

# --------------------------------------------------------------------------- #
# Required wording (§2 of the CHN standards)
# --------------------------------------------------------------------------- #

CHN_FIRST_MENTION = "Contoso Health Network® (CHN®)"
STANDARDS_FIRST_MENTION = "Contoso Health Network Clinical Practice Standards (CHN Clinical Standards™)"
STANDARDS_SECOND_MENTION = "CHN Clinical Standards™"
STANDARDS_SHORT = "CHN Clinical Standards"

DISCLAIMER = (
    "CHN makes no warranties of any kind regarding this content, its use, or application, "
    "and disclaims any responsibility for its application or use in any way."
)

TIER_DEFINITIONS = {
    "A": "Based upon high-quality evidence, there is uniform CHN panel consensus (≥85% support) that the approach is appropriate.",
    "B": "Based upon lower-level evidence, there is uniform CHN panel consensus (≥85% support) that the approach is appropriate.",
    "C": "Based upon lower-level evidence, there is majority CHN panel consensus (≥50%, but <85% support) that the approach is appropriate.",
}

CITATION_ELEMENTS = {
    "topic name": re.compile(r"for\s+(.+?)\s+V\.\s*\d", re.IGNORECASE),
    "version number": re.compile(r"V\.\s*\d+(?:\.\d+)*", re.IGNORECASE),
    "copyright year": re.compile(r"(?:©|Copyright)[^\d]{0,50}(\d{4})", re.IGNORECASE),
    "access date": re.compile(r"Accessed\s+[A-Za-z]+\s+\d{1,2},?\s+\d{4}", re.IGNORECASE),
    "contosohealth.org reference": re.compile(r"contosohealth\.org", re.IGNORECASE),
}

_CITATION_MARKER = re.compile(r"Referenced with permission from", re.IGNORECASE)
_LICENSE_REFERENCE = re.compile(r"agreement\s+CHN-\d{4}-\d+", re.IGNORECASE)
_TIER_LABEL = re.compile(r"Tier\s+([ABC])\b", re.IGNORECASE)
_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+")
_WHITESPACE = re.compile(r"\s+")

# Longest form first so a short form never matches inside a longer one it is part of.
# `CHN\b(?!-\d)` keeps an agreement ID like "CHN-2026-014" from counting as a
# trademark mention; "CHN-approved" still does.
_MENTION = re.compile("|".join([
    f"(?P<standards_first>{re.escape(STANDARDS_FIRST_MENTION)})",
    f"(?P<chn_first>{re.escape(CHN_FIRST_MENTION)})",
    f"(?P<standards_second>{re.escape(STANDARDS_SECOND_MENTION)})",
    f"(?P<standards_short>{re.escape(STANDARDS_SHORT)})",
    r"(?P<chn_bare>CHN\b(?!-\d))",
]), re.IGNORECASE)

_CHN_FIRST_RE = re.compile(re.escape(CHN_FIRST_MENTION), re.IGNORECASE)
_STANDARDS_FIRST_RE = re.compile(re.escape(STANDARDS_FIRST_MENTION), re.IGNORECASE)
_DISCLAIMER_RE = re.compile(re.escape(_WHITESPACE.sub(" ", DISCLAIMER)), re.IGNORECASE)


def normalize(text: str) -> str:
    """Collapse whitespace.

    PyMuPDF's block text carries a literal newline wherever the PDF happens to wrap
    a line, mid-phrase included. That is a layout artifact, not a paraphrase, so it
    is flattened before any match — otherwise a verbatim reproduction of a required
    sentence fails purely because of where the line broke.
    """
    return _WHITESPACE.sub(" ", text)


def is_citation_block(text: str) -> bool:
    """A citation reproduces the standards' published name; it is not fresh prose.

    This is the one semantic judgment the assessment allows an LLM for. A citation
    announces itself with a fixed lead-in, so a regex answers it exactly and for
    free — see README, "Why there is no LLM".
    """
    return bool(_CITATION_MARKER.search(normalize(text)))


@dataclass
class DocumentContext:
    text_spans: list[TextSpan]
    regions: list[Region]
    pdf: pymupdf.Document | None = None
    reference_logo_hash: "imagehash.ImageHash | None" = None


class Rule(Protocol):
    id: str

    def check(self, doc: DocumentContext) -> list[Finding]: ...


# --------------------------------------------------------------------------- #
# CHN-1 / CHN-2 / CHN-3 — naming sequences (§2.1)
# --------------------------------------------------------------------------- #

class NamingSequenceRule:
    """Tracks first-mention state across the whole document, deterministically.

    Two independent counters: bare "CHN" and the "CHN Clinical Standards" family.
    A bare "CHN" inside a standards phrase belongs to the family only — the regex
    consumes the longer phrase first, so family precedence falls out for free.
    """

    id = "NAMING-SEQUENCE"

    def check(self, doc: DocumentContext) -> list[Finding]:
        findings: list[Finding] = []
        chn_first_seen = False
        standards_count = 0

        for span in doc.text_spans:
            text = normalize(span.text)
            if is_citation_block(text):
                continue

            sentences = _sentence_bounds(text)
            for match in _MENTION.finditer(text):
                kind, matched = match.lastgroup, match.group()

                if kind in ("standards_first", "standards_second", "standards_short"):
                    standards_count += 1
                    problem = _standards_problem(kind, standards_count)
                    if problem:
                        findings.append(_violation("CHN-2", span, matched, problem))
                elif kind == "chn_first":
                    chn_first_seen = True
                elif not chn_first_seen and not _CHN_FIRST_RE.search(_sentence_at(text, sentences, match.start())):
                    # A headline can place a bare "CHN" ahead of the full form in the
                    # same breath ("TWO CHN TIER A RECOMMENDATIONS FROM CONTOSO HEALTH
                    # NETWORK® (CHN®)..."); a reader meets both at once. Scoping the
                    # exemption to the sentence mirrors CHN-3 and still catches a bare
                    # "CHN" standing as its own sentence before any introduction.
                    findings.append(_violation(
                        "CHN-1", span, matched,
                        f"Bare 'CHN' used before the required first-mention form "
                        f"'{CHN_FIRST_MENTION}' appeared anywhere earlier in the document",
                    ))

        return findings + self._check_combination(doc.text_spans)

    def _check_combination(self, text_spans: list[TextSpan]) -> list[Finding]:
        findings = []
        for span in text_spans:
            for sentence in _SENTENCE_BREAK.split(normalize(span.text)):
                if _CHN_FIRST_RE.search(sentence) and _STANDARDS_FIRST_RE.search(sentence):
                    findings.append(_violation(
                        "CHN-3", span, sentence.strip(),
                        "Both first-mention forms were introduced together in the same sentence",
                    ))
        return findings


def _standards_problem(kind: str, count: int) -> str | None:
    """The form required at this occurrence: full, then ™, then short."""
    if kind == "standards_first" and count != 1:
        return f"'{STANDARDS_FIRST_MENTION}' form used at occurrence #{count}; it must only appear as the 1st occurrence"
    if kind == "standards_second" and count != 2:
        return f"'{STANDARDS_SECOND_MENTION}' form used at occurrence #{count}; it must only appear as the 2nd occurrence"
    if kind == "standards_short" and count < 3:
        ordinal = "1st" if count == 1 else "2nd"
        return f"Bare '{STANDARDS_SHORT}' used at occurrence #{count}; the {ordinal} occurrence must use the required trademark form"
    return None


# --------------------------------------------------------------------------- #
# Category rating definitions (§2.2)
# --------------------------------------------------------------------------- #

class CategoryDefinitionRule:
    """A stated Tier rating must be accompanied by its definition, word for word.

    The rating and its definition are almost never the same text block — a "TIER A"
    badge up top, the sentence in a footnote below — so the whole page is searched.
    Not the whole document: a definition on another page is not "nearby".
    """

    id = "CAT-DEF"

    def check(self, doc: DocumentContext) -> list[Finding]:
        page_text: dict[int, str] = {}
        for span in doc.text_spans:
            page_text[span.page] = page_text.get(span.page, "") + " " + normalize(span.text)

        findings, reported = [], set()
        for span in doc.text_spans:
            for match in _TIER_LABEL.finditer(span.text):
                tier = match.group(1).upper()
                if (span.page, tier) in reported or TIER_DEFINITIONS[tier] in page_text[span.page]:
                    continue
                # One finding per rating per page: a page naming "Tier A" five times
                # has one problem, and repeating it five times makes a report harder
                # to act on, not more informative.
                reported.add((span.page, tier))
                findings.append(Finding(
                    rule_id=self.id, confidence="confirmed", page=span.page, bbox=span.bbox,
                    snippet=span.text[:200],
                    explanation=f"Tier {tier} rating stated but the required exact definition text is missing or paraphrased nearby.",
                ))
        return findings


# --------------------------------------------------------------------------- #
# Citation format (§2.3)
# --------------------------------------------------------------------------- #

class CitationFormatRule:
    """All five elements must be present in a citation block, in any order."""

    id = "CITATION"

    def check(self, doc: DocumentContext) -> list[Finding]:
        findings = []
        for span in doc.text_spans:
            text = normalize(span.text)
            if not is_citation_block(text):
                continue
            missing = [name for name, pattern in CITATION_ELEMENTS.items() if not pattern.search(text)]
            if missing:
                findings.append(Finding(
                    rule_id=self.id, confidence="confirmed", page=span.page, bbox=span.bbox,
                    snippet=span.text[:300],
                    explanation=f"Citation block is missing required element(s): {', '.join(missing)}.",
                ))
        return findings


# --------------------------------------------------------------------------- #
# Mandatory disclaimer (§2.4)
# --------------------------------------------------------------------------- #

class DisclaimerRule:
    """Document-level: the disclaimer must appear at least once, anywhere."""

    id = "DISCLAIMER"

    def check(self, doc: DocumentContext) -> list[Finding]:
        if any(_DISCLAIMER_RE.search(normalize(span.text)) for span in doc.text_spans):
            return []
        return [Finding(
            rule_id=self.id, confidence="confirmed", page=1, bbox=None, snippet="",
            explanation="Mandatory CHN disclaimer statement was not found anywhere in the document.",
        )]


# --------------------------------------------------------------------------- #
# Logo usage (§2.5)
# --------------------------------------------------------------------------- #

class LogoLicenseRule:
    """A reproduced logo needs a license reference near it, or a human looks at it.

    A match with a license is reported as confirmed-compliant rather than a
    violation; a match without one is handed to a reviewer rather than called a
    violation, since only they can confirm the agreement is real and active.
    """

    id = "LOGO-LICENSE"

    # Measured against Sample-06: the logo region sits ~3-6pt from the license
    # caption. A wider margin would reach unrelated page furniture and risk
    # silently clearing an unlicensed logo.
    NEARBY_MARGIN = 20

    def __init__(self, max_distance: int = 8):
        self.max_distance = max_distance

    def check(self, doc: DocumentContext) -> list[Finding]:
        if doc.reference_logo_hash is None or doc.pdf is None:
            return []

        findings = []
        for region, distance in find_logo_matches(doc.pdf, doc.regions, doc.reference_logo_hash, self.max_distance):
            licensed = bool(_LICENSE_REFERENCE.search(self._nearby_text(doc.pdf, region)))
            findings.append(Finding(
                rule_id=self.id,
                confidence="confirmed" if licensed else "needs_review",
                page=region.page, bbox=region.bbox, snippet=region.text[:200], region_id=region.id,
                explanation=(
                    f"Logo detected (hash distance {distance}); license reference found nearby — provisionally compliant."
                    if licensed else
                    f"Logo detected (hash distance {distance}); no license/agreement reference found nearby — flag for reviewer."
                ),
            ))
        return findings

    def _nearby_text(self, pdf: pymupdf.Document, region: Region) -> str:
        page = pdf[region.page - 1]
        margin = self.NEARBY_MARGIN
        padded = pymupdf.Rect(region.bbox) + (-margin, -margin, margin, margin)
        padded.intersect(page.rect)
        return page.get_textbox(padded)


ALL_RULES: list[Rule] = [
    NamingSequenceRule(),
    CategoryDefinitionRule(),
    CitationFormatRule(),
    DisclaimerRule(),
    LogoLicenseRule(),
]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _violation(rule_id: str, span: TextSpan, snippet: str, explanation: str) -> Finding:
    return Finding(
        rule_id=rule_id, confidence="confirmed", page=span.page, bbox=span.bbox,
        snippet=snippet, explanation=explanation,
    )


def _sentence_bounds(text: str) -> list[tuple[int, int]]:
    bounds, start = [], 0
    for match in _SENTENCE_BREAK.finditer(text):
        bounds.append((start, match.start()))
        start = match.end()
    bounds.append((start, len(text)))
    return bounds


def _sentence_at(text: str, bounds: list[tuple[int, int]], position: int) -> str:
    for start, end in bounds:
        if start <= position < end:
            return text[start:end]
    return text
