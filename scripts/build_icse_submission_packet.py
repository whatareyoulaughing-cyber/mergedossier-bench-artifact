"""Build a concrete ICSE submission packet from current local artifacts."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _rel(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _latex_to_text(text: str) -> str:
    replacements = {
        r"\tool{}": "MergeDossier-Bench",
        r"\tool": "MergeDossier-Bench",
        r"\%": "%",
        "--": "-",
    }
    cleaned = text
    for src, dst in replacements.items():
        cleaned = cleaned.replace(src, dst)
    cleaned = re.sub(r"\\[A-Za-z]+\*?(?:\[[^\]]*\])?(?:\{([^{}]*)\})", r"\1", cleaned)
    cleaned = cleaned.replace("{", "").replace("}", "")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def extract_paper_metadata(tex_path: Path) -> dict[str, Any]:
    text = tex_path.read_text(encoding="utf-8")
    title_match = re.search(r"\\title\{(?P<title>.*?)\}", text, flags=re.DOTALL)
    abstract_match = re.search(r"\\begin\{abstract\}(?P<abstract>.*?)\\end\{abstract\}", text, flags=re.DOTALL)
    keywords_match = re.search(
        r"\\begin\{IEEEkeywords\}(?P<keywords>.*?)\\end\{IEEEkeywords\}",
        text,
        flags=re.DOTALL,
    )
    title = _latex_to_text(title_match.group("title")) if title_match else ""
    abstract = _latex_to_text(abstract_match.group("abstract")) if abstract_match else ""
    keywords = _latex_to_text(keywords_match.group("keywords")) if keywords_match else ""
    return {
        "title": title,
        "abstract": abstract,
        "abstract_word_count": len(re.findall(r"\b\w+\b", abstract)),
        "keywords": keywords,
    }


def _copy_file(root: Path, src: Path, dst: Path) -> dict[str, Any]:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return {"source": _rel(root, src), "packet_path": _rel(root, dst), "bytes": dst.stat().st_size}


def build_icse_submission_packet(root: Path, out_dir: Path) -> dict[str, Any]:
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    metadata = extract_paper_metadata(root / "paper/main.tex")
    dashboard = _read_json(root / "outputs/submission_blocker_dashboard_20260617/submission_blocker_dashboard.json")
    release_summary = _read_json(root / "outputs/release/release_zip_summary.json")
    readiness = _read_json(root / "outputs/paper_readiness_check_20260617_handoff_gap/paper_readiness_check.json")
    action_status = _read_json(root / "outputs/submission_action_packet_20260617/action_status.json")

    files_dir = out_dir / "files_for_submission"
    copied: list[dict[str, Any]] = []
    for src, name, role in [
        (root / "paper/main.pdf", "main.pdf", "anonymous_pdf_submission"),
        (
            root / "outputs/release/MergeDossier-Bench-anonymous-review.zip",
            "MergeDossier-Bench-anonymous-review.zip",
            "anonymous_artifact_archive",
        ),
        (
            root / "outputs/zenodo_deposit_packet_20260617/SHA256SUMS.txt",
            "SHA256SUMS.txt",
            "artifact_checksum",
        ),
    ]:
        if src.exists():
            row = _copy_file(root, src, files_dir / name)
            row["role"] = role
            copied.append(row)

    p0_open = int(dashboard.get("p0_open_count", 0) or 0)
    status = "ready_except_external_actions" if p0_open else "submission_ready_local"
    result = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": status,
        "paper_metadata": metadata,
        "dashboard_status": dashboard.get("status", "missing"),
        "p0_open_count": p0_open,
        "paper_readiness_status": readiness.get("status", "missing"),
        "release_file_count": release_summary.get("file_count"),
        "release_zip_bytes": release_summary.get("zip_bytes"),
        "action_packet_status": action_status.get("status", "missing"),
        "copied_files": copied,
        "claim_boundary": (
            "Submit as a handoff-evidence gap / review-evidence availability paper. "
            "Do not claim correctness, mergeability, reviewer utility, AI-vs-human effects, "
            "all-GitHub rates, or inter-rater reliability."
        ),
    }

    (out_dir / "submission_packet_status.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    write_portal_fields(metadata, out_dir / "PORTAL_FIELDS.md")
    write_checklist(result, out_dir / "ICSE_SUBMISSION_CHECKLIST_ZH.md")
    write_manifest(result, out_dir / "submission_file_manifest.csv")
    return result


def write_portal_fields(metadata: dict[str, Any], out: Path) -> None:
    lines = [
        "# Portal Fields",
        "",
        "## Title",
        "",
        metadata["title"],
        "",
        "## Abstract",
        "",
        metadata["abstract"],
        "",
        f"Abstract word count: `{metadata['abstract_word_count']}`",
        "",
        "## Keywords",
        "",
        metadata["keywords"],
        "",
    ]
    out.write_text("\n".join(lines), encoding="utf-8")


def write_checklist(result: dict[str, Any], out: Path) -> None:
    lines = [
        "# ICSE Submission Checklist",
        "",
        f"Packet status: **{result['status']}**",
        "",
        "## Files In This Packet",
        "",
    ]
    for row in result["copied_files"]:
        packet_path = Path(row["packet_path"])
        lines.append(f"- `{packet_path.name}` - {row['role']} ({row['bytes']} bytes)")
    lines.extend(
        [
            "",
            "## Portal Copy/Paste",
            "",
            "- Use `PORTAL_FIELDS.md` for title, abstract, and keywords.",
            "- Upload `files_for_submission/main.pdf` as the anonymous PDF.",
            "- Use the artifact archive only where the venue or artifact process asks for it.",
            "",
            "## Required Before High-Confidence Submission",
            "",
        ]
    )
    if result["p0_open_count"]:
        lines.extend(
            [
                f"- P0 open count is `{result['p0_open_count']}`.",
                "- Complete the external audit slice or keep it explicitly framed as not completed.",
                "- Publish the archive/public repository and record the real DOI/URL before claiming artifact availability.",
                "- Use `outputs/submission_action_packet_20260617/NEXT_ACTIONS_ZH.md` for the exact commands.",
            ]
        )
    else:
        lines.append("- No P0 blockers are currently reported by the dashboard.")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "- Do not claim patch correctness.",
            "- Do not claim mergeability.",
            "- Do not claim reviewer utility.",
            "- Do not claim AI-vs-human causal effects.",
            "- Do not claim all-GitHub population rates.",
            "- Do not claim inter-rater reliability unless a completed external audit supports it.",
            "",
        ]
    )
    out.write_text("\n".join(lines), encoding="utf-8")


def write_manifest(result: dict[str, Any], out: Path) -> None:
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["role", "packet_path", "source", "bytes"])
        writer.writeheader()
        for row in result["copied_files"]:
            writer.writerow(
                {
                    "role": row["role"],
                    "packet_path": row["packet_path"],
                    "source": row["source"],
                    "bytes": row["bytes"],
                }
            )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build ICSE submission packet")
    parser.add_argument("--out", default="outputs/icse_submission_packet_20260617")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = build_icse_submission_packet(ROOT, ROOT / args.out)
    print(
        "ICSE submission packet written: "
        f"{args.out} ({result['status']}, P0 open={result['p0_open_count']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
