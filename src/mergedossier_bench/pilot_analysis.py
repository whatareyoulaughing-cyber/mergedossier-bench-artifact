"""Paper-facing pilot analysis tables for MergeDossier corpora."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .provenance import PROVENANCE_CATEGORIES, collect_provenance, iter_dossier_inputs, markdown_table, summarize_provenance
from .schema import EVIDENCE_TYPES
from .scoring import score_dossier
from .validators import validate_data


PILOT_WARNING = (
    "These outputs describe review-evidence availability for the analyzed corpus only. They are not population estimates "
    "unless the corpus design, sampling frame, and matching protocol support that claim."
)

CLAIMS_NONCLAIMS: tuple[tuple[str, str], ...] = (
    ("Evidence availability in AIDev-pop", "All-GitHub rates"),
    ("Provenance-backed visibility", "Patch correctness"),
    ("Category-level missing evidence", "Mergeability"),
    ("Single-operator self-consistency", "Inter-rater reliability"),
    ("Dependency candidate audit", "Full-sample dependency prevalence"),
    ("Instrument auditability", "Reviewer utility"),
    ("Descriptive population-frame estimates", "AI-vs-human causal effects"),
)


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _metadata_value(dossier: dict[str, Any], key: str) -> str:
    metadata = dossier.get("metadata", {}) if isinstance(dossier.get("metadata"), dict) else {}
    manifest = metadata.get("manifest_metadata", {}) if isinstance(metadata.get("manifest_metadata"), dict) else {}
    value = dossier.get(key, metadata.get(key, manifest.get(key, "")))
    return "" if value is None else str(value)


def _category_has_evidence(dossier: dict[str, Any], category: str) -> bool:
    evidence = dossier.get("evidence", {}) if isinstance(dossier.get("evidence"), dict) else {}
    item = evidence.get(category, {})
    return isinstance(item, dict) and bool(item.get("present", False))


def _category_quality(dossier: dict[str, Any], category: str) -> int:
    evidence = dossier.get("evidence", {}) if isinstance(dossier.get("evidence"), dict) else {}
    item = evidence.get(category, {})
    if not isinstance(item, dict) or not item.get("present"):
        return 0
    try:
        return int(item.get("quality", 0))
    except (TypeError, ValueError):
        return 0


def _status_for_category(dossier: dict[str, Any], category: str) -> str:
    records = collect_provenance(dossier).get(category, [])
    if not records:
        return "missing"
    priority = {"observed": 0, "inferred": 1, "missing": 2, "not_applicable": 3}
    statuses = [str(record.get("status", "missing")) for record in records]
    return sorted(statuses, key=lambda status: priority.get(status, 9))[0]


def _group_rows(dossiers: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for dossier in dossiers:
        value = _metadata_value(dossier, field) or "unknown"
        groups[value].append(dossier)
    rows: list[dict[str, Any]] = []
    for value, group in sorted(groups.items()):
        scores = [score_dossier(dossier)["evidence_sufficiency_score"] for dossier in group]
        rows.append(
            {
                field: value,
                "dossiers": len(group),
                "mean_score": round(sum(scores) / len(scores), 2) if scores else 0,
                "interpretation": "descriptive only; not a causal or population comparison",
            }
        )
    return rows


def _availability_sensitivity_rows(dossiers: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    total = len(dossiers)
    for category in EVIDENCE_TYPES:
        qualities = [_category_quality(dossier, category) for dossier in dossiers]
        main = sum(1 for quality in qualities if quality >= 1)
        strict = sum(1 for quality in qualities if quality >= 2)
        conservative = strict
        rows.append(
            {
                "category": category,
                "n": total,
                "availability_main": round(main / total, 4) if total else 0.0,
                "availability_strict": round(strict / total, 4) if total else 0.0,
                "availability_conservative": round(conservative / total, 4) if total else 0.0,
                "missing_main": round((total - main) / total, 4) if total else 0.0,
                "missing_strict": round((total - strict) / total, 4) if total else 0.0,
                "missing_conservative": round((total - conservative) / total, 4) if total else 0.0,
                "positive_main_count": main,
                "positive_strict_count": strict,
                "positive_conservative_count": conservative,
            }
        )

    main_gap = {row["category"] for row in rows if row["availability_main"] < 0.5}
    strict_gap = {row["category"] for row in rows if row["availability_strict"] < 0.5}
    pattern_remains = bool(main_gap) and main_gap.issubset(strict_gap)
    summary = {
        "construct": "Review-Evidence Availability",
        "availability_main_definition": "quality >= 1; present and partially present evidence are positive",
        "availability_strict_definition": "quality >= 2; only specific grounded evidence is positive",
        "availability_conservative_definition": "quality >= 2; partial evidence is counted as missing",
        "core_gap_categories_main": sorted(main_gap),
        "core_gap_categories_strict": sorted(strict_gap),
        "core_evidence_gap_pattern_remains_under_stricter_coding": pattern_remains,
        "interpretation": (
            "The core evidence-gap pattern remains under stricter coding."
            if pattern_remains
            else "The core evidence-gap pattern changes under stricter coding; inspect category-level rows."
        ),
    }
    return rows, summary


def _provenance_table_rows(dossiers: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    status_rows: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []
    for category in PROVENANCE_CATEGORIES:
        status_counts: Counter[str] = Counter()
        source_counts: Counter[str] = Counter()
        for dossier in dossiers:
            records = collect_provenance(dossier).get(category, [])
            if not records:
                status_counts["missing"] += 1
                continue
            for record in records:
                status = str(record.get("status", "missing"))
                status_counts[status if status in {"observed", "inferred", "missing", "not_applicable"} else "missing"] += 1
                source_counts[str(record.get("source_type", "unknown") or "unknown")] += 1
        status_rows.append(
            {
                "category": category,
                "observed": status_counts.get("observed", 0),
                "inferred": status_counts.get("inferred", 0),
                "missing": status_counts.get("missing", 0),
                "not_applicable": status_counts.get("not_applicable", 0),
            }
        )
        for source_type, count in sorted(source_counts.items()):
            source_rows.append({"category": category, "source_type": source_type, "count": count})
    return status_rows, source_rows


def _write_claims_nonclaims_tables(output_path: Path) -> None:
    md_rows = [[claim, nonclaim] for claim, nonclaim in CLAIMS_NONCLAIMS]
    (output_path / "paper_table_claims_nonclaims.md").write_text(
        "\n".join(
            [
                "# Claims and Non-Claims",
                "",
                markdown_table(["Claim", "Non-claim"], md_rows),
                "",
            ]
        ),
        encoding="utf-8",
    )
    tex_lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Claims and non-claims for Review-Evidence Availability measurement.}",
        r"\label{tab:claims-nonclaims}",
        r"\footnotesize",
        r"\begin{tabular}{@{}ll@{}}",
        r"\toprule",
        r"Claim & Non-claim \\",
        r"\midrule",
    ]
    for claim, nonclaim in CLAIMS_NONCLAIMS:
        tex_lines.append(f"{claim} & {nonclaim} \\\\")
    tex_lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    (output_path / "paper_table_claims_nonclaims.tex").write_text("\n".join(tex_lines), encoding="utf-8")


def run_pilot_analysis(dossiers: str | Path, out_dir: str | Path) -> dict[str, Any]:
    """Write paper-facing descriptive pilot tables."""
    output_path = Path(out_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    valid: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []
    for source, dossier, load_error in iter_dossier_inputs(dossiers):
        if load_error is not None or dossier is None:
            invalid.append({"source": source, "error": load_error or "missing dossier"})
            continue
        errors = validate_data(dossier, "dossier")
        if errors:
            invalid.append({"source": source, "error": errors[0], "validation_errors": errors})
            continue
        valid.append(dossier)

    coverage_rows: list[dict[str, Any]] = []
    missing_rows: list[dict[str, Any]] = []
    for category in EVIDENCE_TYPES:
        present = sum(1 for dossier in valid if _category_has_evidence(dossier, category))
        missing = len(valid) - present
        coverage_rows.append(
            {
                "category": category,
                "present_count": present,
                "missing_count": missing,
                "coverage_rate": round(present / len(valid), 4) if valid else 0.0,
            }
        )
        missing_rows.append({"category": category, "missing_count": missing})

    status_rows: list[dict[str, Any]] = []
    for category in PROVENANCE_CATEGORIES:
        counts = Counter(_status_for_category(dossier, category) for dossier in valid)
        status_rows.append(
            {
                "category": category,
                "observed": counts.get("observed", 0),
                "inferred": counts.get("inferred", 0),
                "missing": counts.get("missing", 0),
                "not_applicable": counts.get("not_applicable", 0),
            }
        )
    provenance_by_category_rows, source_type_by_category_rows = _provenance_table_rows(valid)
    sensitivity_rows, sensitivity_summary = _availability_sensitivity_rows(valid)

    source_counts: Counter[str] = Counter()
    for dossier in valid:
        for records in collect_provenance(dossier).values():
            source_counts.update(str(record.get("source_type", "unknown")) for record in records)
    source_rows = [{"source_type": key, "count": value} for key, value in sorted(source_counts.items())]

    author_rows = _group_rows(valid, "author_type")
    outcome_rows = _group_rows(valid, "outcome")
    provenance_summary = summarize_provenance(valid)
    scores = [score_dossier(dossier)["evidence_sufficiency_score"] for dossier in valid]
    summary = {
        "total_dossiers": len(valid) + len(invalid),
        "valid_dossiers": len(valid),
        "invalid_dossiers": len(invalid),
        "mean_score": round(sum(scores) / len(scores), 2) if scores else None,
        "warning": PILOT_WARNING,
        "provenance_summary": provenance_summary,
        "sensitivity_summary": sensitivity_summary,
    }

    (output_path / "pilot_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _write_csv(output_path / "paper_table_evidence_coverage.csv", coverage_rows, ["category", "present_count", "missing_count", "coverage_rate"])
    _write_csv(output_path / "paper_table_missing_evidence.csv", missing_rows, ["category", "missing_count"])
    _write_csv(output_path / "paper_table_provenance_status.csv", status_rows, ["category", "observed", "inferred", "missing", "not_applicable"])
    _write_csv(output_path / "paper_table_source_types.csv", source_rows, ["source_type", "count"])
    _write_csv(
        output_path / "paper_table_sensitivity_by_category.csv",
        sensitivity_rows,
        [
            "category",
            "n",
            "availability_main",
            "availability_strict",
            "availability_conservative",
            "missing_main",
            "missing_strict",
            "missing_conservative",
            "positive_main_count",
            "positive_strict_count",
            "positive_conservative_count",
        ],
    )
    _write_csv(output_path / "paper_table_provenance_by_category.csv", provenance_by_category_rows, ["category", "observed", "inferred", "missing", "not_applicable"])
    _write_csv(output_path / "paper_table_source_type_by_category.csv", source_type_by_category_rows, ["category", "source_type", "count"])
    _write_csv(output_path / "paper_table_by_author_type.csv", author_rows, ["author_type", "dossiers", "mean_score", "interpretation"])
    _write_csv(output_path / "paper_table_by_outcome.csv", outcome_rows, ["outcome", "dossiers", "mean_score", "interpretation"])
    (output_path / "sensitivity_summary.json").write_text(json.dumps(sensitivity_summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    sensitivity_md_rows = [
        [
            row["category"],
            f"{row['availability_main']:.2%}",
            f"{row['availability_strict']:.2%}",
            f"{row['availability_conservative']:.2%}",
            f"{row['missing_main']:.2%}",
        ]
        for row in sensitivity_rows
    ]
    (output_path / "sensitivity_summary.md").write_text(
        "\n".join(
            [
                "# Review-Evidence Availability Sensitivity",
                "",
                sensitivity_summary["interpretation"],
                "",
                markdown_table(
                    ["category", "availability_main", "availability_strict", "availability_conservative", "missing_main"],
                    sensitivity_md_rows,
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )
    _write_claims_nonclaims_tables(output_path)
    coverage_md_rows = [[row["category"], row["present_count"], row["missing_count"], f"{row['coverage_rate']:.2%}"] for row in coverage_rows]
    status_md_rows = [[row["category"], row["observed"], row["inferred"], row["missing"], row["not_applicable"]] for row in status_rows]
    (output_path / "pilot_summary.md").write_text(
        "\n".join(
            [
                "# Pilot Analysis",
                "",
                PILOT_WARNING,
                "",
                f"- Valid dossiers: {summary['valid_dossiers']}",
                f"- Invalid dossiers: {summary['invalid_dossiers']}",
                f"- Mean legacy Evidence Sufficiency Score: {summary['mean_score']}",
                f"- Main construct: Review-Evidence Availability",
                f"- Sensitivity: {sensitivity_summary['interpretation']}",
                "",
                "## Review-Evidence Availability",
                "",
                markdown_table(["category", "present", "missing", "coverage"], coverage_md_rows),
                "",
                "## Provenance Status",
                "",
                markdown_table(["category", "observed", "inferred", "missing", "not_applicable"], status_md_rows),
                "",
            ]
        ),
        encoding="utf-8",
    )
    return summary
