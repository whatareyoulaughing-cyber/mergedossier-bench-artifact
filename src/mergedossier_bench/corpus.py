"""Batch summarization for MergeDossier corpora."""

from __future__ import annotations

import csv
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from .schema import EVIDENCE_TYPES
from .scoring import score_dossier
from .validators import load_json, validate_data


def _json_default(value: Any) -> str:
    return str(value)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, default=_json_default) + "\n")


def _iter_dossier_inputs(dossiers_path: Path) -> Iterable[tuple[str, dict[str, Any] | None, str | None]]:
    """Yield dossier records from a JSONL file or a directory of JSON files.

    Each yielded tuple is ``(source, data, load_error)``. ``source`` is stable
    enough for benchmark debugging: a file path for directory inputs and
    ``path:line`` for JSONL inputs.
    """
    if dossiers_path.is_dir():
        for path in sorted(dossiers_path.glob("*.json")):
            try:
                data = load_json(path)
            except Exception as exc:
                yield str(path), None, str(exc)
                continue
            yield str(path), data, None
        return

    with dossiers_path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            if not line.strip():
                continue
            source = f"{dossiers_path}:{line_number}"
            try:
                data = json.loads(line)
            except json.JSONDecodeError as exc:
                yield source, None, str(exc)
                continue
            yield source, data, None


def _empty_summary(total_dossiers: int, invalid_dossiers: int) -> dict[str, Any]:
    return {
        "total_dossiers": total_dossiers,
        "valid_dossiers": 0,
        "invalid_dossiers": invalid_dossiers,
        "mean_evidence_sufficiency_score": None,
        "median_evidence_sufficiency_score": None,
        "min_score": None,
        "max_score": None,
        "readiness_band_counts": {},
        "missing_evidence_counts": {},
        "evidence_category_coverage": {},
        "top_10_most_common_missing_evidence": [],
    }


def _build_summary(scores: list[dict[str, Any]], total_dossiers: int, invalid_dossiers: int) -> dict[str, Any]:
    if not scores:
        return _empty_summary(total_dossiers, invalid_dossiers)

    score_values = [float(row["evidence_sufficiency_score"]) for row in scores]
    readiness_counts = Counter(str(row["readiness_band"]) for row in scores)
    missing_counts: Counter[str] = Counter()
    for row in scores:
        missing_counts.update(str(item) for item in row.get("missing_evidence", []))

    coverage: dict[str, dict[str, float | int]] = {}
    for evidence_type in EVIDENCE_TYPES:
        category_values = [float(row["category_scores"].get(evidence_type, 0.0)) for row in scores]
        present_count = sum(1 for value in category_values if value > 0)
        coverage[evidence_type] = {
            "present_count": present_count,
            "coverage_rate": round(present_count / len(scores), 4),
            "mean_category_score": round(statistics.mean(category_values), 2),
        }

    return {
        "total_dossiers": total_dossiers,
        "valid_dossiers": len(scores),
        "invalid_dossiers": invalid_dossiers,
        "mean_evidence_sufficiency_score": round(statistics.mean(score_values), 2),
        "median_evidence_sufficiency_score": round(statistics.median(score_values), 2),
        "min_score": round(min(score_values), 2),
        "max_score": round(max(score_values), 2),
        "readiness_band_counts": dict(sorted(readiness_counts.items())),
        "missing_evidence_counts": dict(sorted(missing_counts.items())),
        "evidence_category_coverage": coverage,
        "top_10_most_common_missing_evidence": [
            {"evidence_type": key, "count": count} for key, count in missing_counts.most_common(10)
        ],
    }


def _markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    table = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        table.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(table)


def _build_summary_markdown(summary: dict[str, Any], scores: list[dict[str, Any]]) -> str:
    readiness_rows = [[key, value] for key, value in summary["readiness_band_counts"].items()]
    missing_rows = [[key, value] for key, value in summary["missing_evidence_counts"].items()]
    coverage_rows = [
        [
            key,
            value["present_count"],
            f"{value['coverage_rate']:.2%}",
            value["mean_category_score"],
        ]
        for key, value in summary["evidence_category_coverage"].items()
    ]

    sorted_scores = sorted(scores, key=lambda row: float(row["evidence_sufficiency_score"]))
    low_rows = [
        [row["dossier_id"], row["evidence_sufficiency_score"], row["readiness_band"], ";".join(row["missing_evidence"])]
        for row in sorted_scores[:5]
    ]
    high_rows = [
        [row["dossier_id"], row["evidence_sufficiency_score"], row["readiness_band"], ";".join(row["missing_evidence"])]
        for row in reversed(sorted_scores[-5:])
    ]

    sections = [
        "# MergeDossier-Bench Corpus Summary",
        "",
        "## Corpus overview",
        "",
        f"- Total dossiers: {summary['total_dossiers']}",
        f"- Valid dossiers: {summary['valid_dossiers']}",
        f"- Invalid dossiers: {summary['invalid_dossiers']}",
        f"- Mean legacy Evidence Sufficiency Score: {summary['mean_evidence_sufficiency_score']}",
        f"- Median legacy Evidence Sufficiency Score: {summary['median_evidence_sufficiency_score']}",
        f"- Score range: {summary['min_score']} to {summary['max_score']}",
        "",
        "## Artifact triage band table",
        "",
        _markdown_table(["legacy_triage_band", "count"], readiness_rows) if readiness_rows else "_No valid dossiers._",
        "",
        "## Missing evidence table",
        "",
        _markdown_table(["evidence_type", "count"], missing_rows) if missing_rows else "_No missing evidence among valid dossiers._",
        "",
        "## Evidence category coverage table",
        "",
        _markdown_table(["evidence_type", "present_count", "coverage_rate", "mean_category_score"], coverage_rows)
        if coverage_rows
        else "_No valid dossiers._",
        "",
        "## 5 lowest-scoring dossiers",
        "",
        _markdown_table(["dossier_id", "legacy_score", "legacy_triage_band", "missing_evidence"], low_rows)
        if low_rows
        else "_No valid dossiers._",
        "",
        "## 5 highest-scoring dossiers",
        "",
        _markdown_table(["dossier_id", "legacy_score", "legacy_triage_band", "missing_evidence"], high_rows)
        if high_rows
        else "_No valid dossiers._",
        "",
    ]
    return "\n".join(sections)


def _write_leaderboard(path: Path, scores: list[dict[str, Any]]) -> None:
    fieldnames = [
        "dossier_id",
        "source_agent",
        "repository",
        "evidence_sufficiency_score",
        "readiness_band",
        "missing_evidence",
        "source",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in sorted(scores, key=lambda item: float(item["evidence_sufficiency_score"]), reverse=True):
            writer.writerow(
                {
                    "dossier_id": row.get("dossier_id", "UNKNOWN"),
                    "source_agent": row.get("source_agent", ""),
                    "repository": row.get("repository", ""),
                    "evidence_sufficiency_score": row.get("evidence_sufficiency_score", 0),
                    "readiness_band": row.get("readiness_band", "unknown"),
                    "missing_evidence": ";".join(row.get("missing_evidence", [])),
                    "source": row.get("source", ""),
                }
            )


def summarize_corpus(dossiers: str | Path, out_dir: str | Path) -> dict[str, Any]:
    """Validate, score, and summarize a MergeDossier corpus."""
    dossiers_path = Path(dossiers)
    output_path = Path(out_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    scores: list[dict[str, Any]] = []
    invalid_rows: list[dict[str, Any]] = []
    total = 0

    for source, dossier, load_error in _iter_dossier_inputs(dossiers_path):
        total += 1
        if load_error is not None:
            invalid_rows.append({"source": source, "validation_error": load_error, "validation_errors": [load_error]})
            continue
        assert dossier is not None
        errors = validate_data(dossier, "dossier")
        if errors:
            invalid_rows.append({"source": source, "validation_error": errors[0], "validation_errors": errors})
            continue
        report = score_dossier(dossier)
        report["source"] = source
        report["repository"] = dossier.get("repository", "")
        report["source_agent"] = dossier.get("source_agent", "")
        scores.append(report)

    summary = _build_summary(scores, total, len(invalid_rows))
    _write_jsonl(output_path / "scores.jsonl", scores)
    _write_jsonl(output_path / "invalid_dossiers.jsonl", invalid_rows)
    _write_json(output_path / "summary.json", summary)
    (output_path / "summary.md").write_text(_build_summary_markdown(summary, scores), encoding="utf-8")
    if scores:
        _write_leaderboard(output_path / "leaderboard.csv", scores)
    return summary
