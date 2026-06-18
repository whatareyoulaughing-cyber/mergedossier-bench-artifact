"""Inspect an AIDev parquet/CSV source without printing large table contents."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


DEFAULT_DATASET = "hao-li/AIDev"
DEFAULT_TABLE = "pull_request.parquet"


def _source_from_args(args: argparse.Namespace) -> str:
    if args.input:
        return args.input
    return f"hf://datasets/{args.dataset}/{args.table}"


def _read_csv_summary(path: str | Path, sample_size: int) -> dict[str, Any]:
    rows = 0
    sample: list[dict[str, str]] = []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        columns = list(reader.fieldnames or [])
        for row in reader:
            rows += 1
            if len(sample) < sample_size:
                sample.append({key: row.get(key, "") for key in columns[:30]})
    return {
        "source_format": "csv",
        "row_count": rows,
        "column_count": len(columns),
        "columns": columns,
        "sample_rows": sample,
    }


def _read_parquet_summary(source: str, sample_size: int) -> dict[str, Any]:
    try:
        import pandas as pd
    except ModuleNotFoundError as exc:
        raise SystemExit("pandas and pyarrow are required. Install with: pip install -e \".[analysis]\"") from exc

    df = pd.read_parquet(source)
    sample = df.head(sample_size).fillna("").astype(str).to_dict(orient="records")
    return {
        "source_format": "parquet",
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "columns": [str(column) for column in df.columns],
        "dtypes": {str(column): str(dtype) for column, dtype in df.dtypes.items()},
        "sample_rows": sample,
    }


def inspect_source(source: str, sample_size: int) -> dict[str, Any]:
    suffix = Path(source).suffix.lower()
    if suffix == ".csv":
        return _read_csv_summary(source, sample_size)
    return _read_parquet_summary(source, sample_size)


def write_report(summary: dict[str, Any], source: str, out_dir: str | Path) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    payload = {"source": source, **summary}
    (out / "schema_summary.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    column_lines = "\n".join(f"- `{column}`" for column in summary["columns"])
    sample_keys = ", ".join(summary["sample_rows"][0].keys()) if summary.get("sample_rows") else ""
    (out / "schema_summary.md").write_text(
        "\n".join(
            [
                "# AIDev Schema Inspection",
                "",
                f"- Source: `{source}`",
                f"- Format: {summary['source_format']}",
                f"- Rows: {summary['row_count']}",
                f"- Columns: {summary['column_count']}",
                f"- Sample keys shown: {sample_keys}",
                "",
                "## Columns",
                "",
                column_lines,
                "",
            ]
        ),
        encoding="utf-8",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect AIDev parquet/CSV schema")
    parser.add_argument("--dataset", default=DEFAULT_DATASET, help="Hugging Face dataset id")
    parser.add_argument("--table", default=DEFAULT_TABLE, help="Dataset table/parquet file")
    parser.add_argument("--input", help="Optional local or hf:// parquet/CSV source")
    parser.add_argument("--sample-size", type=int, default=5)
    parser.add_argument("--out", required=True, help="Output directory")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source = _source_from_args(args)
    summary = inspect_source(source, args.sample_size)
    write_report(summary, source, args.out)
    print(f"AIDev schema inspected: {summary['row_count']} rows, {summary['column_count']} columns -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
