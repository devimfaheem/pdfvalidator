"""Aggregate findings into a report a non-technical reviewer can act on."""

import json
from pathlib import Path

from .models import ComplianceReport, Finding, Region

# A logo match with a license reference is confirmed *compliant*, not a violation.
# It is the one rule whose confirmed findings are good news.
_COMPLIANCE_ONLY_RULES = {"LOGO-LICENSE"}


def build_report(
    document_name: str,
    rule_ids_checked: list[str],
    findings: list[Finding],
    regions: list[Region] | None = None,
) -> ComplianceReport:
    regions = regions or []
    violations = [
        f for f in findings
        if f.confidence == "confirmed" and f.rule_id not in _COMPLIANCE_ONLY_RULES
    ]
    needs_review = [f for f in findings if f.confidence == "needs_review"]
    unevaluated = [r for r in regions if not r.text.strip()]

    # An unreadable region is not a pass. The submitter flagged something the agent
    # could not judge, so the document goes to a human rather than through.
    if violations:
        status = "FAIL"
    elif needs_review or unevaluated:
        status = "NEEDS_REVIEW"
    else:
        status = "PASS"

    return ComplianceReport(
        document=document_name,
        status=status,
        rules_checked=len(set(rule_ids_checked)),
        rules_violated=len({f.rule_id for f in violations}),
        needs_review_count=len(needs_review),
        findings=findings,
        regions=regions,
        regions_unevaluated=len(unevaluated),
    )


def render_markdown(report: ComplianceReport) -> str:
    lines = [
        f"# Compliance Report: {report.document}",
        "",
        f"**Status: {report.status}**",
        "",
        f"- Rules checked: {report.rules_checked}",
        f"- Rules violated: {report.rules_violated}",
        f"- Findings needing human review: {report.needs_review_count}",
        f"- Flagged regions extracted: {len(report.regions)}",
        f"- Regions that could not be evaluated with confidence: {report.regions_unevaluated}",
        "",
    ]

    violations = [
        f for f in report.findings
        if f.confidence == "confirmed" and f.rule_id not in _COMPLIANCE_ONLY_RULES
    ]
    needs_review = [f for f in report.findings if f.confidence == "needs_review"]
    compliant = [
        f for f in report.findings
        if f.confidence == "confirmed" and f.rule_id in _COMPLIANCE_ONLY_RULES
    ]

    # Violations first, then what a human must decide, then what passed. A reviewer
    # should never have to work out which of these three a finding is.
    lines += _section("Violations", "The agent is confident these break a rule.", violations)
    lines += _section("Needs Human Review", "Surfaced for a person to judge — not called a violation.", needs_review)
    lines += _section("Checked and Compliant", "Verified as meeting the rule.", compliant)

    if not report.findings:
        lines.append("No findings — document passed all checks.")
        lines.append("")

    lines += _regions_section(report.regions)

    return "\n".join(lines)


def _regions_section(regions: list[Region]) -> list[str]:
    """What the submitter marked, and which detection method found it (Task 1)."""
    if not regions:
        return []

    lines = [
        "## Flagged Regions",
        "",
        "_What the submitter marked for review, and how it was detected._",
        "",
        "| Region | Page | Detected by | Text |",
        "|---|---|---|---|",
    ]
    for region in regions:
        text = " ".join(region.text.split())
        if not text:
            preview = "_(no text — could not be evaluated)_"
        else:
            preview = text[:80] + ("…" if len(text) > 80 else "")
        preview = preview.replace("|", "\\|")  # a pipe would break the table row
        method = "native annotation" if region.source == "native_annotation" else "hand-drawn box"
        lines.append(f"| `{region.id}` | {region.page} | {method} ({region.subtype}) | {preview} |")
    lines.append("")
    return lines


def write_report(report: ComplianceReport, output_dir: str) -> tuple[Path, Path]:
    destination = Path(output_dir) / Path(report.document).stem
    destination.mkdir(parents=True, exist_ok=True)

    json_path = destination / "report.json"
    markdown_path = destination / "report.md"
    json_path.write_text(json.dumps(to_dict(report), indent=2))
    markdown_path.write_text(render_markdown(report))
    return json_path, markdown_path


def to_dict(report: ComplianceReport) -> dict:
    return {
        "document": report.document,
        "status": report.status,
        "rules_checked": report.rules_checked,
        "rules_violated": report.rules_violated,
        "needs_review_count": report.needs_review_count,
        "regions_unevaluated": report.regions_unevaluated,
        "regions": [
            {
                "id": r.id, "page": r.page, "bbox": r.bbox, "text": r.text,
                "source": r.source, "subtype": r.subtype, "merged_from": r.merged_from,
            }
            for r in report.regions
        ],
        "findings": [
            {
                "rule_id": f.rule_id, "confidence": f.confidence, "page": f.page, "bbox": f.bbox,
                "snippet": f.snippet, "explanation": f.explanation, "region_id": f.region_id,
            }
            for f in report.findings
        ],
    }


def _section(title: str, subtitle: str, findings: list[Finding]) -> list[str]:
    if not findings:
        return []
    lines = [f"## {title}", "", f"_{subtitle}_", ""]
    for finding in findings:
        lines.append(f"### [{finding.rule_id}] page {finding.page}")
        if finding.snippet:
            lines.append(f"> {finding.snippet}")
        lines.append(finding.explanation)
        lines.append("")
    return lines
