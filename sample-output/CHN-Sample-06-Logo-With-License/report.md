# Compliance Report: CHN-Sample-06-Logo-With-License.pdf

**Status: FAIL**

- Rules checked: 6
- Rules violated: 2
- Findings needing human review: 0
- Flagged regions extracted: 2
- Regions that could not be evaluated with confidence: 0

## Violations

_The agent is confident these break a rule._

### [CHN-1] page 1
> CHN
Bare 'CHN' used before the required first-mention form 'Contoso Health Network® (CHN®)' appeared anywhere earlier in the document

### [DISCLAIMER] page 1
Mandatory CHN disclaimer statement was not found anywhere in the document.

## Checked and Compliant

_Verified as meeting the rule._

### [LOGO-LICENSE] page 1
> Contoso Health
Network
CHN Logo
Logo detected (hash distance 0); license reference found nearby — provisionally compliant.

## Flagged Regions

_What the submitter marked for review, and how it was detected._

| Region | Page | Detected by | Text |
|---|---|---|---|
| `region-0` | 1 | native annotation (Highlight) | Contoso Health Network CHN Logo |
| `region-1` | 1 | native annotation (Highlight) | Logo used with permission per agreement CHN-2026-014. |
