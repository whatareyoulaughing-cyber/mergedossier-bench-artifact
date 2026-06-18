"""Build population-frame evidence estimates from completed annotations."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from mergedossier_bench.population import write_population_results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build population-frame evidence estimate tables")
    parser.add_argument("--annotations", required=True, help="Completed annotation CSV or Label Studio JSON")
    parser.add_argument("--sample-manifest", required=True, help="Population sample manifest with sampling weights")
    parser.add_argument("--out", required=True, help="Output directory")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = write_population_results(args.annotations, args.sample_manifest, args.out)
    print(f"Population results written: {summary['annotation_records']} primary annotation records -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
