"""Evidence provenance audit utilities for MergeDossier-Bench."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from .schema import EVIDENCE_TYPES
from .validators import load_json, validate_data

PROVENANCE_STATUSES: tuple[str, ...] = ("observed", "inferred", "missing", "not_applicable")
PROVENANCE_SOURCE_TYPES: tuple[str, ...] = (
    "pr_title",
    "pr_body",
    "linked_issue",
    "changed_file",
    "commit",
    "ci_check",
    "status",
    "review",
    "review_comment",
    "issue_comment",
    "manifest",
    "heuristic",
    "unknown",
)
PROVENANCE_CONFIDENCE: tuple[str, ...] = ("high", "medium", "low")

PROVENANCE_CATEGORIES: tuple[str, ...] = EVIDENCE_TYPES + ("dependency_evidence", "rationale_evidence")


def make_provenance_record(
    status: str,
    source_type: str,
    extraction_rule: str,
    confidence: str = "medium",
    *,
    source_id: str | int | None = None,
    source_url: str | None = None,
    raw_path: str | None = None,
    excerpt: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Create one schema-compatible provenance record."""
    return {
        "status": status,
        "source_type": source_type,
        "source_id": source_id,
        "source_url": source_url,
        "raw_path": raw_path,
        "excerpt": excerpt[:500] if isinstance(excerpt, str) else excerpt,
        "extraction_rule": extraction_rule,
        "confidence": confidence,
        "notes": notes,
    }


def iter_dossier_inputs(dossiers: str | Path) -> Iterable[tuple[str, dict[str, Any] | None, str | None]]:
    """Yield dossiers from one JSON file, a JSONL file, or a directory."""
    path = Path(dossiers)
    if path.is_dir():
        for dossier_path in sorted(path.glob("*.json")):
            try:
                yield str(dossier_path), load_json(dossier_path), None
            except Exception as exc:
                yield str(dossier_path), None, str(exc)
        return
    if path.suffix.lower() == ".jsonl":
        with path.open("r", encoding="utf-8") as f:
            for line_number, line in enumerate(f, start=1):
                if not line.strip():
                    continue
                source = f"{path}:{line_number}"
                try:
                    yield source, json.loads(line), None
                except json.JSONDecodeError as exc:
                    yield source, None, str(exc)
        return
    try:
        yield str(path), load_json(path), None
    except Exception as exc:
        yield str(path), None, str(exc)


def collect_provenance(dossier: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Return normalized provenance mapping for a dossier."""
    provenance = dossier.get("evidence_provenance", {})
    if not isinstance(provenance, dict):
        return {}
    normalized: dict[str, list[dict[str, Any]]] = {}
    for category, records in provenance.items():
        if isinstance(records, list):
            normalized[str(category)] = [record for record in records if isinstance(record, dict)]
    return normalized


def find_uncited_evidence(dossier: dict[str, Any]) -> list[dict[str, Any]]:
    """Find present evidence items without observed/inferred provenance."""
    provenance = collect_provenance(dossier)
    rows: list[dict[str, Any]] = []
    evidence = dossier.get("evidence", {})
    if not isinstance(evidence, dict):
        return rows
    for category in EVIDENCE_TYPES:
        item = evidence.get(category)
        if not isinstance(item, dict) or not item.get("present"):
            continue
        records = provenance.get(category, [])
        cited = any(record.get("status") in {"observed", "inferred"} for record in records)
        if not cited:
            rows.append(
                {
                    "dossier_id": dossier.get("dossier_id", ""),
                    "instance_id": dossier.get("instance_id", ""),
                    "category": category,
                    "claim": item.get("claim", ""),
                }
            )
    return rows


def find_evidence_without_sources(dossier: dict[str, Any]) -> list[dict[str, Any]]:
    """Find provenance records that cite evidence but lack source pointers."""
    rows: list[dict[str, Any]] = []
    for category, records in collect_provenance(dossier).items():
        for index, record in enumerate(records):
            if record.get("status") not in {"observed", "inferred"}:
                continue
            if any(record.get(key) for key in ("source_id", "source_url", "raw_path", "excerpt")):
                continue
            rows.append(
                {
                    "dossier_id": dossier.get("dossier_id", ""),
                    "instance_id": dossier.get("instance_id", ""),
                    "category": category,
                    "record_index": index,
                    "status": record.get("status", ""),
                    "source_type": record.get("source_type", ""),
                    "extraction_rule": record.get("extraction_rule", ""),
                }
            )
    return rows


def missing_provenance_rows(dossier: dict[str, Any]) -> list[dict[str, Any]]:
    """Find categories present in the evidence schema but missing provenance."""
    provenance = collect_provenance(dossier)
    rows: list[dict[str, Any]] = []
    for category in EVIDENCE_TYPES:
        if category not in provenance:
            rows.append(
                {
                    "dossier_id": dossier.get("dossier_id", ""),
                    "instance_id": dossier.get("instance_id", ""),
                    "category": category,
                    "validation_error": "missing provenance category",
                }
            )
    return rows


def audit_dossier_provenance(dossier: dict[str, Any]) -> dict[str, Any]:
    """Audit one dossier for provenance completeness and uncited evidence."""
    return {
        "dossier_id": dossier.get("dossier_id", ""),
        "instance_id": dossier.get("instance_id", ""),
        "has_provenance": bool(collect_provenance(dossier)),
        "missing_provenance": missing_provenance_rows(dossier),
        "uncited_evidence": find_uncited_evidence(dossier),
        "evidence_without_sources": find_evidence_without_sources(dossier),
    }


def provenance_coverage_by_category(dossiers: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Compute per-category provenance coverage."""
    coverage: dict[str, dict[str, Any]] = {}
    total = len(dossiers)
    for category in PROVENANCE_CATEGORIES:
        with_records = sum(1 for dossier in dossiers if collect_provenance(dossier).get(category))
        coverage[category] = {
            "dossiers_with_records": with_records,
            "coverage_rate": round(with_records / total, 4) if total else 0.0,
        }
    return coverage


def summarize_provenance(dossiers: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize provenance status and source coverage for a corpus."""
    total = len(dossiers)
    with_provenance = sum(1 for dossier in dossiers if collect_provenance(dossier))
    status_counts_by_category: dict[str, dict[str, int]] = {}
    source_counts: Counter[str] = Counter()
    inferred_vs_observed: Counter[str] = Counter()
    missing_counts: Counter[str] = Counter()
    uncited_rows: list[dict[str, Any]] = []
    dossiers_with_uncited: set[str] = set()

    for dossier in dossiers:
        provenance = collect_provenance(dossier)
        for category in PROVENANCE_CATEGORIES:
            category_counts = status_counts_by_category.setdefault(category, {status: 0 for status in PROVENANCE_STATUSES})
            records = provenance.get(category, [])
            if not records and category in EVIDENCE_TYPES:
                category_counts["missing"] += 1
                missing_counts[category] += 1
            for record in records:
                status = str(record.get("status", "missing"))
                if status not in PROVENANCE_STATUSES:
                    status = "missing"
                category_counts[status] += 1
                if status == "missing":
                    missing_counts[category] += 1
                source_counts[str(record.get("source_type", "unknown"))] += 1
                if status in {"observed", "inferred"}:
                    inferred_vs_observed[status] += 1
        uncited = find_uncited_evidence(dossier)
        uncited_rows.extend(uncited)
        if uncited:
            dossiers_with_uncited.add(str(dossier.get("dossier_id", dossier.get("instance_id", ""))))

    return {
        "total_dossiers": total,
        "dossiers_with_provenance": with_provenance,
        "provenance_coverage_rate": round(with_provenance / total, 4) if total else 0.0,
        "category_coverage": provenance_coverage_by_category(dossiers),
        "status_counts_by_category": status_counts_by_category,
        "source_type_counts": dict(sorted(source_counts.items())),
        "inferred_vs_observed_counts": dict(sorted(inferred_vs_observed.items())),
        "top_missing_categories": [
            {"category": category, "count": count} for category, count in missing_counts.most_common(10)
        ],
        "uncited_evidence_count": len(uncited_rows),
        "dossiers_with_uncited_evidence": len(dossiers_with_uncited),
    }


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(lines)


def provenance_summary_markdown(summary: dict[str, Any]) -> str:
    """Render a human-readable provenance audit summary."""
    category_rows = [
        [
            category,
            value["dossiers_with_records"],
            f"{value['coverage_rate']:.2%}",
            summary["status_counts_by_category"].get(category, {}).get("observed", 0),
            summary["status_counts_by_category"].get(category, {}).get("inferred", 0),
            summary["status_counts_by_category"].get(category, {}).get("missing", 0),
        ]
        for category, value in summary["category_coverage"].items()
    ]
    source_rows = [[key, value] for key, value in summary["source_type_counts"].items()]
    missing_rows = [[row["category"], row["count"]] for row in summary["top_missing_categories"]]
    return "\n".join(
        [
            "# Evidence Provenance Audit",
            "",
            f"- Total dossiers: {summary['total_dossiers']}",
            f"- Dossiers with provenance: {summary['dossiers_with_provenance']}",
            f"- Provenance coverage rate: {summary['provenance_coverage_rate']:.2%}",
            f"- Uncited evidence rows: {summary['uncited_evidence_count']}",
            f"- Dossiers with uncited evidence: {summary['dossiers_with_uncited_evidence']}",
            "",
            "## Category Coverage",
            "",
            markdown_table(["category", "dossiers_with_records", "coverage", "observed", "inferred", "missing"], category_rows),
            "",
            "## Source Types",
            "",
            markdown_table(["source_type", "count"], source_rows) if source_rows else "_No provenance source records._",
            "",
            "## Top Missing Categories",
            "",
            markdown_table(["category", "count"], missing_rows) if missing_rows else "_No missing provenance records._",
            "",
        ]
    )


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def audit_provenance(dossiers: str | Path, out_dir: str | Path) -> dict[str, Any]:
    """Audit provenance for a dossier corpus and write JSON/Markdown reports."""
    output_path = Path(out_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    valid_dossiers: list[dict[str, Any]] = []
    missing_rows: list[dict[str, Any]] = []
    uncited_rows: list[dict[str, Any]] = []

    for source, dossier, load_error in iter_dossier_inputs(dossiers):
        if load_error is not None or dossier is None:
            missing_rows.append({"source": source, "validation_error": load_error or "missing dossier"})
            continue
        errors = validate_data(dossier, "dossier")
        if errors:
            missing_rows.append({"source": source, "validation_error": errors[0], "validation_errors": errors})
            continue
        valid_dossiers.append(dossier)
        audit = audit_dossier_provenance(dossier)
        for row in audit["missing_provenance"]:
            missing_rows.append({"source": source, **row})
        for row in audit["uncited_evidence"] + audit["evidence_without_sources"]:
            uncited_rows.append({"source": source, **row})

    summary = summarize_provenance(valid_dossiers)
    (output_path / "provenance_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output_path / "provenance_summary.md").write_text(provenance_summary_markdown(summary), encoding="utf-8")
    write_jsonl(output_path / "uncited_evidence.jsonl", uncited_rows)
    write_jsonl(output_path / "missing_provenance.jsonl", missing_rows)
    return summary


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
