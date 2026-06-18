"""Build a compact submission-readiness packet for the paper artifact."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_FINAL_HUMAN_MATCHES = Path("outputs/human_match_review_sheet_provisional_verified_20260613.csv")
DEFAULT_REFINED_HUMAN_SCAN = Path("outputs/human_match_web_verification_refined_20260613.csv")
DEFAULT_MANIFEST = Path("data/manifests/real_pilot_full_provisional_verified_manifest_20260613.csv")
DEFAULT_OUT = Path("outputs/submission_readiness_20260614")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def count(rows: list[dict[str, str]], field: str) -> dict[str, int]:
    return dict(Counter(row.get(field, "") for row in rows))


def same_repo_count(rows: list[dict[str, str]]) -> int:
    return sum(1 for row in rows if row.get("ai_repo") and row.get("ai_repo") == row.get("human_repo"))


def write_human_match_summary(
    final_rows: list[dict[str, str]], refined_rows: list[dict[str, str]], manifest_rows: list[dict[str, str]], out_dir: Path
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    final_decisions = count(final_rows, "decision")
    refined_verdicts = count(refined_rows, "refined_verdict")
    manifest_author_types = count(manifest_rows, "author_type")
    manifest_sources = count(manifest_rows, "source")

    weak_context_rows = [row for row in final_rows if "weak_context" in row.get("decision", "")]
    replacement_rows = [row for row in final_rows if "replacement" in row.get("decision", "")]
    clean_like = sum(
        1
        for row in final_rows
        if row.get("decision") in {"provisional_clean_scan", "provisional_replacement_clean_scan"}
    )

    summary = {
        "final_human_match_rows": len(final_rows),
        "same_repository_matches": same_repo_count(final_rows),
        "broad_or_replacement_matches": len(final_rows) - same_repo_count(final_rows),
        "final_decision_counts": final_decisions,
        "initial_refined_verdict_counts": refined_verdicts,
        "original_candidates_rejected_or_replaced": refined_verdicts.get("reject_or_replace_visible_ai_or_bot_marker", 0),
        "replacement_rows": len(replacement_rows),
        "clean_or_replacement_clean_rows": clean_like,
        "weak_context_rows": len(weak_context_rows),
        "manifest_author_type_counts": manifest_author_types,
        "manifest_source_counts": manifest_sources,
        "boundary": (
            "Human matches are provisionally verified for corpus balance only. "
            "They are not used for causal authorship-group comparison."
        ),
    }
    (out_dir / "human_match_verification_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    csv_fields = [
        "ai_instance_id",
        "ai_repo",
        "human_repo",
        "human_pr_url",
        "decision",
        "match_basis",
        "refined_note",
    ]
    with (out_dir / "human_match_verification_summary.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()
        for row in final_rows:
            writer.writerow({field: row.get(field, "") for field in csv_fields})

    lines = [
        "# Human-Match Verification Summary",
        "",
        "Status: provisional verification complete; final human confirmation still required before any authorship-group claim.",
        "",
        "## Counts",
        "",
        f"- Final human-match rows: {summary['final_human_match_rows']}",
        f"- Same-repository matches: {summary['same_repository_matches']}",
        f"- Broad or replacement matches: {summary['broad_or_replacement_matches']}",
        f"- Original candidates rejected or replaced after refined scan: {summary['original_candidates_rejected_or_replaced']}",
        f"- Final rows with clean or replacement-clean scan: {summary['clean_or_replacement_clean_rows']}",
        f"- Final rows requiring weak-context manual check: {summary['weak_context_rows']}",
        "",
        "## Final Decision Counts",
        "",
    ]
    for key, value in sorted(final_decisions.items()):
        lines.append(f"- `{key}`: {value}")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            summary["boundary"],
            "",
            "The paper should continue to describe the matched side as corpus balance and tool exercise, not as a causal comparison.",
            "",
            "## Remaining Manual Checks",
            "",
        ]
    )
    if weak_context_rows:
        for row in weak_context_rows:
            lines.append(
                f"- `{row.get('ai_instance_id')}` -> {row.get('human_pr_url')}: {row.get('refined_note')}"
            )
    else:
        lines.append("- None flagged by the current verification sheet.")
    lines.append("")
    (out_dir / "human_match_verification_summary.md").write_text("\n".join(lines), encoding="utf-8")
    return summary


def path_status(path: Path) -> str:
    return "present" if path.exists() else "missing"


def write_release_checklist(out_dir: Path, human_summary: dict[str, Any]) -> None:
    items = [
        ("Functional smoke workflow", Path("scripts/reproduce_artifact_smoke.py"), "present"),
        ("Completed annotation CSV", Path("outputs/real_pilot_mixed_source_annotation_sheet_completed_20260613.csv"), "present"),
        ("Annotation statistics", Path("outputs/real_pilot_mixed_source_annotation_paper_results_20260613/annotation_stats/agreement_summary.json"), "present"),
        ("Pilot statistical treatment", Path("outputs/real_pilot_mixed_source_annotation_paper_results_20260613/pilot_statistical_treatment.json"), "present"),
        ("Human-match verification summary", out_dir / "human_match_verification_summary.json", "present"),
        ("AI assistance disclosure", Path(".paper/ai_assistance_disclosure.md"), "present"),
        ("Archival DOI", Path("DOI_TO_BE_ADDED_AFTER_REVIEW"), "pending"),
        ("Public repository URL", Path("PUBLIC_REPOSITORY_URL_TO_BE_ADDED_AFTER_REVIEW"), "pending"),
        ("Second annotator or external audit", Path("SECOND_ANNOTATOR_OR_EXTERNAL_AUDIT"), "pending"),
    ]
    lines = [
        "# Submission Readiness Checklist",
        "",
        "This checklist separates local artifact readiness from final archival and multi-annotator work.",
        "",
        "| Item | Status | Note |",
        "|---|---:|---|",
    ]
    for label, path, expected in items:
        status = path_status(path) if expected == "present" else expected
        note = str(path) if expected == "present" else "Not available in the current anonymous-review snapshot."
        lines.append(f"| {label} | {status} | `{note}` |")
    lines.extend(
        [
            "",
            "## Human-Match Boundary",
            "",
            (
                f"The packet contains {human_summary['final_human_match_rows']} provisional human matches, "
                f"including {human_summary['same_repository_matches']} same-repository matches and "
                f"{human_summary['broad_or_replacement_matches']} broad/replacement matches."
            ),
            "Use them for corpus balance only; do not claim an authorship-group effect.",
            "",
        ]
    )
    (out_dir / "release_readiness_checklist.md").write_text("\n".join(lines), encoding="utf-8")


def build_packet(final_human_matches: Path, refined_human_scan: Path, manifest: Path, out_dir: Path) -> dict[str, Any]:
    final_rows = read_csv(final_human_matches)
    refined_rows = read_csv(refined_human_scan)
    manifest_rows = read_csv(manifest)
    out_dir.mkdir(parents=True, exist_ok=True)
    human_summary = write_human_match_summary(final_rows, refined_rows, manifest_rows, out_dir)
    write_release_checklist(out_dir, human_summary)
    packet = {
        "human_match_verification": human_summary,
        "outputs": [
            str(out_dir / "human_match_verification_summary.json"),
            str(out_dir / "human_match_verification_summary.csv"),
            str(out_dir / "human_match_verification_summary.md"),
            str(out_dir / "release_readiness_checklist.md"),
        ],
    }
    (out_dir / "submission_packet_manifest.json").write_text(
        json.dumps(packet, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return packet


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--final-human-matches", type=Path, default=DEFAULT_FINAL_HUMAN_MATCHES)
    parser.add_argument("--refined-human-scan", type=Path, default=DEFAULT_REFINED_HUMAN_SCAN)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    packet = build_packet(args.final_human_matches, args.refined_human_scan, args.manifest, args.out)
    print(f"Submission readiness packet written to {args.out}")
    print(json.dumps(packet["human_match_verification"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
