"""Sample a stratified population PR manifest from a normalized frame."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from mergedossier_bench.population import FRAME_COLUMNS, read_csv_rows, sample_population_prs, write_csv_rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sample 500 public AI/AI-assisted PRs from a population frame")
    parser.add_argument("--frame", required=True, help="Normalized population frame CSV")
    parser.add_argument("--n", type=int, default=500)
    parser.add_argument("--seed", type=int, default=20260616)
    parser.add_argument("--min-per-agent", type=int, default=50)
    parser.add_argument("--out", required=True, help="Sample manifest CSV")
    parser.add_argument("--report-out", help="Output directory for sampling report")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    rows = read_csv_rows(args.frame)
    sample, report = sample_population_prs(rows, n=args.n, seed=args.seed, min_per_agent=args.min_per_agent)
    write_csv_rows(args.out, sample, FRAME_COLUMNS)
    report_dir = Path(args.report_out) if args.report_out else ROOT / "outputs" / f"population_sampling_report_{datetime.now().strftime('%Y%m%d')}"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "sampling_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Population sample written: {report['sample_size']} of {report['eligible_size']} eligible rows -> {args.out}")
    if report["shortfall"]:
        print(f"WARNING: requested {args.n} rows but only sampled {report['sample_size']} eligible rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
