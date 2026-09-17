# CHN PDF Compliance Validator

Pre-screens submitted PDFs against the Contoso Health Network content rules and
produces a report a non-technical reviewer can act on without opening the source file.

Given a PDF, it extracts every region a submitter flagged for review, checks the
document against the CHN rulebook, surfaces QR codes and links for manual review,
detects reproductions of the CHN logo, and writes a `PASS` / `FAIL` / `NEEDS_REVIEW`
report as both JSON and Markdown.

---

## Quick start

### Docker (nothing to install)

```bash
docker compose run --rm pdfvalidator python -m pdfvalidator validate "CHN Generated Samples/CHN-Sample-01-Multi-Color-Highlights.pdf"
```

Reports land in `output/<document-name>/`. For the web UI:

```bash
docker compose up
```

then open <http://localhost:8501> and upload a PDF.

### Local install

QR decoding needs the native `zbar` library, which pip cannot install:

```bash
brew install zbar          # macOS
sudo apt-get install libzbar0   # Debian/Ubuntu
```

Then:

```bash
pip install -e ".[web,dev]"
python -m pdfvalidator validate "CHN Generated Samples/CHN-Sample-01-Multi-Color-Highlights.pdf"
pytest
streamlit run web/app.py    # optional UI
```

The CLI exits `1` on `FAIL`, `0` otherwise, so it drops into a pipeline as a gate.

---

## What it checks

| Rule | What it enforces |
|---|---|
| `CHN-1` | A bare "CHN" only after `Contoso Health Network® (CHN®)` has appeared |
| `CHN-2` | The standards name steps down correctly: full form → `CHN Clinical Standards™` → `CHN Clinical Standards` |
| `CHN-3` | The two first-mention forms are never introduced in the same sentence |
| `CAT-DEF` | A stated Tier A/B/C rating reproduces its definition verbatim |
| `CITATION` | A citation block carries all five required elements |
| `DISCLAIMER` | The mandatory disclaimer appears at least once |
| `LOGO-LICENSE` | A reproduced logo has a license reference near it |
| `QR-LINK` | QR codes and links in or beside flagged regions are surfaced |

---

## How it works

```
PDF ─┬─ extract.py ── flagged regions  ─┬─ rules.py    ── findings ─┐
     │                text spans        ├─ links.py    ── findings ─┼─ report.py ─→ report.json
     └─ logo.py ───── reference hash ───┘                           ┘               report.md
```

Eight modules, ~900 lines:

| File | Responsibility |
|---|---|
| `models.py` | `Region`, `TextSpan`, `Finding`, `ComplianceReport` |
| `extract.py` | Annotations, hand-drawn boxes, overlap merging, ordered text |
| `rules.py` | The five rule classes and the required wording they enforce |
| `links.py` | QR codes, plain URLs, link annotations |
| `logo.py` | Perceptual-hash logo matching |
| `report.py` | Status aggregation, Markdown rendering, file output |
| `pipeline.py` | Wires the above together |
| `cli.py` | `python -m pdfvalidator validate <pdf>` |

Every rule implements the same two-line interface (`id`, `check(doc) -> list[Finding]`)
and is registered in one list, so adding a rule means adding a class — nothing else
changes. Each rule is unit-tested against plain text spans, no PDF involved.

---

## Why there is no LLM

The brief allows an LLM for semantic judgment calls, and names the specific one:
telling a genuine first mention apart from a citation reproducing older text. **This
implementation uses no LLM**, deliberately.

That judgment turned out to have an exact answer. Every citation in the CHN format
opens with `Referenced with permission from`, so identifying one is a regex, not an
inference. Once a block is identified as a citation, the naming rule skips it — which
is precisely the behaviour an LLM was being proposed for:

```python
def is_citation_block(text: str) -> bool:
    return bool(_CITATION_MARKER.search(normalize(text)))
```

This matters for Sample-01, where both citations respell the standards' full name. Counting
them as fresh mentions would push the later short form to occurrence #5 and invent a
CHN-2 violation in a compliant document.

The rest of the rulebook is exact-match text, ordinal counting, and geometry — all of
which a model would only make slower, non-deterministic, and harder to test. The
trade-off is real, though: the regex keys on one fixed phrase, so a citation worded
differently would be missed where a model might generalise. If that became a problem,
the fix is to widen the check at this single call site, which is where an LLM would slot
in behind the same one-line signature.

**Deterministic by design, everywhere else too.** Cross-document first-mention state is
two counters walked over the text in reading order — never re-derived per call. Two runs
over the same PDF always produce the same report.

---

## Judgment calls

These are the ambiguities worth disagreeing with. Each is a decision, not an oversight.

**Rules scan the whole document, not just flagged regions.** Sample-01 puts the required
first-mention form in its unflagged title while the short forms it licenses sit inside
flagged panels. A region-only scan would report violations for a compliant document. Flagged
regions still scope the two rules whose briefs are explicitly spatial — QR/link detection
and logo detection.

**Every `Square`/`Circle` annotation is treated as a hand-drawn region.** Sample-01's two
`Square` annotations are decorative brochure borders; Sample-04's is a genuine reviewer
box. They are structurally identical — bordered box, dense CHN text inside — so no
geometry or text-density heuristic separates them, and this makes no attempt to. It is safe
because rules read text, not provenance: the cost is a possibly-wrong `source` label in the
report, never a missed or invented violation.

**A native annotation beats a hand-drawn box on the same content.** When both cover the same
text, the native annotation becomes the canonical region and the box is folded into
`merged_from`. Native annotations carry the PDF tool's deliberate semantics; shape detection
is a heuristic with real false-positive risk.

**Reviewer notes are excluded from the text stream, not just from regions.** `FreeText`
annotations are painted into the page content as well as stored on the annotation, so
excluding them from regions alone still leaves the reviewer's words to be scanned as if the
submitter wrote them. Sample-04's "Note to CHN: CHN content is located on slide 3" produced
two false CHN-1 violations until the text stream dropped text sitting inside a note.

**Case-insensitive for naming sequences, case-sensitive for definitions.** Sample-01's title
is set in all caps, a styling choice rather than a wording one. Tier definitions are body
text the brief explicitly forbids paraphrasing, so those match exactly.

**`CHN-2026-014` is an identifier, not a mention.** A bare "CHN" followed by `-` and a digit
is skipped. "CHN-approved" still counts.

**A licensed logo is reported as compliance, not as a violation or a flag.** It appears under
its own "Checked and Compliant" heading, so a reviewer skimming for problems never meets good
news under a heading that reads like a violation.

**One category finding per rating per page.** A page naming "Tier A" five times with no
definition has one problem; repeating it five times makes the report harder to act on.

---

## Results on the sample packet

Verified by reading each PDF directly, not by recording whatever the tool emitted:

| Sample | Result |
|---|---|
| 01 Multi-colour highlights | `FAIL` — citation #1 genuinely omits "Accessed [date]"; QR code surfaced |
| 02 Tradeshow banner | `FAIL` — short form used above the citation that introduces it |
| 03 Multi-page deck | `FAIL` — 2nd occurrence drops the ™, caught across a page boundary |
| 04 Hand-drawn boxes | `FAIL` — Tier A stated with no definition; drawn box extracted, reviewer note ignored |
| 05 Logo, no license | `FAIL` — logo flagged for review; disclaimer missing |
| 06 Logo with license | `FAIL` — logo provisionally compliant; disclaimer still missing |

Every sample fails on `CHN-1` or `DISCLAIMER` except 01, because each reuses the mandated
disclaimer wording (`CHN makes no warranties…`) without ever introducing
`Contoso Health Network® (CHN®)`. That is a true reading of the rules and a realistic
failure mode for reused boilerplate — not a parsing artifact.

---

## Testing

```bash
pytest
```

62 tests. Rule logic is tested against constructed text spans with no PDF I/O; extraction,
links and logo matching against PDFs built on the fly; and `test_samples.py` runs the full
pipeline over the real packet with expectations derived from reading the files.

---

## Left out, and why

- **Whether a link's destination is compliant.** Out of scope per the brief — links are
  surfaced for a human.
- **The full CHN rulebook.** Only the §2 subset was in scope.
- **OCR.** A scanned page with no text layer yields no text spans. Real submissions include
  scans, so this would be first on the list next.
- **Multiple logo lockups.** One reference image, extracted from Sample-06 itself (no separate
  asset was supplied) and checked in at `assets/reference_logo/contoso_logo.png`. Because both
  samples embed that exact image, the perceptual-hash tolerance for resizing and
  recompression is untested against real variants, though the approach supports it.
- **Production concerns** — auth, persistence, queuing, deployment. The brief asks for a local
  prototype.

## Known limitations

- `CAT-DEF` searches the page a rating appears on. A definition placed on a later page is
  reported as missing.
- Reading order is `(page, y, x)` over PyMuPDF text blocks. Multi-column layouts where blocks
  interleave vertically could be traversed in the wrong order, which matters because every
  sequencing rule depends on it.
- The citation check confirms all five elements are present, not that the wording around them
  matches the template.
