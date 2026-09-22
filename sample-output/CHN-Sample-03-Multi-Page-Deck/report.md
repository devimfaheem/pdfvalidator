# Compliance Report: CHN-Sample-03-Multi-Page-Deck.pdf

**Status: FAIL**

- Rules checked: 6
- Rules violated: 2
- Findings needing human review: 1
- Flagged regions extracted: 4
- Regions that could not be evaluated with confidence: 0

## Violations

_The agent is confident these break a rule._

### [CHN-2] page 3
> CHN Clinical Standards
Bare 'CHN Clinical Standards' used at occurrence #2; the 2nd occurrence must use the required trademark form

### [CHN-1] page 4
> CHN
Bare 'CHN' used before the required first-mention form 'Contoso Health Network® (CHN®)' appeared anywhere earlier in the document

## Needs Human Review

_Surfaced for a person to judge — not called a violation._

### [QR-LINK] page 4
> https://contosohealth.org/clinical-standards
Hyperlink annotation found near flagged region: https://contosohealth.org/clinical-standards

## Flagged Regions

_What the submitter marked for review, and how it was detected._

| Region | Page | Detected by | Text |
|---|---|---|---|
| `region-0` | 2 | native annotation (Highlight) | • Contoso Health Network Clinical Practice Standards (CHN Clinical Standards™) |
| `region-1` | 3 | hand-drawn box (Square) | CHN Clinical Standards — General Testing Criteria • Regardless of cancer type in… |
| `region-2` | 3 | native annotation (Highlight) | CHN Clinical Standards — General Testing Criteria |
| `region-3` | 4 | native annotation (Highlight) | 1. Referenced with permission from the Contoso Health Network Clinical Practice … |
