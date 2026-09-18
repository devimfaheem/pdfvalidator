# Architecture

How the system is put together, why the boundaries sit where they do, and what the
PDF format forced along the way.

Companion documents: [README](../README.md) for running it and the judgment calls,
[SPEC.md](SPEC.md) for requirement-by-requirement traceability.

---

## 1. Shape of the system

One pass over a PDF produces two things — the regions a submitter marked, and the
document's text in reading order. Everything downstream consumes those.

```
                      ┌──────────────────────────────────────────┐
   submitted.pdf ───► │ extract.py                               │
                      │   annotations  → regions                 │
                      │   vector paths → regions (fallback)      │
                      │   merge overlaps, drop reviewer notes    │
                      │   text blocks  → ordered text spans      │
                      └────────────┬─────────────────┬───────────┘
                                   │ regions         │ text spans
                                   │                 │
         ┌─────────────────────────┼─────────────────┼──────────────────┐
         │                         ▼                 ▼                  │
         │  rules.py — DocumentContext(regions, text_spans, pdf, hash)  │
         │    NamingSequenceRule      CHN-1 / CHN-2 / CHN-3             │
         │    CategoryDefinitionRule  CAT-DEF                           │
         │    CitationFormatRule      CITATION                          │
         │    DisclaimerRule          DISCLAIMER                        │
         │    LogoLicenseRule         LOGO-LICENSE ──► logo.py (phash)  │
         └─────────────────────────┬────────────────────────────────────┘
                                   │ findings
              links.py ────────────┤ findings (QR codes, URLs, link annots)
                                   ▼
                      ┌──────────────────────────────────────────┐
                      │ report.py                                │
                      │   aggregate → status, counts             │
                      │   serialise → report.json                │
                      │   render    → report.md                  │
                      └──────────────────────────────────────────┘

  pipeline.py wires the above.  cli.py and web/app.py are two front doors onto it.
```

The important property: **rules never touch a PDF.** They receive plain text spans
and region records, which is why every rule is unit-testable without a fixture file
and why the suite runs in about a second.

`LogoLicenseRule` is the one exception — image matching needs the document itself —
so `DocumentContext` carries the open handle for it alone.

---

## 2. Modules

| File | Lines | Responsibility |
|---|---|---|
| `models.py` | 49 | `Region`, `TextSpan`, `Finding`, `ComplianceReport`. Data only, no behaviour |
| `extract.py` | 220 | Everything that reads PDF structure: annotations, vector paths, overlap merging, the ordered text stream |
| `rules.py` | 333 | The required wording, the five rule classes, and the `Rule` interface |
| `links.py` | 86 | QR decoding, plain URLs, link annotations |
| `logo.py` | 38 | Perceptual-hash matching of the reference logo |
| `report.py` | 159 | Status aggregation, JSON serialisation, Markdown rendering |
| `pipeline.py` | 46 | Wiring. Knows the order of operations and nothing else |
| `cli.py` | 33 | Argument parsing and exit codes |
| `web/app.py` | 115 | Streamlit view over the same `ComplianceReport` |

About 970 lines of source and 930 of tests, plus the UI.

**Why flat, not layered.** An earlier iteration spread the same code over eight
packages — a nine-line module in its own directory, eight empty `__init__.py` files.
Every rule still took the same inputs and produced the same outputs; the packaging
added navigation cost and no isolation. Eight modules that each fit on a screen are
easier to hold in your head than twenty that don't.

---

## 3. Data model

```python
Region(id, page, bbox, text, source, subtype, color, merged_from)
TextSpan(page, bbox, text, order_key)
Finding(rule_id, confidence, page, bbox, snippet, explanation, region_id)
ComplianceReport(document, status, rules_checked, rules_violated,
                 needs_review_count, findings, regions, regions_unevaluated)
```

Three things are load-bearing:

- **`Region.text` is verbatim.** Never cleaned, never paraphrased. A reviewer
  comparing the report against the source must see the same characters.
- **`TextSpan.order_key` is `(page, y, x)`** and defines document reading order.
  Every sequencing rule depends on it, which makes it the single point of failure
  for CHN-1/2/3 — see Limitations.
- **`Region.merged_from`** records which regions were absorbed during overlap
  resolution, so a merge is auditable rather than silent.

---

## 4. The rule interface

```python
class Rule(Protocol):
    id: str
    def check(self, doc: DocumentContext) -> list[Finding]: ...
```

Rules are registered in one list:

```python
ALL_RULES: list[Rule] = [
    NamingSequenceRule(), CategoryDefinitionRule(),
    CitationFormatRule(), DisclaimerRule(), LogoLicenseRule(),
]
```

**Adding a rule** is: write a class with those two members, append it to `ALL_RULES`,
write a test against a `context("some text")` fixture. Nothing else changes —
`pipeline.py` iterates the list, `report.py` aggregates whatever comes back, and both
front ends render it. The rule ID flows automatically into `rules_checked`.

This is the main reason for the registry over a single `validate_document()`
function: the rulebook is the part most likely to grow, and it grows by addition
rather than by editing a function everything else depends on.

---

## 5. Confidence, and why there are three buckets

Every finding is `confirmed` or `needs_review`. There is no implicit third state.

- **`confirmed`** — an exact-match, ordinal or regex check the agent can defend.
- **`needs_review`** — something only a person can settle: where a link goes, or a
  logo with no licence reference nearby.

`LOGO-LICENSE` is the one rule whose `confirmed` findings are *good* news — a logo
with a licence reference is compliance, not a violation. So `report.py` excludes it
from the violation count and renders it under its own heading. Three sections result:

| Section | Meaning |
|---|---|
| Violations | Confident this breaks a rule |
| Needs human review | Surfaced for a person; not called a violation |
| Checked and compliant | Verified as meeting the rule |

A reviewer skimming for problems should never meet good news under a heading that
reads like a violation.

**Status aggregation:** any violation → `FAIL`; else any needs-review *or* any
unreadable region → `NEEDS_REVIEW`; else `PASS`. A flagged region yielding no text
counts as unreadable — the submitter marked something the agent could not judge, and
that is not a pass.

---

## 6. What the PDF format forced

The design was calibrated against the six provided samples, inspected with PyMuPDF.
Several reasonable assumptions turned out to be wrong, and each one shaped a module.

1. **"Hand-drawn boxes" arrive as `Square` annotations**, not loose vector paths. The
   rectangle tool in Preview and Acrobat produces an annotation — the annotation
   layer, just a different subtype than `Highlight`. A vector-path fallback still
   exists for PDFs that draw boxes as plain shapes; the packet never exercises it.

2. **Decorative graphics look rectangular.** A background blob's bezier path reports a
   rectangular bounding box, so `_is_rectangular_path` inspects the path's own
   segments rather than its bounds.

3. **Page furniture looks like a flagged box.** Sample-04's navigation tab bar is five
   filled rectangles per page — 21 in all, each containing real text. A reviewer draws
   an *outline*; a solid block of brand colour is furniture. Hence the stroke
   requirement, plus a minimum size, since Sample-06's header rule is a stroked
   rectangle 532pt wide and 0pt tall.

4. **Annotations are painted into page content as well.** Highlights and boxes appear
   in `get_drawings()` output alongside genuine drawings, so the fallback discards any
   drawing closely matching an annotation already captured.

5. **A reviewer's note is drawn into the page too.** Excluding `FreeText` annotations
   from *regions* is not enough — their text reaches the text stream and gets scanned
   as if the submitter wrote it. Sample-04's "Note to CHN: CHN content is located on
   slide 3" produced two false CHN-1 violations until the text stream dropped text
   sitting inside a note.

6. **Headings are set in all caps.** `CONTOSO HEALTH NETWORK® (CHN®)` is styling, not
   different wording — hence case-insensitive sequence matching, while category
   definitions stay case-sensitive.

7. **PyMuPDF inserts newlines at physical line breaks**, mid-phrase included. A
   required sentence that wraps is still a verbatim reproduction, so whitespace is
   collapsed before every match.

---

## 7. Output formats

`report.json` is the source of truth; `report.md` is rendered from it, and the
Streamlit UI is a third view over the same `ComplianceReport` object. None of the
three re-derives anything.

JSON because it is what tests assert against and what another system would consume.
Markdown because a reviewer wants prose and a table, not a payload, and because it
renders anywhere without a templating dependency. Writing both means the format a
human reads and the format a machine checks cannot drift apart.

---

## 8. Where an LLM would go

At exactly one call site — `is_citation_block()` in `rules.py`. The brief permits an
LLM for one semantic judgment: telling a fresh mention from a citation reproducing
older text. That judgment has an exact answer here, because a CHN citation announces
itself with a fixed lead-in, so a regex settles it deterministically and for free.

If the citation wording ever varied enough to defeat the regex, a model would slot in
behind the same one-line signature without touching any rule. See README →
"Why there is no LLM" for the trade-off.

---

## 9. Known structural limitations

1. **Reading order is `(page, y, x)`** over text blocks. A multi-column layout whose
   blocks interleave vertically could be traversed out of order, and every sequencing
   rule depends on that order.
2. **`CAT-DEF` searches the page** a rating appears on; a definition on a later page
   reads as missing.
3. **No OCR.** A page with no text layer yields no spans. Flagged regions with no text
   are counted as unevaluable rather than passed silently, so the gap shows up in the
   report instead of hiding.
4. **Decorative bordered callouts and genuine reviewer boxes** are not reliably
   distinguishable; both are extracted. Safe because rules read text, not provenance.
