"""Final PDF proofread gate for the paper artifact.

This check complements format/layout gates. It renders a contact sheet for
page-by-page visual review and audits extracted PDF text for unresolved
placeholders, broken references, and missing paper identity phrases.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_PHRASES = [
    "MergeDossier-Bench",
    "Handoff-Evidence Gap",
    "A diff is not a dossier",
    "A dossier must cite its evidence",
    "AIDev-pop",
    "single-operator",
]

PLACEHOLDER_PATTERNS = {
    "todo": re.compile(r"\bTODO\b", re.I),
    "fixme": re.compile(r"\bFIXME\b", re.I),
    "tbd": re.compile(r"\bTBD\b", re.I),
    "placeholder": re.compile(r"\bPLACEHOLDER\b", re.I),
    "unresolved_reference": re.compile(r"\[\?\]|\?\?"),
    "latex_warning_token": re.compile(r"undefined references|undefined citations", re.I),
}

RISK_TERMS = [
    "inter-rater reliability",
    "all GitHub",
    "AI-vs-human",
    "reviewer utility",
    "mergeability",
    "patch correctness",
]


def _run(command: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        errors="replace",
        check=False,
    )


def _cmd_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _extract_pdf_text(pdf_path: Path, out_dir: Path) -> tuple[str, dict[str, Any]]:
    text_path = out_dir / "paper_text.txt"
    completed = _run(["pdftotext", "-layout", _cmd_path(pdf_path), _cmd_path(text_path)])
    if completed.returncode != 0:
        return "", {
            "name": "pdf_text_extract",
            "status": "fail",
            "detail": completed.stderr.strip() or "pdftotext failed",
        }
    return text_path.read_text(encoding="utf-8", errors="replace"), {
        "name": "pdf_text_extract",
        "status": "pass",
        "detail": str(text_path.relative_to(ROOT)),
    }


def _render_contact_sheet(pdf_path: Path, out_dir: Path) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    pages_dir = out_dir / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    prefix = pages_dir / "page"
    render = _run(["pdftoppm", "-png", "-r", "120", _cmd_path(pdf_path), _cmd_path(prefix)])
    if render.returncode != 0:
        checks.append(
            {
                "name": "pdf_page_render",
                "status": "fail",
                "detail": render.stderr.strip() or "pdftoppm failed",
            }
        )
        return checks
    page_images = sorted(pages_dir.glob("page-*.png"))
    if not page_images:
        checks.append({"name": "pdf_page_render", "status": "fail", "detail": "No page images produced."})
        return checks
    checks.append({"name": "pdf_page_render", "status": "pass", "detail": f"{len(page_images)} page image(s)."})

    contact = out_dir / "contact.png"
    montage = _run(
        [
            "magick",
            "montage",
            *[_cmd_path(path) for path in page_images],
            "-thumbnail",
            "520x672",
            "-tile",
            "2x",
            "-geometry",
            "+16+16",
            "-background",
            "white",
            _cmd_path(contact),
        ]
    )
    if montage.returncode != 0:
        checks.append(
            {
                "name": "contact_sheet",
                "status": "fail",
                "detail": montage.stderr.strip() or "ImageMagick montage failed",
            }
        )
    else:
        checks.append({"name": "contact_sheet", "status": "pass", "detail": str(contact.relative_to(ROOT))})
    return checks


def check_text_quality(text: str) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    normalized = " ".join(text.split())
    missing = [phrase for phrase in REQUIRED_PHRASES if phrase.lower() not in normalized.lower()]
    checks.append(
        {
            "name": "required_identity_phrases",
            "status": "fail" if missing else "pass",
            "detail": "Missing: " + ", ".join(missing) if missing else "All required paper identity phrases found.",
        }
    )

    placeholder_findings = []
    for name, pattern in PLACEHOLDER_PATTERNS.items():
        count = len(pattern.findall(text))
        if count:
            placeholder_findings.append(f"{name}={count}")
    checks.append(
        {
            "name": "placeholder_tokens",
            "status": "fail" if placeholder_findings else "pass",
            "detail": "; ".join(placeholder_findings) if placeholder_findings else "No TODO/TBD/unresolved-reference tokens found.",
        }
    )

    risk_counts = {
        term: len(re.findall(re.escape(term), normalized, flags=re.I))
        for term in RISK_TERMS
    }
    checks.append(
        {
            "name": "claim_boundary_terms",
            "status": "pass",
            "detail": ", ".join(f"{term}={count}" for term, count in risk_counts.items()),
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


def write_markdown(result: dict[str, Any], out: Path) -> None:
    lines = [
        "# Final PDF Proofread",
        "",
        f"Overall status: **{result['status']}**",
        "",
        "| Check | Status | Detail |",
        "|---|---:|---|",
    ]
    for check in result["checks"]:
        detail = str(check["detail"]).replace("|", "\\|")
        lines.append(f"| {check['name']} | {check['status']} | {detail} |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This gate checks the rendered PDF artifact for paper identity, unresolved placeholders, and a generated contact sheet for page-by-page visual review. It supports submission polish; it does not establish new empirical validity.",
            "",
        ]
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")


def run_final_pdf_proofread(pdf_path: Path, out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    checks: list[dict[str, Any]] = []
    if not pdf_path.exists():
        checks.append({"name": "pdf_exists", "status": "fail", "detail": f"Missing PDF: {pdf_path}"})
        result = summarize(checks)
    else:
        checks.append({"name": "pdf_exists", "status": "pass", "detail": str(pdf_path.relative_to(ROOT))})
        checks.extend(_render_contact_sheet(pdf_path, out_dir))
        text, extract_check = _extract_pdf_text(pdf_path, out_dir)
        checks.append(extract_check)
        if text:
            checks.extend(check_text_quality(text))
        result = summarize(checks)

    result["generated_at"] = datetime.now(timezone.utc).isoformat()
    result["pdf"] = str(pdf_path.relative_to(ROOT)) if pdf_path.exists() else str(pdf_path)
    (out_dir / "final_pdf_proofread.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    write_markdown(result, out_dir / "final_pdf_proofread.md")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run final PDF proofread gate")
    parser.add_argument("--pdf", default="paper/main.pdf")
    parser.add_argument("--out", default="outputs/final_pdf_proofread_20260617")
    args = parser.parse_args(argv)
    result = run_final_pdf_proofread(ROOT / args.pdf, ROOT / args.out)
    print(
        "Final PDF proofread: "
        f"{result['status']} ({result['fail_count']} fail, {result['warn_count']} warn)"
    )
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
