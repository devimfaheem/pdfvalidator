# Tasks

Implementation plan traced to [requirements.md](requirements.md). Every task names
the requirements it satisfies, the code that implements it, and the tests that hold
it in place.

**Status.** T-1 through T-11 are complete and verified: 71 tests pass, `ruff` is
clean, and all six samples produce committed output. T-12 onward are open, ordered by
what I would pick up next.

---

## Completed

### T-1 — Data model
**Requirements:** R1.4, R9.4 · **Code:** `models.py` · **Tests:** covered via consumers

Four dataclasses with no behaviour: `Region`, `TextSpan`, `Finding`,
`ComplianceReport`. Keeping them inert is what lets rule tests construct inputs
directly without touching a PDF (R11.6).

### T-2 — Annotation extraction
**Requirements:** R1.1, R1.2, R1.4, R1.5, R1.8 · **Code:** `extract.py::extract_annotations` · **Tests:** `test_extract.py` (13)

Text-markup subtypes become `native_annotation`; shape subtypes become `hand_drawn`;
`FreeText` and `Text` are skipped. Quad points resolve to the enclosing box so a
multi-line highlight yields one region.

### T-3 — Vector-path fallback
**Requirements:** R1.3, R1.9–R1.12 · **Code:** `extract.py::extract_handdrawn_boxes` · **Tests:** `test_extract.py`

Four exclusions, each answering an observed false positive: curve segments
(decorative blobs), fill with no outline (navigation bars), no enclosed area (header
rules), and anything inside a reviewer note.

### T-4 — Overlap merging
**Requirements:** R1.6, R1.7 · **Code:** `extract.py::merge_regions` · **Tests:** `test_extract.py`

IoU ≥ 0.6 merges; a native annotation wins over a hand-drawn region and the loser's
id lands in `merged_from`. Verified live on Sample 01, where two regions were
absorbed this way.

### T-5 — Ordered text stream
**Requirements:** R2.1–R2.4 · **Code:** `extract.py::build_text_spans` · **Tests:** `test_extract.py`

Blocks sorted by `(page, y, x)`, with reviewer-note text excluded. The exclusion is
separate from T-2's because a note's text is painted into page content as well as
stored on the annotation.

### T-6 — Naming sequence rules
**Requirements:** R3.1–R3.10 · **Code:** `rules.py::NamingSequenceRule` · **Tests:** `test_rules.py` (29)

One ordered walk, two counters, longest-form-first matching. Includes the citation
exemption, the same-sentence headline exemption, and the identifier carve-out.

### T-7 — Text rules
**Requirements:** R4, R5, R6 · **Code:** `rules.py` (`CategoryDefinitionRule`, `CitationFormatRule`, `DisclaimerRule`) · **Tests:** `test_rules.py`

Category definitions match case-sensitively within a page and dedupe per page and
tier; citations check five elements in any order; the disclaimer is document-level.

### T-8 — Links and QR codes
**Requirements:** R8.1–R8.6 · **Code:** `links.py` · **Tests:** `test_links.py` (4)

Region bbox padded by 15pt, rendered to pixels for decoding. Every hit is
needs-review by construction — there is no code path that makes a link a violation.

### T-9 — Logo matching
**Requirements:** R7.1–R7.6 · **Code:** `logo.py`, `rules.py::LogoLicenseRule` · **Tests:** `test_logo.py` (2), `test_rules.py`

Perceptual hash within distance 8, licence reference within 20pt. The margin was
measured against Sample 06, where the gap is roughly 3–6pt.

### T-10 — Report
**Requirements:** R9.1–R9.10 · **Code:** `report.py` · **Tests:** `test_report.py` (12)

Status aggregation, three-way section split, JSON as source of truth with Markdown
rendered from it, and the region inventory.

### T-11 — Input handling
**Requirements:** R10.1–R10.5 · **Code:** `pipeline.py::open_pdf`, `cli.py`, `web/app.py` · **Tests:** `test_pipeline.py` (5)

`UnreadablePDF` is the single definition of an unvalidatable input, shared by both
front doors. Encryption is checked explicitly because an encrypted PDF opens fine and
only fails on page read.

### T-E2E — Sample packet verification
**Requirements:** all · **Tests:** `test_samples.py` (6) · **Output:** `sample-output/`

Expectations derived by reading each PDF, not by recording tool output. Regenerated
twice and diffed to confirm R11.4.

---

## Open

### T-12 — OCR for pages with no text layer
**Requirements:** would extend R2 · **Priority:** highest

A scanned page yields no text spans, so no rule can judge it. Today those regions
count unevaluable and force `NEEDS_REVIEW` (R9.6), so the gap is visible in the
report rather than hidden — but real submissions include scans.

*Acceptance:* WHEN a page has no text layer THEN the system SHALL OCR it and emit
text spans with a confidence marker distinguishing them from extracted text.

### T-13 — Scope the disclaimer rule to documents containing CHN content
**Requirements:** R6.1 deviation · **Priority:** medium

The brief scopes the disclaimer to "every document containing CHN content"; the
system applies it unconditionally, so a document mentioning CHN nowhere is still
flagged. No sample exercises this, and fixing it needs a definition of "contains CHN
content" that does not weaken the rule for real submissions.

*Acceptance:* WHEN a document contains no CHN reference of any form THEN the system
SHALL NOT raise a DISCLAIMER violation.

### T-14 — Widen citation detection beyond one lead-in phrase
**Requirements:** R5.1, and R3.7 depends on it · **Priority:** medium

Detection keys on `Referenced with permission from`. A citation worded differently is
not recognised, which also silently disables the R3.7 exemption for it. This is the
one place a language model would earn its cost.

*Acceptance:* WHEN a citation block uses wording outside the fixed lead-in THEN the
system SHALL still recognise it, and SHALL record how that judgment was made.

### T-15 — Calibrate the logo threshold against degraded copies
**Requirements:** R7.2 · **Priority:** medium

Both samples embed the byte-identical reference image, so distance 8 is untested
against the resizing and recompression R7.2 exists for.

*Acceptance:* WHEN the reference logo is resized between 50% and 200% or re-encoded
at JPEG quality 60 THEN the system SHALL still match it, and SHALL NOT match an
unrelated logo.

### T-16 — Reading order for multi-column layouts
**Requirements:** R2.1 · **Priority:** low until a multi-column sample exists

`(page, y, x)` traverses a two-column page in the wrong order, and every R3 rule
depends on order. No sample exercises it, so the risk is unmeasured rather than known
to be absent.

*Acceptance:* WHEN a page is laid out in columns THEN the system SHALL order text
spans by column before vertical position.

### T-17 — Strip internal paths from error messages
**Requirements:** R10.4 · **Priority:** low

Messages still carry the underlying library's text, which includes a temp file path.
Not a traceback and not sensitive, but noise for a reviewer.

*Acceptance:* WHEN an input cannot be read THEN the message SHALL name the file and
the reason without an absolute path.

---

## Traceability summary

| Requirement | Tasks | Test file |
|---|---|---|
| R1 Region extraction | T-2, T-3, T-4 | `test_extract.py` |
| R2 Text stream | T-5 | `test_extract.py` |
| R3 Naming sequences | T-6 | `test_rules.py` |
| R4–R6 Text rules | T-7 | `test_rules.py` |
| R7 Logo | T-9 | `test_logo.py`, `test_rules.py` |
| R8 Links | T-8 | `test_links.py` |
| R9 Report | T-10 | `test_report.py` |
| R10 Input handling | T-11 | `test_pipeline.py` |
| R11 Constraints | T-1, T-E2E | whole suite |
