"""Check the local paper draft against ICSE 2027 formatting guardrails."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


PASS = "pass"
WARN = "warn"
FAIL = "fail"

REQUIRED_DOCUMENTCLASS = r"\documentclass[10pt,conference]{IEEEtran}"
FORBIDDEN_CLASS_OPTIONS = ("compsoc", "compsocconf")
RISKY_SPACING_PATTERNS = (
    r"\\vspace\s*[{[]",
    r"\\hspace\s*[{[]",
    r"\\addtolength\s*{\\text",
    r"\\setlength\s*{\\text",
    r"\\setlength\s*{\\columnsep",
    r"\\enlargethispage",
    r"\\fontsize\s*{",
    r"\\renewcommand\s*{\\baselinestretch}",
)


def _record(checks: list[dict[str, Any]], name: str, status: str, detail: str) -> None:
    checks.append({"name": name, "status": status, "detail": detail})


def _read_text_guess(path: Path) -> str:
    data = path.read_bytes()
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16", errors="replace")
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig", errors="replace")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")


def _contains_documentclass(tex: str) -> bool:
    compact = re.sub(r"\s+", "", tex)
    return REQUIRED_DOCUMENTCLASS.replace(" ", "") in compact


def check_tex_source(tex_path: str | Path) -> list[dict[str, Any]]:
    """Return source-level ICSE format checks."""
    path = Path(tex_path)
    tex = path.read_text(encoding="utf-8")
    checks: list[dict[str, Any]] = []

    if _contains_documentclass(tex):
        _record(checks, "ieeetran_documentclass", PASS, REQUIRED_DOCUMENTCLASS)
    else:
        _record(
            checks,
            "ieeetran_documentclass",
            FAIL,
            f"Expected {REQUIRED_DOCUMENTCLASS} without compsoc/compsocconf options.",
        )

    documentclass_line = next((line.strip() for line in tex.splitlines() if line.strip().startswith(r"\documentclass")), "")
    forbidden = [option for option in FORBIDDEN_CLASS_OPTIONS if option in documentclass_line]
    if forbidden:
        _record(checks, "forbidden_ieee_options", FAIL, "Forbidden class options: " + ", ".join(forbidden))
    else:
        _record(checks, "forbidden_ieee_options", PASS, "No compsoc or compsocconf class options detected.")

    risky_hits: list[str] = []
    for pattern in RISKY_SPACING_PATTERNS:
        if re.search(pattern, tex):
            risky_hits.append(pattern)
    if risky_hits:
        _record(checks, "spacing_tampering", FAIL, "Risky manual spacing/font commands: " + ", ".join(risky_hits))
    else:
        _record(checks, "spacing_tampering", PASS, "No risky manual spacing or font-size changes detected.")

    if r"\balance" in tex:
        _record(checks, "last_page_balance", PASS, r"\balance is present before the bibliography.")
    elif r"\IEEEtriggeratref" in tex:
        _record(checks, "last_page_balance", PASS, r"\IEEEtriggeratref is present for bibliography balancing.")
    else:
        _record(checks, "last_page_balance", WARN, r"No bibliography balancing command found; inspect the final page manually.")

    return checks


def _run_pdfinfo(pdf_path: Path) -> str:
    completed = subprocess.run(["pdfinfo", str(pdf_path)], text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "pdfinfo failed")
    return completed.stdout


def check_pdf_info_text(pdfinfo_text: str) -> list[dict[str, Any]]:
    """Return checks from pdfinfo output."""
    checks: list[dict[str, Any]] = []
    pages_match = re.search(r"^Pages:\s+(\d+)", pdfinfo_text, flags=re.MULTILINE)
    page_size_match = re.search(r"^Page size:\s+([\d.]+)\s+x\s+([\d.]+)\s+pts", pdfinfo_text, flags=re.MULTILINE)

    if not pages_match:
        _record(checks, "pdf_pages", FAIL, "Could not read page count from pdfinfo output.")
    else:
        pages = int(pages_match.group(1))
        if pages <= 10:
            _record(checks, "pdf_pages", PASS, f"{pages} pages; within 10-page main-text limit.")
        elif pages <= 12:
            _record(checks, "pdf_pages", WARN, f"{pages} pages; verify that pages after 10 contain references only.")
        else:
            _record(checks, "pdf_pages", FAIL, f"{pages} pages; exceeds 10 pages plus 2 reference pages.")

    if not page_size_match:
        _record(checks, "pdf_page_size", FAIL, "Could not read page size from pdfinfo output.")
    else:
        width = float(page_size_match.group(1))
        height = float(page_size_match.group(2))
        if abs(width - 612.0) < 1 and abs(height - 792.0) < 1:
            _record(checks, "pdf_page_size", PASS, "US Letter page size: 612 x 792 pts.")
        else:
            _record(checks, "pdf_page_size", FAIL, f"Expected US Letter 612 x 792 pts, got {width:g} x {height:g} pts.")
    return checks


def check_pdf_file(pdf_path: str | Path) -> list[dict[str, Any]]:
    """Return PDF-level ICSE format checks."""
    path = Path(pdf_path)
    if not path.exists():
        return [{"name": "pdf_exists", "status": FAIL, "detail": f"Missing PDF: {path}"}]
    try:
        return [{"name": "pdf_exists", "status": PASS, "detail": str(path)}] + check_pdf_info_text(_run_pdfinfo(path))
    except (OSError, RuntimeError) as exc:
        return [
            {"name": "pdf_exists", "status": PASS, "detail": str(path)},
            {"name": "pdfinfo_available", "status": FAIL, "detail": str(exc)},
        ]


def check_latex_log_text(log_text: str) -> list[dict[str, Any]]:
    """Return checks from LaTeX log text."""
    checks: list[dict[str, Any]] = []
    fail_patterns = {
        "latex_errors": r"(^! |LaTeX Error|Emergency stop|Fatal error)",
        "undefined_references": r"(Reference .* undefined|Citation .* undefined|There were undefined references)",
        "overfull_boxes": r"Overfull",
    }
    for name, pattern in fail_patterns.items():
        hits = re.findall(pattern, log_text, flags=re.MULTILINE)
        if hits:
            _record(checks, name, FAIL, f"{len(hits)} issue(s) detected.")
        else:
            _record(checks, name, PASS, "No issue detected.")

    underfull_count = len(re.findall(r"Underfull", log_text))
    if underfull_count:
        _record(checks, "underfull_boxes", WARN, f"{underfull_count} underfull box warning(s); inspect visually.")
    else:
        _record(checks, "underfull_boxes", PASS, "No underfull box warnings.")
    return checks


def check_latex_log(log_path: str | Path) -> list[dict[str, Any]]:
    path = Path(log_path)
    if not path.exists():
        return [{"name": "latex_log_exists", "status": FAIL, "detail": f"Missing LaTeX log: {path}"}]
    return [{"name": "latex_log_exists", "status": PASS, "detail": str(path)}] + check_latex_log_text(_read_text_guess(path))


def summarize(checks: list[dict[str, Any]]) -> dict[str, Any]:
    fail_count = sum(1 for check in checks if check["status"] == FAIL)
    warn_count = sum(1 for check in checks if check["status"] == WARN)
    pass_count = sum(1 for check in checks if check["status"] == PASS)
    return {
        "status": "fail" if fail_count else "pass",
        "pass_count": pass_count,
        "warn_count": warn_count,
        "fail_count": fail_count,
        "checks": checks,
    }


def write_markdown(result: dict[str, Any], out: str | Path) -> None:
    lines = [
        "# ICSE Format Check",
        "",
        f"Overall status: **{result['status']}**",
        "",
        "| Check | Status | Detail |",
        "|---|---:|---|",
    ]
    for check in result["checks"]:
        detail = str(check["detail"]).replace("|", "\\|")
        lines.append(f"| {check['name']} | {check['status']} | {detail} |")
    Path(out).write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check ICSE 2027 paper formatting guardrails")
    parser.add_argument("--tex", default="paper/main.tex")
    parser.add_argument("--pdf", default="paper/main.pdf")
    parser.add_argument("--log", default="paper/build.log")
    parser.add_argument("--out", help="Optional JSON report path")
    parser.add_argument("--markdown", help="Optional Markdown report path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    checks = check_tex_source(args.tex) + check_pdf_file(args.pdf) + check_latex_log(args.log)
    result = summarize(checks)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.markdown:
        Path(args.markdown).parent.mkdir(parents=True, exist_ok=True)
        write_markdown(result, args.markdown)
    print(f"ICSE format check: {result['status']} ({result['fail_count']} fail, {result['warn_count']} warn)")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
