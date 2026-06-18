"""Check the paper PDF/source for double-anonymous submission hygiene."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

LOCAL_USER = os.environ.get("USERNAME") or os.environ.get("USER") or ""

IDENTITY_PATTERNS = {
    "email": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    "orcid": re.compile(r"\bORCID\b|orcid\.org", re.I),
    "acknowledgment": re.compile(r"\bAcknowledge?ments?\b", re.I),
    "funding": re.compile(r"\b(?:grant|funded by|funding|NSF|National Science Foundation)\b", re.I),
    "local_windows_path": re.compile(r"C:\\Users\\|C:/Users/|C:\\\\Users\\\\", re.I),
    "onedrive_path": re.compile(r"\bOneDrive\b", re.I),
    "placeholder": re.compile(r"TO_BE_FILLED|PLACEHOLDER|To be added after anonymous review", re.I),
}

FRONT_MATTER_IDENTITY_PATTERNS = {
    "affiliation": re.compile(
        r"\b(?:University|Institute|Department|School|College|Laboratory|Lab|Inc\.|LLC|Ltd\.|Corporation)\b",
        re.I,
    ),
    "email": IDENTITY_PATTERNS["email"],
}


def _run(command: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, errors="replace", check=False)


def _display(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _extract_pdf_text(pdf_path: Path, out_dir: Path) -> tuple[str, list[dict[str, Any]]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    text_path = out_dir / "submission_pdf_text.txt"
    completed = _run(["pdftotext", "-layout", _display(pdf_path), _display(text_path)])
    if completed.returncode != 0:
        return "", [
            {
                "name": "pdf_text_extract",
                "status": "fail",
                "message": completed.stderr.strip() or "pdftotext failed",
            }
        ]
    return text_path.read_text(encoding="utf-8", errors="replace"), [
        {"name": "pdf_text_extract", "status": "pass", "message": _display(text_path)}
    ]


def _extract_pdf_metadata(pdf_path: Path) -> tuple[str, list[dict[str, Any]]]:
    completed = _run(["pdfinfo", _display(pdf_path)])
    metadata = (completed.stdout or "") + "\n" + (completed.stderr or "")
    status = "pass" if completed.returncode == 0 else "warn"
    return metadata, [
        {
            "name": "pdf_metadata_extract",
            "status": status,
            "message": "pdfinfo ok" if completed.returncode == 0 else completed.stderr.strip(),
        }
    ]


def _front_matter(text: str) -> str:
    lower = text.lower()
    abstract_index = lower.find("abstract")
    if abstract_index >= 0:
        return text[:abstract_index]
    return "\n".join(text.splitlines()[:80])


def _find_patterns(text: str, patterns: dict[str, re.Pattern[str]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for name, pattern in patterns.items():
        matches = list(pattern.finditer(text))
        if matches:
            findings.append({"name": name, "count": len(matches)})
    return findings


def check_double_anonymous_text(pdf_text: str, metadata: str, tex_text: str = "") -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    normalized = " ".join(pdf_text.split())
    front = _front_matter(pdf_text)

    checks.append(
        {
            "name": "anonymous_author_present",
            "status": "pass" if "Anonymous Author(s)" in normalized else "fail",
            "message": "Anonymous Author(s) found." if "Anonymous Author(s)" in normalized else "Missing Anonymous Author(s).",
        }
    )

    front_findings = _find_patterns(front, FRONT_MATTER_IDENTITY_PATTERNS)
    checks.append(
        {
            "name": "front_matter_identity",
            "status": "fail" if front_findings else "pass",
            "message": front_findings or "No email or affiliation terms in front matter.",
        }
    )

    full_patterns = dict(IDENTITY_PATTERNS)
    if LOCAL_USER:
        full_patterns["local_user_id"] = re.compile(re.escape(LOCAL_USER), re.I)
    full_findings = _find_patterns(pdf_text + "\n" + metadata, full_patterns)
    checks.append(
        {
            "name": "full_pdf_identity_leaks",
            "status": "fail" if full_findings else "pass",
            "message": full_findings or "No local paths, acknowledgments, funding, emails, ORCID, or placeholders found.",
        }
    )

    if tex_text:
        author_ok = r"\IEEEauthorblockN{Anonymous Author(s)}" in tex_text
        affiliation_block = r"\IEEEauthorblockA" in tex_text
        checks.append(
            {
                "name": "tex_author_block",
                "status": "pass" if author_ok and not affiliation_block else "fail",
                "message": "TeX author block is anonymous and has no affiliation block."
                if author_ok and not affiliation_block
                else "TeX author block is missing Anonymous Author(s) or contains an affiliation block.",
            }
        )
    return checks


def summarize(checks: list[dict[str, Any]]) -> dict[str, Any]:
    fail_count = sum(1 for check in checks if check["status"] == "fail")
    warn_count = sum(1 for check in checks if check["status"] == "warn")
    return {
        "status": "fail" if fail_count else "pass",
        "fail_count": fail_count,
        "warn_count": warn_count,
        "checks": checks,
    }


def run_double_anonymous_check(pdf_path: Path, tex_path: Path, out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    checks: list[dict[str, Any]] = []
    if not pdf_path.exists():
        checks.append({"name": "pdf_exists", "status": "fail", "message": f"Missing PDF: {_display(pdf_path)}"})
        result = summarize(checks)
    else:
        checks.append({"name": "pdf_exists", "status": "pass", "message": _display(pdf_path)})
        pdf_text, text_checks = _extract_pdf_text(pdf_path, out_dir)
        metadata, metadata_checks = _extract_pdf_metadata(pdf_path)
        checks.extend(text_checks)
        checks.extend(metadata_checks)
        tex_text = tex_path.read_text(encoding="utf-8", errors="replace") if tex_path.exists() else ""
        checks.extend(check_double_anonymous_text(pdf_text, metadata, tex_text))
        result = summarize(checks)

    result["generated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    result["pdf"] = _display(pdf_path)
    result["tex"] = _display(tex_path)
    (out_dir / "double_anonymous_submission_check.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    write_markdown(result, out_dir / "double_anonymous_submission_check.md")
    return result


def write_markdown(result: dict[str, Any], out: Path) -> None:
    lines = [
        "# Double-Anonymous Submission Check",
        "",
        f"Overall status: **{result['status']}**",
        "",
        f"Failures: `{result['fail_count']}`",
        f"Warnings: `{result['warn_count']}`",
        "",
        "| Check | Status | Message |",
        "|---|---:|---|",
    ]
    for check in result["checks"]:
        message = str(check["message"]).replace("|", "\\|")
        lines.append(f"| {check['name']} | {check['status']} | {message} |")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This checks submission anonymity hygiene for the PDF/source. It does not validate empirical claims or replace a human double-anonymous policy review.",
            "",
        ]
    )
    out.write_text("\n".join(lines), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check double-anonymous submission hygiene")
    parser.add_argument("--pdf", default="paper/main.pdf")
    parser.add_argument("--tex", default="paper/main.tex")
    parser.add_argument("--out", default="outputs/double_anonymous_submission_check_20260617")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_double_anonymous_check(ROOT / args.pdf, ROOT / args.tex, ROOT / args.out)
    print(
        "Double-anonymous submission check: "
        f"{result['status']} ({result['fail_count']} fail, {result['warn_count']} warn)"
    )
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
