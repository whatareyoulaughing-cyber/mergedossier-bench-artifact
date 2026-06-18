"""Validate AI assistance disclosure wording and placement."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_PATTERNS = {
    "ai_assistance_used": re.compile(r"AI .*assist|AI assistance|AI tools", re.I | re.S),
    "authors_responsible": re.compile(r"authors? remained responsible|responsible for all research", re.I),
    "not_operators": re.compile(r"not treated as operators|not .*annotators|not operators", re.I),
    "audit_boundary": re.compile(r"single-operator|delayed repeats", re.I),
    "no_inter_rater_claim": re.compile(r"does not claim inter-rater reliability|not claim inter-rater", re.I),
    "no_utility_claim": re.compile(r"does not claim .*reviewer utility|not claim .*reviewer utility", re.I | re.S),
    "no_all_github_claim": re.compile(r"all-GitHub\s+population rates", re.I),
}

FORBIDDEN_PATTERNS = {
    "ai_authored_final_text": re.compile(r"AI (?:wrote|authored) (?:the )?final", re.I),
    "ai_annotator": re.compile(r"AI (?:annotator|operator|rater)", re.I),
    "validated_by_ai": re.compile(r"validated by AI|AI-validated", re.I),
    "old_population_rate_boundary": re.compile(r"does not claim population-level rates", re.I),
    "inter_rater_established": re.compile(r"inter-rater reliability (?:was|is) established", re.I),
}


def _run(command: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, errors="replace", check=False)


def _display(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _extract_pdf_text(pdf_path: Path) -> str:
    completed = _run(["pdftotext", "-layout", _display(pdf_path), "-"])
    if completed.returncode != 0:
        return ""
    return completed.stdout


def check_ai_disclosure(source: Path, packet_dir: Path, pdf_path: Path | None = None, out_dir: Path | None = None) -> dict[str, Any]:
    if not source.is_absolute():
        source = ROOT / source
    if not packet_dir.is_absolute():
        packet_dir = ROOT / packet_dir
    if pdf_path is not None and not pdf_path.is_absolute():
        pdf_path = ROOT / pdf_path
    text_parts = []
    if source.exists():
        text_parts.append(source.read_text(encoding="utf-8", errors="replace"))
    portal = packet_dir / "PORTAL_AI_DISCLOSURE.md"
    if portal.exists():
        text_parts.append(portal.read_text(encoding="utf-8", errors="replace"))
    text = "\n".join(text_parts)

    failures: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    if not source.exists():
        failures.append({"name": "source_missing", "message": f"Missing {_display(source)}"})
    if not portal.exists():
        failures.append({"name": "portal_disclosure_missing", "message": f"Missing {_display(portal)}"})

    for name, pattern in REQUIRED_PATTERNS.items():
        if not pattern.search(text):
            failures.append({"name": f"required_missing:{name}", "message": f"Missing required disclosure pattern {name}."})

    for name, pattern in FORBIDDEN_PATTERNS.items():
        if pattern.search(text):
            failures.append({"name": f"forbidden:{name}", "message": f"Forbidden disclosure wording matched {name}."})

    word_count = len(re.findall(r"\b\w+\b", text))
    if word_count < 80:
        warnings.append({"name": "disclosure_short", "message": f"Disclosure text is short: {word_count} words."})
    if word_count > 500:
        warnings.append({"name": "disclosure_long", "message": f"Disclosure text is long: {word_count} words."})

    if pdf_path and pdf_path.exists():
        pdf_text = _extract_pdf_text(pdf_path)
        if "AI Assistance Disclosure" in pdf_text or "AI tools were used" in pdf_text:
            warnings.append(
                {
                    "name": "disclosure_in_pdf",
                    "message": "AI disclosure text appears in the anonymous PDF; confirm venue requires in-PDF disclosure.",
                }
            )

    result = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "fail" if failures else "pass",
        "failure_count": len(failures),
        "warning_count": len(warnings),
        "failures": failures,
        "warnings": warnings,
        "source": _display(source),
        "packet_dir": _display(packet_dir),
        "word_count": word_count,
    }
    if out_dir is not None:
        if not out_dir.is_absolute():
            out_dir = ROOT / out_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "ai_assistance_disclosure_check.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        write_markdown(result, out_dir / "ai_assistance_disclosure_check.md")
    return result


def write_markdown(result: dict[str, Any], out: Path) -> None:
    lines = [
        "# AI Assistance Disclosure Check",
        "",
        f"Overall status: **{result['status']}**",
        "",
        f"Failures: `{result['failure_count']}`",
        f"Warnings: `{result['warning_count']}`",
        "",
    ]
    if result["failures"]:
        lines.extend(["## Failures", "", "| Check | Message |", "|---|---|"])
        for failure in result["failures"]:
            lines.append(f"| {failure['name']} | {str(failure['message']).replace('|', '\\|')} |")
    if result["warnings"]:
        lines.extend(["## Warnings", "", "| Check | Message |", "|---|---|"])
        for warning in result["warnings"]:
            lines.append(f"| {warning['name']} | {str(warning['message']).replace('|', '\\|')} |")
    lines.extend(
        [
            "## Boundary",
            "",
            "This validates disclosure wording and placement. It does not decide the venue's final AI disclosure policy.",
            "",
        ]
    )
    out.write_text("\n".join(lines), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check AI assistance disclosure")
    parser.add_argument("--source", default=".paper/ai_assistance_disclosure.md")
    parser.add_argument("--packet", default="outputs/ai_assistance_disclosure_packet_20260617")
    parser.add_argument("--pdf", default="paper/main.pdf")
    parser.add_argument("--out", default="outputs/ai_assistance_disclosure_check_20260617")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = check_ai_disclosure(ROOT / args.source, ROOT / args.packet, ROOT / args.pdf, ROOT / args.out)
    print(
        "AI assistance disclosure check: "
        f"{result['status']} ({result['failure_count']} fail, {result['warning_count']} warn)"
    )
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
