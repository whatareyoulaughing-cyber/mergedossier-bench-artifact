"""Command-line interface for MergeDossier-Bench."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any

from .annotation_stats import write_annotation_stats
from .corpus import summarize_corpus
from .dossier_cards import make_dossier_cards
from .dossier_builder import build_skeleton_dossier
from .label_studio import (
    create_reliability_sample,
    export_annotation_csv_template,
    export_annotation_tasks,
    validate_annotation_csv,
)
from .perturbation import run_perturbation_suite
from .pilot_analysis import run_pilot_analysis
from .provenance import audit_provenance
from .review_demands import extract_review_demands
from .scoring import score_dossier
from .seed_builder import (
    load_seed_manifest,
    lint_seed_manifest,
    reconstruct_dossier_from_raw,
    reconstruct_dossiers_from_raw_dir,
    validate_seed_manifest,
    write_seed_corpus,
)
from .validators import load_json, validate_file


def _write_json(data: dict[str, Any], path: str | Path | None) -> None:
    text = json.dumps(data, indent=2, ensure_ascii=False)
    if path:
        Path(path).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


def cmd_validate(args: argparse.Namespace) -> int:
    errors = validate_file(args.file, args.kind)
    if errors:
        print(f"INVALID: {args.file}", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"VALID: {args.file}")
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    dossier = load_json(args.dossier)
    report = score_dossier(dossier)
    _write_json(report, args.out)
    return 0


def cmd_build_dossier(args: argparse.Namespace) -> int:
    instance = load_json(args.instance)
    dossier = build_skeleton_dossier(instance)
    _write_json(dossier, args.out)
    return 0


def cmd_leaderboard(args: argparse.Namespace) -> int:
    rows = []
    for report_path in args.reports:
        report = load_json(report_path)
        rows.append(
            {
                "dossier_id": report.get("dossier_id", "UNKNOWN"),
                "evidence_sufficiency_score": report.get("evidence_sufficiency_score", 0),
                "readiness_band": report.get("readiness_band", "unknown"),
                "missing_evidence": ";".join(report.get("missing_evidence", [])),
            }
        )
    rows.sort(key=lambda r: float(r["evidence_sufficiency_score"]), reverse=True)
    if args.out:
        with Path(args.out).open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["dossier_id", "evidence_sufficiency_score", "readiness_band", "missing_evidence"])
            writer.writeheader()
            writer.writerows(rows)
    else:
        for row in rows:
            print(row)
    return 0


def cmd_summarize(args: argparse.Namespace) -> int:
    summary = summarize_corpus(args.dossiers, args.out)
    print(
        "Corpus summary written: "
        f"{summary['valid_dossiers']} valid, {summary['invalid_dossiers']} invalid "
        f"of {summary['total_dossiers']} dossiers"
    )
    return 0


def cmd_export_annotation_tasks(args: argparse.Namespace) -> int:
    tasks = export_annotation_tasks(args.dossiers, args.out)
    print(f"Annotation tasks written: {len(tasks)} tasks -> {args.out}")
    return 0


def cmd_annotation_stats(args: argparse.Namespace) -> int:
    summary = write_annotation_stats(args.annotations, args.out)
    print(
        "Annotation stats written: "
        f"{summary['total_annotations']} annotations across {summary['total_tasks']} tasks"
    )
    return 0


def cmd_export_annotation_csv(args: argparse.Namespace) -> int:
    rows = export_annotation_csv_template(args.tasks, args.out, annotator_id=args.annotator_id)
    print(f"Annotation CSV written: {len(rows)} rows -> {args.out}")
    return 0


def cmd_validate_annotation_csv(args: argparse.Namespace) -> int:
    result = validate_annotation_csv(args.annotations, require_complete=not args.allow_incomplete)
    if args.out:
        _write_json(result, args.out)
    print(
        "Annotation CSV validation: "
        f"{result['completed_rows']} complete rows, {result['incomplete_rows']} incomplete rows, "
        f"{len(result['errors'])} errors"
    )
    if result["errors"]:
        for error in result["errors"][:20]:
            print(f"ERROR: {error}", file=sys.stderr)
        if len(result["errors"]) > 20:
            print(f"ERROR: ... {len(result['errors']) - 20} more", file=sys.stderr)
    elif result["warnings"]:
        for warning in result["warnings"][:10]:
            print(f"WARNING: {warning}", file=sys.stderr)
    return 0 if result["valid"] else 1


def cmd_create_reliability_sample(args: argparse.Namespace) -> int:
    tasks = create_reliability_sample(args.tasks, args.out, rate=args.rate, min_count=args.min_count, seed=args.seed)
    print(f"Reliability sample written: {len(tasks)} tasks -> {args.out}")
    return 0


def cmd_build_seed_corpus(args: argparse.Namespace) -> int:
    rows = load_seed_manifest(args.manifest)
    if args.limit is not None:
        rows = rows[: args.limit]
    errors = validate_seed_manifest(rows)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    if args.dry_run:
        print(f"Seed corpus dry run: {len(rows)} manifest rows")
        for row in rows:
            print(f"- {row['instance_id']} {row['repo']}#{row['pr_number']} ({row['author_type']}, {row['agent_name']})")
        return 0
    if not args.use_fixtures and not args.live:
        print("ERROR: provide --use-fixtures or --live, or use --dry-run", file=sys.stderr)
        return 1
    token = os.environ.get(args.github_token_env) if args.live else None
    summary = write_seed_corpus(
        rows,
        args.out,
        fixture_dir=args.use_fixtures,
        live=args.live,
        github_token=token,
        api_base=args.api_base,
        sleep_seconds=args.sleep_seconds,
        continue_on_error=args.continue_on_error,
        limit=None,
        force=args.force,
    )
    print(
        "Seed corpus written: "
        f"{summary['reconstructed_dossiers']} dossiers, {summary['missing_fixtures']} missing fixtures"
    )
    return 0


def cmd_lint_seed_manifest(args: argparse.Namespace) -> int:
    rows = load_seed_manifest(args.manifest)
    result = lint_seed_manifest(rows)
    for warning in result["warnings"]:
        print(f"WARNING: {warning}")
    for error in result["errors"]:
        print(f"ERROR: {error}", file=sys.stderr)
    if not result["errors"]:
        print(f"Manifest lint passed: {len(rows)} rows, {len(result['warnings'])} warnings")
        return 0
    return 1


def cmd_reconstruct_dossier(args: argparse.Namespace) -> int:
    raw_path = Path(args.raw)
    out_path = Path(args.out)
    if raw_path.is_dir():
        dossiers = reconstruct_dossiers_from_raw_dir(raw_path, out_path)
        print(f"Reconstructed {len(dossiers)} dossiers -> {out_path}")
        return 0
    raw = load_json(raw_path)
    dossier = reconstruct_dossier_from_raw(raw)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(dossier, out_path)
    print(f"Reconstructed dossier -> {out_path}")
    return 0


def cmd_audit_provenance(args: argparse.Namespace) -> int:
    summary = audit_provenance(args.dossiers, args.out)
    print(
        "Provenance audit written: "
        f"{summary['dossiers_with_provenance']} provenance-rich dossiers "
        f"of {summary['total_dossiers']} valid dossiers"
    )
    return 0


def cmd_run_perturbation_suite(args: argparse.Namespace) -> int:
    summary = run_perturbation_suite(args.out)
    print(
        "Perturbation suite written: "
        f"{summary['passed']} passed, {summary['failed']} failed "
        f"of {summary['total_checks']} checks"
    )
    return 0 if summary["failed"] == 0 else 1


def cmd_make_dossier_cards(args: argparse.Namespace) -> int:
    summary = make_dossier_cards(args.dossiers, args.out, fmt=args.format)
    print(f"Dossier cards written: {summary['total_cards']} cards -> {args.out}")
    return 0


def cmd_pilot_analysis(args: argparse.Namespace) -> int:
    summary = run_pilot_analysis(args.dossiers, args.out)
    print(f"Pilot analysis written: {summary['valid_dossiers']} valid dossiers -> {args.out}")
    return 0


def cmd_extract_review_demands(args: argparse.Namespace) -> int:
    summary = extract_review_demands(args.raw, args.out)
    print(
        "Exploratory review-demand signals written: "
        f"{summary['total_review_demand_signals']} signals from "
        f"{summary['records_with_review_demand_signals']} raw records -> {args.out}"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MergeDossier-Bench CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser("validate", help="Validate a JSON artifact against a schema")
    p_validate.add_argument("--kind", required=True, choices=["dossier", "instance", "annotation", "score", "github_pr_raw"])
    p_validate.add_argument("--file", required=True)
    p_validate.set_defaults(func=cmd_validate)

    p_score = sub.add_parser("score", help="Score a MergeDossier JSON file")
    p_score.add_argument("--dossier", required=True)
    p_score.add_argument("--out")
    p_score.set_defaults(func=cmd_score)

    p_build = sub.add_parser("build-dossier", help="Build a conservative dossier skeleton from a PR instance")
    p_build.add_argument("--instance", required=True)
    p_build.add_argument("--out")
    p_build.set_defaults(func=cmd_build_dossier)

    p_leaderboard = sub.add_parser("leaderboard", help="Create a simple CSV leaderboard from score reports")
    p_leaderboard.add_argument("--reports", nargs="+", required=True)
    p_leaderboard.add_argument("--out")
    p_leaderboard.set_defaults(func=cmd_leaderboard)

    p_summarize = sub.add_parser("summarize", help="Score and summarize a corpus of MergeDossiers")
    p_summarize.add_argument("--dossiers", required=True, help="Directory of *.json dossiers or a JSONL file")
    p_summarize.add_argument("--out", required=True, help="Output directory for corpus reports")
    p_summarize.set_defaults(func=cmd_summarize)

    p_export = sub.add_parser("export-annotation-tasks", help="Export dossiers as Label Studio import tasks")
    p_export.add_argument("--dossiers", required=True, help="Directory of *.json dossiers or a JSONL file")
    p_export.add_argument("--out", required=True, help="Output Label Studio task JSON")
    p_export.set_defaults(func=cmd_export_annotation_tasks)

    p_annotation_stats = sub.add_parser("annotation-stats", help="Summarize annotation agreement from Label Studio JSON or CSV")
    p_annotation_stats.add_argument("--annotations", required=True, help="Label Studio export JSON or spreadsheet CSV")
    p_annotation_stats.add_argument("--out", required=True, help="Output directory for agreement reports")
    p_annotation_stats.set_defaults(func=cmd_annotation_stats)

    p_export_csv = sub.add_parser("export-annotation-csv", help="Export annotation tasks as a spreadsheet-friendly CSV")
    p_export_csv.add_argument("--tasks", required=True, help="Label Studio task JSON, usually after create-reliability-sample")
    p_export_csv.add_argument("--out", required=True, help="Output CSV annotation sheet")
    p_export_csv.add_argument("--annotator-id", default="solo", help="Annotator id to prefill in the sheet")
    p_export_csv.set_defaults(func=cmd_export_annotation_csv)

    p_validate_csv = sub.add_parser("validate-annotation-csv", help="Validate a spreadsheet annotation CSV before stats")
    p_validate_csv.add_argument("--annotations", required=True, help="Completed or in-progress annotation CSV")
    p_validate_csv.add_argument("--allow-incomplete", action="store_true", help="Report missing labels as warnings")
    p_validate_csv.add_argument("--out", help="Optional JSON validation report")
    p_validate_csv.set_defaults(func=cmd_validate_annotation_csv)

    p_reliability = sub.add_parser("create-reliability-sample", help="Append delayed-repeat tasks for single-operator self-consistency checks")
    p_reliability.add_argument("--tasks", required=True, help="Label Studio task JSON")
    p_reliability.add_argument("--out", required=True, help="Output task JSON with repeat tasks appended")
    p_reliability.add_argument("--rate", type=float, default=0.2)
    p_reliability.add_argument("--min-count", type=int, default=5)
    p_reliability.add_argument("--seed", type=int, default=13)
    p_reliability.set_defaults(func=cmd_create_reliability_sample)

    p_seed = sub.add_parser("build-seed-corpus", help="Build an offline seed corpus from a manifest and fixtures")
    p_seed.add_argument("--manifest", required=True)
    p_seed.add_argument("--out", required=True)
    p_seed.add_argument("--use-fixtures", help="Directory of synthetic raw PR fixtures")
    p_seed.add_argument("--live", action="store_true", help="Fetch public GitHub PR artifacts")
    p_seed.add_argument("--github-token-env", default="GITHUB_TOKEN")
    p_seed.add_argument("--api-base", default="https://api.github.com")
    p_seed.add_argument("--sleep-seconds", type=float, default=0.0)
    p_seed.add_argument("--continue-on-error", action=argparse.BooleanOptionalAction, default=True)
    p_seed.add_argument("--limit", type=int)
    p_seed.add_argument("--force", action="store_true")
    p_seed.add_argument("--dry-run", action="store_true")
    p_seed.set_defaults(func=cmd_build_seed_corpus)

    p_lint = sub.add_parser("lint-seed-manifest", help="Lint a seed PR manifest")
    p_lint.add_argument("--manifest", required=True)
    p_lint.set_defaults(func=cmd_lint_seed_manifest)

    p_reconstruct = sub.add_parser("reconstruct-dossier", help="Reconstruct MergeDossiers from raw PR JSON")
    p_reconstruct.add_argument("--raw", required=True, help="Raw PR JSON file or directory")
    p_reconstruct.add_argument("--out", required=True, help="Output dossier JSON file or directory")
    p_reconstruct.set_defaults(func=cmd_reconstruct_dossier)

    p_audit = sub.add_parser("audit-provenance", help="Audit evidence provenance coverage for dossiers")
    p_audit.add_argument("--dossiers", required=True, help="Dossier JSON file, JSONL file, or directory of *.json dossiers")
    p_audit.add_argument("--out", required=True, help="Output directory for provenance audit reports")
    p_audit.set_defaults(func=cmd_audit_provenance)

    p_perturb = sub.add_parser("run-perturbation-suite", help="Run offline synthetic provenance perturbation checks")
    p_perturb.add_argument("--out", required=True, help="Output directory for perturbation reports")
    p_perturb.set_defaults(func=cmd_run_perturbation_suite)

    p_cards = sub.add_parser("make-dossier-cards", help="Write compact Markdown dossier cards")
    p_cards.add_argument("--dossiers", required=True, help="Dossier JSON file, JSONL file, or directory of *.json dossiers")
    p_cards.add_argument("--out", required=True, help="Output directory for cards")
    p_cards.add_argument("--format", default="md", choices=["md"])
    p_cards.set_defaults(func=cmd_make_dossier_cards)

    p_pilot = sub.add_parser("pilot-analysis", help="Write paper-facing descriptive pilot analysis tables")
    p_pilot.add_argument("--dossiers", required=True, help="Dossier JSON file, JSONL file, or directory of *.json dossiers")
    p_pilot.add_argument("--out", required=True, help="Output directory for pilot analysis reports")
    p_pilot.set_defaults(func=cmd_pilot_analysis)

    p_demands = sub.add_parser("extract-review-demands", help="Extract exploratory review-comment evidence-demand signals")
    p_demands.add_argument("--raw", required=True, help="Raw PR JSON file, JSONL file, or directory of *.json raw PR artifacts")
    p_demands.add_argument("--out", required=True, help="Output directory for exploratory demand-signal reports")
    p_demands.set_defaults(func=cmd_extract_review_demands)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
