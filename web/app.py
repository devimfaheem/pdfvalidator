"""Upload a PDF, see the compliance report.

A view over the same `run_pipeline` the CLI calls — no validation logic lives here.
"""

import tempfile
from pathlib import Path

import streamlit as st

from pdfvalidator.models import ComplianceReport, Finding
from pdfvalidator.pipeline import run_pipeline
from pdfvalidator.report import to_dict

COMPLIANCE_ONLY_RULES = {"LOGO-LICENSE"}

STATUS_STYLE = {
    "PASS": (st.success, "PASS — no violations found"),
    "FAIL": (st.error, "FAIL — confirmed violations found"),
    "NEEDS_REVIEW": (st.warning, "NEEDS REVIEW — nothing confirmed, but a person should look"),
}


def main() -> None:
    st.set_page_config(page_title="CHN PDF Compliance Validator", page_icon="📄", layout="wide")
    st.title("CHN PDF Compliance Validator")
    st.caption("Pre-screens submitted material against the Contoso Health Network content rules.")

    uploaded = st.file_uploader("Choose a PDF", type="pdf")
    if uploaded is None:
        st.info("Upload a PDF to validate. Sample files are in `CHN Generated Samples/`.")
        return

    with st.spinner(f"Validating {uploaded.name}…"):
        report = _validate(uploaded.getvalue(), uploaded.name)

    _render(report)


def _validate(pdf_bytes: bytes, filename: str) -> ComplianceReport:
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / filename
        path.write_bytes(pdf_bytes)
        return run_pipeline(str(path))


def _render(report: ComplianceReport) -> None:
    show, message = STATUS_STYLE[report.status]
    show(message)

    checked, violated, review = st.columns(3)
    checked.metric("Rules checked", report.rules_checked)
    violated.metric("Rules violated", report.rules_violated)
    review.metric("Needs human review", report.needs_review_count)

    violations = [
        f for f in report.findings
        if f.confidence == "confirmed" and f.rule_id not in COMPLIANCE_ONLY_RULES
    ]
    needs_review = [f for f in report.findings if f.confidence == "needs_review"]
    compliant = [
        f for f in report.findings
        if f.confidence == "confirmed" and f.rule_id in COMPLIANCE_ONLY_RULES
    ]

    # Same order and separation as the Markdown report: what is wrong, what needs a
    # decision, what passed.
    _section("Violations", "The agent is confident these break a rule.", violations, st.error)
    _section("Needs human review", "Surfaced for a person to judge.", needs_review, st.warning)
    _section("Checked and compliant", "Verified as meeting the rule.", compliant, st.success)

    if not report.findings:
        st.success("No findings — document passed all checks.")

    with st.expander("Raw report (JSON)"):
        st.json(to_dict(report))


def _section(title: str, subtitle: str, findings: list[Finding], callout) -> None:
    if not findings:
        return

    st.subheader(f"{title} ({len(findings)})")
    st.caption(subtitle)
    for finding in findings:
        with st.expander(f"[{finding.rule_id}] page {finding.page}", expanded=len(findings) <= 3):
            callout(finding.explanation)
            if finding.snippet:
                st.code(finding.snippet, language=None)
            if finding.region_id:
                st.caption(f"Flagged region: {finding.region_id}")


main()
