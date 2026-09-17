"""Aggregate findings into a report a non-technical reviewer can act on."""

import json
from pathlib import Path

from .models import ComplianceReport, Finding

# A logo match with a license reference is confirmed *compliant*, not a violation.
# It is the one rule whose confirmed findings are good news.
_COMPLIANCE_ONLY_RULES = {"LOGO-LICENSE"}


def build_report(document_name: str, rule_ids_checked: list[str], findings: list[Finding]) -> ComplianceReport:
    violations = [
        f for f in findings
        if f.confidence == "confirmed" and f.rule_id not in _COMPLIANCE_ONLY_RULES
    ]
    needs_review = [f for f in findings if f.confidence == "needs_review"]

    if violations:
        status = "FAIL"
    elif needs_review:
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

    return "\n".join(lines)


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
