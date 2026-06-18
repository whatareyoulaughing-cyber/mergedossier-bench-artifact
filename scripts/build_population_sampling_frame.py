"""Build a normalized population sampling frame from an AIDev-like CSV export."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from mergedossier_bench.population import FRAME_COLUMNS, build_population_frame, read_csv_rows, write_csv_rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a normalized MergeDossier population sampling frame")
    parser.add_argument("--input", required=True, help="AIDev-like CSV export")
    parser.add_argument("--out", required=True, help="Normalized frame CSV")
    parser.add_argument("--report-out", help="Optional JSON summary path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    frame, summary = build_population_frame(read_csv_rows(args.input))
    write_csv_rows(args.out, frame, FRAME_COLUMNS)
    report = Path(args.report_out) if args.report_out else Path(args.out).with_suffix(".summary.json")
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Population frame written: {summary['eligible_size']} eligible of {summary['frame_size']} rows -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
