# Specification and requirements traceability

Every requirement from the assessment brief, where it is implemented, and the test
that holds it in place. Requirements are restated in our own words — the brief
itself is the commissioning party's document and is deliberately not republished here.

Status key: **Done** — implemented and tested. **Partial** — implemented with a
stated limitation. **Not done** — deliberately out of scope, with a reason.

---

## Part 1 — Content rules

| ID | Requirement | Implementation | Test | Status |
|---|---|---|---|---|
| CHN-1 | A bare "CHN" is only allowed after the full form `Contoso Health Network® (CHN®)` has appeared earlier in the document | `rules.py` → `NamingSequenceRule` | `test_rules.py::test_bare_chn_before_first_mention_is_flagged` | Done |
| CHN-2 | The standards name steps down by occurrence: 1st full form, 2nd `CHN Clinical Standards™`, 3rd onward `CHN Clinical Standards` | `rules.py` → `_standards_problem` | `test_rules.py::test_correct_standards_sequence_produces_no_findings` | Done |
| CHN-2a | A bare "CHN" inside a standards phrase belongs to that family and must not also trigger CHN-1 (family precedence) | `rules.py` → `_MENTION` matches longest form first, consuming it | `test_rules.py::test_bare_chn_inside_a_standards_phrase_does_not_also_fire_chn1` | Done |
| CHN-3 | The two first-mention forms may not be introduced in the same sentence | `rules.py` → `NamingSequenceRule._check_combination` | `test_rules.py::test_chn3_flags_both_first_mentions_in_one_sentence` | Done |
| CAT-DEF | A stated Tier A/B/C rating must reproduce its definition verbatim; paraphrase or omission is a violation | `rules.py` → `CategoryDefinitionRule`, `TIER_DEFINITIONS` | `test_rules.py::test_paraphrased_definition_is_flagged` | Done |
| CITATION | A citation block must contain all five elements — topic, version, copyright year, access date, contosohealth.org — in any order | `rules.py` → `CitationFormatRule`, `CITATION_ELEMENTS` | `test_rules.py::test_missing_access_date_is_flagged` | Done |
| DISCLAIMER | The mandatory disclaimer must appear at least once, anywhere in the document | `rules.py` → `DisclaimerRule` | `test_rules.py::test_missing_disclaimer_is_a_document_level_finding` | Done |
| LOGO | A reproduced logo without a nearby licence/agreement reference is flagged; with one, it is provisionally compliant | `rules.py` → `LogoLicenseRule` | `test_rules.py::test_license_reference_near_the_logo_is_compliant` | Done |
| QR | QR codes and links inside or beside CHN-referencing content are surfaced for manual review; the destination is not judged | `links.py` → `detect_qr_and_urls` | `test_links.py` (4 tests) | Done |

---

## Part 2 — Tasks

### Task 1 — Region extraction

| Requirement | Implementation | Test | Status |
|---|---|---|---|
| Extract regions from native highlight/underline annotations | `extract.py` → `extract_annotations`, `TEXT_MARKUP_SUBTYPES` | `test_extract.py::test_extracts_highlight_and_square_but_not_reviewer_note` | Done |
| Extract regions from hand-drawn rectangles | `extract.py` → `extract_annotations` (shape annotations) and `extract_handdrawn_boxes` (vector paths) | `test_extract.py::test_handdrawn_captures_rectangles_and_skips_curves` | Done |
| Capture page, bbox, verbatim text, and which method detected it | `models.py` → `Region(page, bbox, text, source, subtype)`; text is never cleaned up | `test_samples.py::test_sample_04_extracts_the_drawn_box_and_ignores_the_reviewer_note` | Done |
| Avoid reporting the same underlying text twice | `extract.py` → `merge_regions`, IoU ≥ 0.6 | `test_extract.py::test_overlapping_regions_merge_with_native_annotation_winning` | Done |
| Decide which wins when a box and a highlight overlap | Native annotation is canonical; the box is folded into `merged_from`. Rationale in README | same as above | Done |
| Distinguish a reviewer's own note from flagged content | `FreeText`/`Text` annotations excluded from regions **and** from the text stream; their borders excluded too | `test_extract.py::test_reviewer_note_text_is_excluded_from_the_text_stream` | Done |

Discussion of the three ambiguities the brief raises is in README → "Judgment calls".

### Task 2 — Naming sequence validation

| Requirement | Implementation | Test | Status |
|---|---|---|---|
| Track first-mention state across the whole document, not per region | `rules.py` → counters walked over `doc.text_spans` in reading order | `test_samples.py::test_sample_03_flags_the_missing_trademark_symbol_across_pages` | Done |
| Track the two families independently | Separate `chn_first_seen` and `standards_count` | `test_rules.py::test_correct_standards_sequence_produces_no_findings` | Done |
| Keep cross-document state deterministic in code, not re-derived by a model | No model is used at all; state is two local variables | every naming test | Done |
| Distinguish a fresh mention from a citation reproducing older text | `rules.py` → `is_citation_block`, a regex on the fixed citation lead-in. See README → "Why there is no LLM" | `test_rules.py::test_citation_reproductions_do_not_shift_the_occurrence_count` | Done |

### Task 3 — QR and URL detection

| Requirement | Implementation | Test | Status |
|---|---|---|---|
| Detect and decode QR codes in or near flagged regions | `links.py` → `_qr_codes` (renders the padded region, decodes with pyzbar) | `test_samples.py::test_sample_01_flags_only_the_genuinely_incomplete_citation` | Done |
| Detect plain-text URLs and embedded link annotations in the same regions | `links.py` → `_plain_text_urls`, `_link_annotations` | `test_links.py` (4 tests) | Done |
| Output the target alongside the region it was found in | `Finding.snippet` carries the target; `Finding.region_id` the region | `test_links.py::test_detects_plain_text_url_inside_a_flagged_region` | Done |
| Do not evaluate the destination | Every hit is `needs_review`, never a violation | `test_links.py::test_detects_plain_text_url_inside_a_flagged_region` | Done |

### Task 4 — Category, citation and disclaimer

Covered by CAT-DEF, CITATION and DISCLAIMER above. The disclaimer check is
document-level as the brief requires; the other two are anchored to a page.

### Task 5 — Logo detection (stretch)

| Requirement | Implementation | Test | Status |
|---|---|---|---|
| Detect the reference logo within flagged image regions | `logo.py` → `find_logo_matches` | `test_logo.py::test_finds_a_reproduced_logo_inside_a_flagged_region` | Done |
| Use perceptual hashing, not exact pixel matching | `imagehash.phash`, Hamming distance ≤ 8 | same as above | Done |
| Flag a logo with no nearby licence reference | `rules.py` → `LogoLicenseRule`, 20pt margin | `test_samples.py::test_sample_05_logo_without_a_license_goes_to_a_reviewer` | Done |
| Report a licensed logo as provisionally compliant, not flagged | Reported `confirmed` and excluded from the violation count | `test_samples.py::test_sample_06_logo_with_a_license_is_provisionally_compliant` | Done |
| Tolerate resizing and recompression | Supported by phash, but **untested against real variants** — both samples embed the byte-identical source image | — | Partial |

### Task 6 — Structured compliance report

| Requirement | Implementation | Test | Status |
|---|---|---|---|
| One report per document, summarizing Tasks 1–5 | `report.py` → `build_report`; includes the Task 1 regions, not just findings | `test_report.py::test_extracted_regions_are_carried_into_the_report` | Done |
| Overall PASS / FAIL / NEEDS_REVIEW status | `report.py` → `build_report` | `test_report.py` (3 status tests) | Done |
| Count of rules checked | `rules_checked` | `test_report.py::test_pass_when_there_are_no_findings` | Done |
| Count of rules violated | `rules_violated`, counting distinct rules | `test_report.py::test_fail_when_a_violation_is_confirmed` | Done |
| Count of regions that could not be evaluated with confidence | `regions_unevaluated` — flagged regions yielding no text; also forces NEEDS_REVIEW | `test_report.py::test_region_without_text_counts_as_not_evaluable` | Done |
| Per-rule findings with page and snippet, so the source PDF need not be reopened | `Finding(page, snippet, explanation)`, rendered in both formats | `test_report.py::test_markdown_includes_status_counts_and_sections` | Done |
| Clear separation of confident violations from items for human judgment | Three headed sections: Violations / Needs Human Review / Checked and Compliant | `test_report.py::test_markdown_separates_a_compliant_logo_from_violations` | Done |
| Justify the output format | JSON as source of truth, Markdown rendered from it. Reasoning in docs/DESIGN.md | — | Done |

---

## Deliberately not done

| Item | Reason |
|---|---|
| Judging whether a link's destination is compliant | Out of scope per the brief — links go to a human |
| The full CHN rulebook | Only the subset in the brief was in scope |
| OCR for scanned pages | A page with no text layer yields no spans. Flagged regions with no text are counted as unevaluable rather than passed silently, so the gap is visible in the report rather than hidden |
| Multiple logo lockups | One reference image was available, extracted from the sample packet itself |
| Auth, persistence, queueing, deployment | The brief asks for a local prototype |

## Known limitations

1. `CAT-DEF` searches the page the rating appears on; a definition on a later page reads as missing.
2. Reading order is `(page, y, x)` over text blocks. A multi-column layout whose blocks interleave vertically could be traversed out of order, which matters because every sequencing rule depends on reading order.
3. The citation check confirms the five elements are present, not that the wording around them matches the template.
4. A decorative bordered callout and a genuine reviewer box are not reliably distinguishable; see README → "Judgment calls" for why this is safe and what it costs.
