"""Build portal-ready AI assistance disclosure materials."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / ".paper" / "ai_assistance_disclosure.md"


def _strip_heading(text: str) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    body = []
    for line in lines:
        if line.startswith("# "):
            continue
        if line.startswith("Status:"):
            continue
        if line.startswith("Before camera-ready release"):
            continue
        body.append(line)
    return "\n".join(body).strip()


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def build_ai_disclosure_packet(source: Path, out_dir: Path) -> dict[str, Any]:
    if not source.is_absolute():
        source = ROOT / source
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    source_text = source.read_text(encoding="utf-8")
    portal_text = _strip_heading(source_text)
    result = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "ready_for_portal_adaptation",
        "source": _display(source),
        "portal_disclosure": "outputs/ai_assistance_disclosure_packet_20260617/PORTAL_AI_DISCLOSURE.md",
        "word_count": _word_count(portal_text),
        "claim_boundary": (
            "AI assistance was used for coding, editing, debugging, summarization, and internal review. "
            "AI tools were not operators/annotators and were not responsible for claims, citations, audit codes, or final text."
        ),
    }
    (out_dir / "PORTAL_AI_DISCLOSURE.md").write_text(
        "# Portal AI Assistance Disclosure\n\n" + portal_text + "\n",
        encoding="utf-8",
    )
    write_checklist(out_dir / "AI_DISCLOSURE_CHECKLIST.md")
    (out_dir / "ai_assistance_disclosure_status.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return result


def _display(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def write_checklist(out: Path) -> None:
    lines = [
        "# AI Assistance Disclosure Checklist",
        "",
        "- Use `PORTAL_AI_DISCLOSURE.md` when the submission portal asks for AI tool usage.",
        "- Preserve the boundary that AI tools were assistants, not authors, annotators, operators, or arbiters of claims.",
        "- Do not claim AI-generated labels, AI-validated citations, or AI-established reliability.",
        "- Before camera-ready submission, adapt the wording to the exact venue field if ICSE/ACM provides one.",
        "- Keep the disclosure outside the anonymous PDF unless the venue explicitly asks for in-PDF disclosure at submission time.",
        "",
    ]
    out.write_text("\n".join(lines), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build AI assistance disclosure packet")
    parser.add_argument("--source", default=".paper/ai_assistance_disclosure.md")
    parser.add_argument("--out", default="outputs/ai_assistance_disclosure_packet_20260617")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = build_ai_disclosure_packet(ROOT / args.source, ROOT / args.out)
    print(f"AI assistance disclosure packet written: {args.out} ({result['word_count']} words)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
