# Feature Specification: CHN PDF Compliance Validator

**Feature Branch**: `001-chn-compliance-validator`
**Created**: 2026-10-06
**Status**: Implemented
**Input**: Contoso Health Network content-compliance brief (6 tasks, 8 content rules)

Source of truth for what the validator must do. Acceptance criteria are written in
EARS form (`WHEN <trigger> THEN the system SHALL <response>`) so each one is directly
testable.

**Status of this document.** The system was built first and these requirements were
derived from the brief and from behaviour verified against the provided sample
packet. They are the source of truth from here on: a change to behaviour starts with
a change here.

Governed by [the project constitution](../../.specify/memory/constitution.md).
Design in [plan.md](plan.md); traceability to code and tests in [tasks.md](tasks.md).

---

## R1 — Region extraction

**User story.** As a compliance reviewer, I want every region a submitter marked for
review extracted from the PDF, so I can see what was flagged without opening the file.

| # | Acceptance criterion |
|---|---|
| 1.1 | WHEN a page carries a text-markup annotation (`Highlight`, `Underline`, `Squiggly`, `StrikeOut`) THEN the system SHALL emit a region with `source = "native_annotation"` |
| 1.2 | WHEN a page carries a shape annotation (`Square`, `Circle`) THEN the system SHALL emit a region with `source = "hand_drawn"` |
| 1.3 | WHEN a page carries a stroked rectangular vector path that matches no annotation THEN the system SHALL emit a region with `source = "hand_drawn"` |
| 1.4 | The system SHALL record page number, bounding box, verbatim underlying text, and detection method for every region |
| 1.5 | The system SHALL NOT alter, clean, or paraphrase extracted text |
| 1.6 | WHEN two regions on one page overlap with IoU ≥ 0.6 THEN the system SHALL merge them into one region covering the union of their boxes |
| 1.7 | WHEN a merge joins a native annotation and a hand-drawn region THEN the native annotation SHALL be canonical and the absorbed region's id SHALL be recorded in `merged_from` |
| 1.8 | WHEN an annotation is `FreeText` or `Text` THEN the system SHALL NOT emit a region for it |
| 1.9 | WHEN a vector path is filled with no outline THEN the system SHALL NOT emit a region for it |
| 1.10 | WHEN a vector path is narrower or shorter than 10pt THEN the system SHALL NOT emit a region for it |
| 1.11 | WHEN a vector path lies inside a reviewer-note annotation THEN the system SHALL NOT emit a region for it |
| 1.12 | WHEN a vector path is built from curve segments THEN the system SHALL NOT emit a region for it |

**Rationale for 1.9–1.12.** Each exclusion answers a false positive observed in the
packet: a navigation tab bar (21 filled rectangles), a 0pt-tall header rule, a
reviewer's note border, and decorative circles whose bounding box is rectangular.

---

## R2 — Document text in reading order

**User story.** As a rule author, I want the document's text as an ordered stream, so
sequencing rules can reason about what came before what.

| # | Acceptance criterion |
|---|---|
| 2.1 | The system SHALL emit one text span per text block, ordered by page, then vertical position, then horizontal position |
| 2.2 | The system SHALL include text that lies outside any flagged region |
| 2.3 | WHEN a text block lies at least 50% inside a reviewer-note annotation THEN the system SHALL exclude it from the stream |
| 2.4 | WHEN matching required wording THEN the system SHALL collapse whitespace first, so a phrase broken by a line wrap still matches |

**Rationale for 2.2.** Sample 01 carries its required first-mention form in an
unflagged title while the short forms depending on it sit inside flagged panels. A
region-only scan reports violations in a compliant document.

---

## R3 — Trademark naming sequences

**User story.** As CHN, I want the naming rules enforced across a whole document, so a
submission cannot use a short form it never introduced.

| # | Acceptance criterion |
|---|---|
| 3.1 | WHEN a bare `CHN` appears before `Contoso Health Network® (CHN®)` has appeared earlier THEN the system SHALL raise a confirmed CHN-1 violation |
| 3.2 | WHEN a bare `CHN` and the full first-mention form appear in the same sentence THEN the system SHALL NOT raise CHN-1 |
| 3.3 | The system SHALL require the standards name at occurrence 1 to be `Contoso Health Network Clinical Practice Standards (CHN Clinical Standards™)`, at occurrence 2 `CHN Clinical Standards™`, and at occurrence 3 onward `CHN Clinical Standards` |
| 3.4 | WHEN the form used does not match the form required for its occurrence THEN the system SHALL raise a confirmed CHN-2 violation naming both |
| 3.5 | WHEN a bare `CHN` is part of a standards phrase THEN the system SHALL count it only against the standards family and SHALL NOT raise CHN-1 |
| 3.6 | WHEN both first-mention forms are introduced in one sentence THEN the system SHALL raise a confirmed CHN-3 violation |
| 3.7 | WHEN an occurrence sits inside a citation block THEN the system SHALL exclude it from occurrence counting |
| 3.8 | WHEN `CHN` is immediately followed by a hyphen and a digit THEN the system SHALL treat it as an identifier, not a trademark mention |
| 3.9 | The system SHALL match naming forms case-insensitively |
| 3.10 | The system SHALL track occurrence state in its own code and SHALL NOT delegate it to a language model |

**Rationale for 3.7.** Both of Sample 01's citations respell the full standards name.
Counting them would push a later short form to occurrence 5 and invent a violation.

**Rationale for 3.9.** Headings are set in all caps as a styling choice, not different
wording.

---

## R4 — Category rating definitions

| # | Acceptance criterion |
|---|---|
| 4.1 | WHEN a Tier A, B or C rating is stated THEN the system SHALL require that tier's definition to appear verbatim on the same page |
| 4.2 | WHEN the definition is absent or paraphrased THEN the system SHALL raise a confirmed CAT-DEF violation |
| 4.3 | The system SHALL compare definition text case-sensitively |
| 4.4 | WHEN one page states the same tier several times with no definition THEN the system SHALL raise exactly one finding for that page and tier |

---

## R5 — Citation format

| # | Acceptance criterion |
|---|---|
| 5.1 | WHEN a text block contains `Referenced with permission from` THEN the system SHALL treat it as a citation block |
| 5.2 | The system SHALL require five elements in a citation block: topic name, version number, copyright year, access date, and a contosohealth.org reference |
| 5.3 | The system SHALL accept those elements in any order |
| 5.4 | WHEN any element is missing THEN the system SHALL raise a confirmed CITATION violation naming each missing element |

---

## R6 — Mandatory disclaimer

| # | Acceptance criterion |
|---|---|
| 6.1 | The system SHALL require the disclaimer sentence to appear at least once anywhere in the document |
| 6.2 | WHEN it is absent THEN the system SHALL raise a confirmed DISCLAIMER violation with no bounding box, since the finding is document-level |
| 6.3 | The system SHALL match the disclaimer despite line wrapping |

**Known deviation.** The brief scopes this to "every document containing CHN
content". The system applies it unconditionally, so a document with no CHN content
is flagged. No sample exercises this. See [tasks.md](tasks.md) T-13.

---

## R7 — Logo and licence

| # | Acceptance criterion |
|---|---|
| 7.1 | WHEN an image inside a flagged region has a perceptual hash within Hamming distance 8 of the reference logo THEN the system SHALL treat it as a logo reproduction |
| 7.2 | The system SHALL use perceptual hashing, not byte comparison, so a resized or recompressed copy still matches |
| 7.3 | WHEN a licence reference matching `agreement CHN-####-#` appears within 20pt of the region THEN the system SHALL report the use as confirmed and provisionally compliant |
| 7.4 | WHEN no licence reference is near THEN the system SHALL raise a needs-review finding, not a violation |
| 7.5 | A confirmed LOGO-LICENSE finding SHALL NOT count toward the violated-rule total |
| 7.6 | WHEN no reference logo is configured THEN the system SHALL emit no logo findings |

---

## R8 — Links and QR codes

| # | Acceptance criterion |
|---|---|
| 8.1 | WHEN a QR code is inside or within 15pt of a flagged region THEN the system SHALL decode it and surface the target |
| 8.2 | WHEN a plain-text URL appears in a flagged region's text THEN the system SHALL surface it |
| 8.3 | WHEN a link annotation intersects a flagged region padded by 15pt THEN the system SHALL surface its target |
| 8.4 | Every link or QR finding SHALL be needs-review and SHALL NOT be a violation |
| 8.5 | The system SHALL NOT evaluate whether a link's destination is itself compliant |
| 8.6 | The system SHALL strip sentence punctuation that is not part of a URL |

---

## R9 — Compliance report

**User story.** As a non-technical reviewer, I want one report per document, so I can
act on it without reopening the source PDF.

| # | Acceptance criterion |
|---|---|
| 9.1 | WHEN any confirmed violation exists THEN the overall status SHALL be `FAIL` |
| 9.2 | WHEN no violation exists but a needs-review finding or an unevaluable region does THEN the status SHALL be `NEEDS_REVIEW` |
| 9.3 | WHEN neither exists THEN the status SHALL be `PASS` |
| 9.4 | The report SHALL state rules checked, rules violated, needs-review findings, regions extracted, and regions that could not be evaluated |
| 9.5 | `rules_violated` SHALL count distinct rules, not individual findings |
| 9.6 | WHEN a flagged region yields no text THEN the system SHALL count it as unevaluable |
| 9.7 | Every finding SHALL carry a rule id, page number, text snippet, and plain-language explanation |
| 9.8 | The report SHALL separate confirmed violations, items needing human judgment, and verified-compliant findings into distinct sections |
| 9.9 | The system SHALL write the report as JSON and as Markdown rendered from the same object |
| 9.10 | The report SHALL list every extracted region with its detection method |

---

## R10 — Input handling

| # | Acceptance criterion |
|---|---|
| 10.1 | WHEN the input is missing, unreadable, or not a PDF THEN the system SHALL report a readable message and SHALL NOT emit a report |
| 10.2 | WHEN the input is password-protected THEN the system SHALL say so and SHALL NOT emit a report |
| 10.3 | The CLI SHALL exit 1 on failure or on a `FAIL` status, and 0 otherwise |
| 10.4 | No interface SHALL expose a stack trace or internal filesystem path to the user |
| 10.5 | A document that validates badly SHALL still produce a report; one that cannot be read SHALL produce none |

---

## R11 — Constraints

| # | Acceptance criterion |
|---|---|
| 11.1 | The system SHALL make no language-model call at validation time |
| 11.2 | The system SHALL make no network call at validation time |
| 11.3 | The system SHALL read no environment variables and SHALL require no API key |
| 11.4 | Two runs over one document SHALL produce byte-identical reports |
| 11.5 | The system SHALL run on Python 3.11 or newer |
| 11.6 | Rule logic SHALL be testable without PDF input |

**Rationale for 11.1.** The brief permits a model for one judgment — telling a fresh
mention from a citation reproducing older text. That judgment has an exact answer
because CHN citations open with a fixed phrase, so it is settled in code. The
trade-off and the single call site where a model would re-enter are recorded in
[plan.md](plan.md).
