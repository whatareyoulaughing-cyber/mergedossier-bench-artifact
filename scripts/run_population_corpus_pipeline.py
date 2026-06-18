"""Run the population corpus build, audit, cards, and annotation export pipeline."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from mergedossier_bench.population import run_population_corpus_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run MergeDossier population corpus pipeline")
    parser.add_argument("--sample", required=True, help="Population sample manifest CSV")
    parser.add_argument("--out", required=True, help="Output directory for raw artifacts, dossiers, and reports")
    parser.add_argument("--live", action="store_true", help="Fetch GitHub artifacts instead of metadata-only reconstruction")
    parser.add_argument("--github-token-env", default="GITHUB_TOKEN")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--annotation-repeats", type=int, default=50, help="Minimum delayed-repeat tasks to append")
    parser.add_argument("--seed", type=int, default=20260616, help="Seed for delayed-repeat selection")
    parser.add_argument(
        "--no-workbook",
        action="store_true",
        help="Do not attempt to create reports/annotation_sheet.xlsx from the CSV template",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    token = os.environ.get(args.github_token_env) if args.live else None
    summary = run_population_corpus_pipeline(
        args.sample,
        args.out,
        live=args.live,
        github_token=token,
        force=args.force,
        annotation_repeat_count=args.annotation_repeats,
        seed=args.seed,
    )
    workbook_note = ""
    if not args.no_workbook:
        try:
            from export_annotation_workbook import build_workbook

            csv_path = Path(summary["annotation_sheet_csv"])
            workbook_path = csv_path.with_suffix(".xlsx")
            build_workbook(csv_path, workbook_path)
            summary["annotation_sheet_workbook"] = str(workbook_path)
            workbook_note = f", workbook {workbook_path}"
        except SystemExit as exc:
            workbook_note = f", workbook skipped ({exc})"
    print(
        "Population pipeline written: "
        f"{summary['build_summary'].get('reconstructed_dossiers', 0)} dossiers, "
        f"{summary['annotation_tasks']} annotation tasks, "
        f"{summary['repeat_tasks']} delayed repeats, "
        f"CSV {summary['annotation_sheet_csv']}{workbook_note} -> {args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
