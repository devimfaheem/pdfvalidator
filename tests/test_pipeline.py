from conftest import build_pdf

from pdfvalidator.cli import main
from pdfvalidator.pipeline import run_pipeline

DISCLAIMER_LINE = (
    "CHN makes no warranties of any kind regarding this content, its use, or application, "
    "and disclaims any responsibility for its application or use in any way."
)

COMPLIANT_DOCUMENT = [
    "Contoso Health Network® (CHN®) publishes guidance.",
    "CHN is well known.",
    DISCLAIMER_LINE,
]


def test_compliant_document_passes(tmp_path):
    report = run_pipeline(build_pdf(tmp_path, COMPLIANT_DOCUMENT))
    assert report.status == "PASS"
    assert report.rules_checked >= 6


def test_bare_chn_without_a_first_mention_fails(tmp_path):
    report = run_pipeline(build_pdf(tmp_path, ["CHN is well known.", DISCLAIMER_LINE]))
    assert report.status == "FAIL"
    assert any(f.rule_id == "CHN-1" for f in report.findings)


def test_cli_writes_both_reports(tmp_path):
    pdf_path = build_pdf(tmp_path, COMPLIANT_DOCUMENT)
    output_dir = tmp_path / "output"

    assert main(["validate", pdf_path, "--output-dir", str(output_dir)]) == 0
    assert (output_dir / "doc" / "report.json").exists()
    assert (output_dir / "doc" / "report.md").exists()


def test_cli_rejects_a_file_that_is_not_a_pdf(tmp_path, capsys):
    bad_path = tmp_path / "not_a_pdf.pdf"
    bad_path.write_text("this is not a pdf")

    assert main(["validate", str(bad_path)]) == 1
    assert "could not open" in capsys.readouterr().err
