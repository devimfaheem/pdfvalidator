# Design notes

Background for the choices in the README, and what the sample packet revealed that the
brief's prose did not. Start with the [README](../README.md) — this is the longer version.

## What the samples showed

The design was calibrated against the six provided PDFs, inspected with PyMuPDF. Several
reasonable-sounding assumptions turned out to be wrong:

1. **"Hand-drawn boxes" arrive as `Square` annotations**, not as loose vector paths. The
   rectangle tool in Preview and Acrobat produces an annotation — technically the annotation
   layer, just a different subtype than `Highlight`. Confirmed in Sample-04 page 3, where a
   red `Square` encloses exactly the paragraph a `FreeText` note on page 1 points at.
   A vector-path fallback still exists for PDFs that draw boxes as plain shapes; the packet
   does not exercise it.

2. **Decorative graphics look rectangular.** A background blob's bezier path reports a
   rectangular bounding box. The fallback inspects the path's own segments and skips anything
   containing a curve — otherwise Sample-04's decorative circles become regions.

3. **Annotations are painted into the page content as well.** Highlights and boxes appear in
   `get_drawings()` output alongside genuine drawings, so the fallback discards any drawing
   that closely matches an annotation already captured. The same duplication is why reviewer
   notes must be excluded from the text stream, not just from regions.

4. **Headings are set in all caps.** Sample-01's title reads `CONTOSO HEALTH NETWORK® (CHN®)`
   — styling, not different wording, hence case-insensitive sequence matching.

5. **PyMuPDF inserts newlines at physical line breaks.** A required sentence that wraps
   mid-phrase is still a verbatim reproduction, so whitespace is collapsed before every
   match. Without this, Sample-01's first-mention form fails to match and the document
   reports violations it does not have.

6. **The packet contains genuine violations.** Sample-01's first citation omits its access
   date; Sample-03 drops the ™ at the second occurrence; Sample-02 uses the short form above
   the citation that introduces it. These are real, and asserted as such in `test_samples.py`.

## Data model

```python
Region(id, page, bbox, text, source, subtype, color, merged_from)
TextSpan(page, bbox, text, order_key)
Finding(rule_id, confidence, page, bbox, snippet, explanation, region_id)
ComplianceReport(document, status, rules_checked, rules_violated, needs_review_count, findings)
```

`Region.text` is verbatim — never cleaned up or paraphrased. `order_key` is `(page, y, x)`
and defines reading order, which every sequencing rule depends on.

## Confidence

Every finding is `confirmed` or `needs_review`; there is no implicit third state.

- `confirmed` — an exact-match or ordinal check the agent can defend on its own.
- `needs_review` — something only a person can settle: a QR/link destination, or a logo with
  no license reference nearby.

`LOGO-LICENSE` is the one rule whose `confirmed` findings are good news, so `report.py`
excludes it from the violation count and renders it under its own heading.

Status aggregation: any violation → `FAIL`; otherwise any `needs_review` → `NEEDS_REVIEW`;
otherwise `PASS`.

## Why JSON and Markdown

JSON is the source of truth — stable field names, diffable, what tests assert against.
Markdown is rendered from it for the reviewer. Writing both means the format a human reads
and the format a machine checks can never disagree, and neither needs a rendering
dependency. The Streamlit UI is a third view over the same `ComplianceReport` object, not a
second implementation.

## Where an LLM would go

At one call site, `is_citation_block()` in `rules.py`. See "Why there is no LLM" in the
README for the reasoning and the trade-off.
