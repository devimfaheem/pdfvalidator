# CHN PDF Compliance Validator Constitution

Principles that govern this codebase. They are not aspirations — each one is
already enforced by the code and the test suite, and a change that breaks one needs
an explicit amendment here first.

## Core Principles

### I. Deterministic by default (NON-NEGOTIABLE)

No language-model call, no network call, and no environment variable at validation
time. Two runs over the same document produce byte-identical reports.

A compliance verdict must be reproducible and defensible to the person it is shown
to. A model's judgment cannot be re-derived six months later when someone asks why a
document failed. Where the brief permitted a model — telling a fresh mention from a
citation reproducing older text — that judgment turned out to have an exact answer,
so it is settled in code at one named call site.

If a future requirement genuinely needs a model, it enters behind an interface at a
single call site, its output is marked `needs_review` rather than `confirmed`, and
this principle is amended to say so.

### II. Rules are pure functions of plain data

A rule receives text spans and region records. It never opens a PDF, reads a file, or
touches the network. Every rule is testable by constructing its input directly.

This is what keeps the suite under a second and what makes a rule's behaviour legible
without a fixture file. The single exception is logo matching, which compares images
and therefore needs the document handle; it is isolated to one rule rather than
widened into a general capability.

### III. Confidence is explicit, never implied

Every finding is `confirmed` or `needs_review`. There is no third state and no
silent default.

`confirmed` means an exact-match, ordinal or regex check the system can defend.
`needs_review` means something only a person can settle — where a link points, or a
logo with no licence reference nearby. A rule that cannot tell the difference raises
`needs_review`; it never guesses in order to look decisive.

### IV. Unreadable is not the same as non-compliant

A document that fails its rules produces a report. A document that cannot be read
produces none, and says why in a sentence a reviewer can act on.

A flagged region that yields no text is counted as unevaluable and forces
`NEEDS_REVIEW` rather than passing quietly. Gaps in what the system can read must
appear in the report, never be absorbed by it. No interface exposes a stack trace or
an internal path.

### V. Verify against the artifact, not against the output

Expectations in tests are derived by reading the source PDF. They are never recorded
from whatever the tool happened to emit.

Recording output as the expectation makes a test that can only ever pass. This
discipline is what surfaced a genuine missing access date in Sample 01, and a build
reporting 23 flagged regions where a reviewer had marked 2. A test whose expectation
came from a run is not evidence.

## Additional Constraints

- **Python 3.11+**, four runtime dependencies, all on the input side: PyMuPDF,
  pyzbar, imagehash, Pillow. No package evaluates compliance; rule logic is standard
  library.
- **Extracted text is verbatim.** Never cleaned, normalised in place, or paraphrased.
  Normalisation happens at comparison time, not in stored data.
- **The rulebook grows by addition.** A new rule is a class with an `id` and a
  `check()`, registered in one list. Adding one changes nothing else.
- **Ambiguity is documented, not silently resolved.** Where two readings of a rule
  are defensible, the chosen one and its cost are written down. Over-inclusion is
  preferred when the cost is a mislabelled field rather than a wrong verdict.

## Development Workflow

- Specifications live in `specs/`; the constitution governs them. A behaviour change
  starts with the spec, not the code.
- Every requirement carries testable acceptance criteria in EARS form.
- Every task names the requirements it satisfies and the tests that hold it.
- `pytest` and `ruff check` pass before any commit.
- Sample output in `sample-output/` is regenerated and diffed to prove Principle I.

## Governance

This constitution supersedes convenience. A pull request that violates a principle is
either rewritten or accompanied by an amendment here explaining what changed and why.

Amendments record the date and the reasoning, not just the new text. A principle
removed without a recorded reason is a principle that was never real.

**Version**: 1.0.0 | **Ratified**: 2026-10-06 | **Last amended**: 2026-10-06
