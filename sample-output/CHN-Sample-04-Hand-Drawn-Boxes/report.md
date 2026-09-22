# Compliance Report: CHN-Sample-04-Hand-Drawn-Boxes.pdf

**Status: FAIL**

- Rules checked: 6
- Rules violated: 1
- Findings needing human review: 1
- Flagged regions extracted: 2
- Regions that could not be evaluated with confidence: 0

## Violations

_The agent is confident these break a rule._

### [CAT-DEF] page 3
> for Central Nervous System Cancers
TumorScan+ is recommended as a Tier A systemic option for patients with a high-risk profile not amenable to complete
resection²

Tier A rating stated but the required exact definition text is missing or paraphrased nearby.

## Needs Human Review

_Surfaced for a person to judge — not called a violation._

### [QR-LINK] page 3
> https://contosohealth.org
Hyperlink annotation found near flagged region: https://contosohealth.org

## Flagged Regions

_What the submitter marked for review, and how it was detected._

| Region | Page | Detected by | Text |
|---|---|---|---|
| `region-0` | 3 | hand-drawn box (Square) | Contoso Health Network Clinical Practice Standards (CHN Clinical Standards™) for… |
| `region-1` | 3 | native annotation (Highlight) | 1. TumorScan+ Prescribing Information. Meridian Diagnostics. 2. Referenced with … |
