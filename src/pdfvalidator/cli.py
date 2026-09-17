"""`python -m pdfvalidator validate <pdf>`"""

import argparse
import sys

import pymupdf

from .pipeline import run_pipeline
from .report import write_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pdfvalidator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="Validate a submitted PDF against CHN rules")
    validate.add_argument("pdf_path", help="Path to the PDF to validate")
    validate.add_argument("--output-dir", default="output", help="Where to write report.json and report.md")

    args = parser.parse_args(argv)

    try:
        pymupdf.open(args.pdf_path).close()
    except Exception as exc:
        print(f"Error: could not open '{args.pdf_path}' as a PDF: {exc}", file=sys.stderr)
        return 1

    report = run_pipeline(args.pdf_path)
    json_path, markdown_path = write_report(report, args.output_dir)

    print(f"Status: {report.status}")
    print(f"Report written to {json_path} and {markdown_path}")
    return 1 if report.status == "FAIL" else 0
