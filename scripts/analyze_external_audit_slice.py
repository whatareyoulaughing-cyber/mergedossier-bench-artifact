"""Analyze a completed external audit slice against the primary audit codes.

This script is intentionally conservative. If the external audit sheet still
contains blank audit-code cells, it writes an incomplete-status report and does
not claim agreement. Once the sheet is complete, it compares the external
operator's codes against the primary single-operator audit for the selected
instances.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mergedossier_bench.label_studio import EVIDENCE_CATEGORIES, LABEL_VALUES


ROOT = Path(__file__).resolve().parents[1]
LABEL_SET = set(LABEL_VALUES)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _label_column(category: str) -> str:
    return f"{category}_label"


def _primary_rows_by_instance(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    primary: dict[str, dict[str, str]] = {}
    for row in rows:
        if str(row.get("is_reliability_repeat", "")).strip().lower() == "true":
            continue
        instance_id = str(row.get("instance_id", "")).strip()
        if instance_id and instance_id not in primary:
            primary[instance_id] = row
    return primary


def _selected_ids_from_manifest(path: Path | None, external_rows: dict[str, dict[str, str]]) -> list[str]:
    if path is None:
        return [instance_id for instance_id in external_rows if instance_id]
    manifest = json.loads(path.read_text(encoding="utf-8"))
    ids = manifest.get("selected_instance_ids")
    if not isinstance(ids, list):
        raise ValueError(f"{path} does not contain selected_instance_ids")
    return [str(item) for item in ids]


def _availability_bucket(label: str) -> str:
    if label in {"present", "partially_present"}:
        return "available"
    if label in {"missing", "not_applicable"}:
        return "unavailable"
    return "invalid"


def _cohen_kappa(pairs: list[tuple[str, str]], labels: list[str]) -> float | None:
    if not pairs:
        return None
    observed = sum(1 for left, right in pairs if left == right) / len(pairs)
    left_counts = Counter(left for left, _ in pairs)
    right_counts = Counter(right for _, right in pairs)
    expected = sum((left_counts[label] / len(pairs)) * (right_counts[label] / len(pairs)) for label in labels)
    if expected == 1.0:
        return 1.0 if observed == 1.0 else 0.0
    return round((observed - expected) / (1 - expected), 4)


def _pct(value: float | None) -> str:
    if value is None:
        return "--"
    return f"{100 * value:.1f}\\%"


def _latex_escape(value: Any) -> str:
    text = str(value)
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("_", r"\_")
        .replace("#", r"\#")
    )


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def _write_agreement_tex(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{External audit-slice agreement by evidence family. Exact agreement uses four audit codes; availability agreement collapses present and partially present into available.}",
        r"\label{tab:external-audit-slice}",
        r"\footnotesize",
        r"\begin{tabular}{@{}lrrr@{}}",
        r"\toprule",
        r"Family & $n$ & Exact & Availability \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            f"{_latex_escape(row['family'])} & {row['pairs']} & "
            f"{_pct(row['exact_agreement'])} & {_pct(row['availability_agreement'])} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def analyze_external_audit(
    primary_csv: Path,
    external_csv: Path,
    out_dir: Path,
    manifest_path: Path | None = None,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    primary_rows = _primary_rows_by_instance(_read_csv(primary_csv))
    external_rows = _primary_rows_by_instance(_read_csv(external_csv))
    selected_ids = _selected_ids_from_manifest(manifest_path, external_rows)

    missing_instances = [instance_id for instance_id in selected_ids if instance_id not in external_rows]
    missing_primary = [instance_id for instance_id in selected_ids if instance_id not in primary_rows]
    blank_cells: list[dict[str, str]] = []
    invalid_cells: list[dict[str, str]] = []
    for instance_id in selected_ids:
        row = external_rows.get(instance_id)
        if row is None:
            continue
        for category in EVIDENCE_CATEGORIES:
            label = str(row.get(_label_column(category), "")).strip()
            if not label:
                blank_cells.append({"instance_id": instance_id, "category": category})
            elif label not in LABEL_SET:
                invalid_cells.append({"instance_id": instance_id, "category": category, "label": label})

    is_complete = not missing_instances and not missing_primary and not blank_cells and not invalid_cells
    agreement_rows: list[dict[str, Any]] = []
    disagreements: list[dict[str, Any]] = []

    if is_complete:
        for category in EVIDENCE_CATEGORIES:
            exact_pairs: list[tuple[str, str]] = []
            availability_pairs: list[tuple[str, str]] = []
            category_disagreements = 0
            availability_disagreements = 0
            for instance_id in selected_ids:
                primary_label = str(primary_rows[instance_id].get(_label_column(category), "")).strip()
                external_label = str(external_rows[instance_id].get(_label_column(category), "")).strip()
                exact_pairs.append((primary_label, external_label))
                availability_pair = (_availability_bucket(primary_label), _availability_bucket(external_label))
                availability_pairs.append(availability_pair)
                if primary_label != external_label:
                    category_disagreements += 1
                    disagreements.append(
                        {
                            "instance_id": instance_id,
                            "category": category,
                            "primary_label": primary_label,
                            "external_label": external_label,
                            "primary_comment": primary_rows[instance_id].get(f"{category}_comment", ""),
                            "external_comment": external_rows[instance_id].get(f"{category}_comment", ""),
                        }
                    )
                if availability_pair[0] != availability_pair[1]:
                    availability_disagreements += 1

            total = len(exact_pairs)
            exact_agreement = sum(1 for left, right in exact_pairs if left == right) / total if total else None
            availability_agreement = (
                sum(1 for left, right in availability_pairs if left == right) / total if total else None
            )
            agreement_rows.append(
                {
                    "category": category,
                    "family": category.replace("_", " ").title(),
                    "pairs": total,
                    "exact_agreement": round(exact_agreement, 4) if exact_agreement is not None else None,
                    "availability_agreement": round(availability_agreement, 4)
                    if availability_agreement is not None
                    else None,
                    "exact_kappa": _cohen_kappa(exact_pairs, list(LABEL_VALUES)),
                    "availability_kappa": _cohen_kappa(availability_pairs, ["available", "unavailable"]),
                    "exact_disagreements": category_disagreements,
                    "availability_disagreements": availability_disagreements,
                }
            )

        _write_csv(
            out_dir / "external_audit_agreement_by_category.csv",
            agreement_rows,
            [
                "category",
                "family",
                "pairs",
                "exact_agreement",
                "availability_agreement",
                "exact_kappa",
                "availability_kappa",
                "exact_disagreements",
                "availability_disagreements",
            ],
        )
        _write_agreement_tex(out_dir / "paper_table_external_audit_agreement.tex", agreement_rows)
        _write_csv(
            out_dir / "external_audit_disagreements.csv",
            disagreements,
            [
                "instance_id",
                "category",
                "primary_label",
                "external_label",
                "primary_comment",
                "external_comment",
            ],
        )
        with (out_dir / "external_audit_disagreements.jsonl").open("w", encoding="utf-8") as handle:
            for row in disagreements:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "complete" if is_complete else "incomplete",
        "primary_csv": str(primary_csv),
        "external_csv": str(external_csv),
        "manifest": str(manifest_path) if manifest_path else None,
        "selected_tasks": len(selected_ids),
        "external_rows": len(external_rows),
        "missing_external_instances": missing_instances,
        "missing_primary_instances": missing_primary,
        "blank_label_cells": blank_cells,
        "invalid_label_cells": invalid_cells,
        "agreement_by_category": agreement_rows,
        "claim_boundary": (
            "External audit-slice statistics can support a secondary reliability check only after "
            "the slice is independently completed. They do not establish patch correctness, mergeability, "
            "reviewer utility, AI-vs-human effects, or all-GitHub rates."
        ),
    }
    (out_dir / "external_audit_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (out_dir / "external_audit_summary.md").write_text(_summary_markdown(summary), encoding="utf-8")
    return summary


def _summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# External Audit Slice Analysis",
        "",
        f"- Status: `{summary['status']}`",
        f"- Selected tasks: {summary['selected_tasks']}",
        f"- External rows found: {summary['external_rows']}",
        "",
    ]
    if summary["status"] != "complete":
        lines.extend(
            [
                "The external audit slice is not complete enough to report agreement.",
                "",
                f"- Missing external instances: {len(summary['missing_external_instances'])}",
                f"- Missing primary instances: {len(summary['missing_primary_instances'])}",
                f"- Blank label cells: {len(summary['blank_label_cells'])}",
                f"- Invalid label cells: {len(summary['invalid_label_cells'])}",
                "",
                "Complete every audit-code cell with one of `present`, `partially_present`, "
                "`missing`, or `not_applicable`, then rerun this script.",
                "",
            ]
        )
    else:
        lines.extend(["## Agreement By Category", "", "| Category | Pairs | Exact | Availability | Exact kappa | Availability kappa |", "|---|---:|---:|---:|---:|---:|"])
        for row in summary["agreement_by_category"]:
            lines.append(
                f"| {row['category']} | {row['pairs']} | {row['exact_agreement']} | "
                f"{row['availability_agreement']} | {row['exact_kappa']} | {row['availability_kappa']} |"
            )
        lines.extend(["", "Interpret these values as an external audit slice, not as full-corpus inter-rater reliability.", ""])
    lines.extend(["## Claim Boundary", "", summary["claim_boundary"], ""])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze completed external audit slice")
    parser.add_argument(
        "--primary",
        default="outputs/population_ai_pr_500_20260616/reports/annotation_sheet_completed.csv",
        help="Primary completed annotation CSV.",
    )
    parser.add_argument(
        "--external",
        default="outputs/external_audit_slice_20260617/external_audit_sheet.csv",
        help="Completed external audit CSV.",
    )
    parser.add_argument(
        "--manifest",
        default="outputs/external_audit_slice_20260617/external_audit_manifest.json",
        help="External audit manifest with selected_instance_ids.",
    )
    parser.add_argument("--out", default="outputs/external_audit_analysis_20260617")
    args = parser.parse_args(argv)
    summary = analyze_external_audit(
        ROOT / args.primary,
        ROOT / args.external,
        ROOT / args.out,
        ROOT / args.manifest if args.manifest else None,
    )
    print(f"External audit analysis written: {args.out} ({summary['status']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
