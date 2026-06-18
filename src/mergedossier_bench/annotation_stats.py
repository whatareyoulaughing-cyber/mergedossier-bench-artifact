"""Agreement and descriptive statistics for dossier annotations."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

from .label_studio import EVIDENCE_CATEGORIES, LABEL_VALUES, parse_annotation_export

LABEL_SEVERITY = {
    "missing": 0,
    "partially_present": 1,
    "present": 2,
    "not_applicable": 1,
}


def simple_percent_agreement(annotations: list[dict[str, Any]], field: str) -> float | None:
    """Compute simple agreement for a single top-level field on same item."""
    if len(annotations) < 2:
        return None
    total = 0
    agree = 0
    for a, b in combinations(annotations, 2):
        total += 1
        if a.get(field) == b.get(field):
            agree += 1
    return agree / total if total else None


def category_rating_distribution(annotations: list[dict[str, Any]]) -> dict[str, dict[int, int]]:
    """Return per-category rating counts for legacy 0/1/2 annotations."""
    counts: dict[str, Counter[int]] = defaultdict(Counter)
    for annotation in annotations:
        for category, rating in annotation.get("category_ratings", {}).items():
            counts[category][int(rating)] += 1
    return {category: dict(counter) for category, counter in counts.items()}


def group_by_dossier(annotations: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for annotation in annotations:
        grouped[str(annotation.get("dossier_id", annotation.get("instance_id", "UNKNOWN")))].append(annotation)
    return dict(grouped)


def group_by_instance(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(record.get("reliability_group_id") or record.get("instance_id", "UNKNOWN"))].append(record)
    return dict(grouped)


def label_distribution(records: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    counts: dict[str, Counter[str]] = {category: Counter() for category in EVIDENCE_CATEGORIES}
    for record in records:
        labels = record.get("category_labels", {})
        for category in EVIDENCE_CATEGORIES:
            label = labels.get(category)
            if label is not None:
                counts[category][str(label)] += 1
    return {category: {label: counter.get(label, 0) for label in LABEL_VALUES} for category, counter in counts.items()}


def category_rates(distribution: dict[str, dict[str, int]]) -> dict[str, dict[str, float]]:
    rates: dict[str, dict[str, float]] = {}
    for category, counts in distribution.items():
        total = sum(counts.values())
        if total == 0:
            rates[category] = {label: 0.0 for label in LABEL_VALUES}
        else:
            rates[category] = {label: round(count / total, 4) for label, count in counts.items()}
    return rates


def percent_agreement_by_category(records: list[dict[str, Any]]) -> dict[str, float | None]:
    grouped = group_by_instance(records)
    agreements: dict[str, float | None] = {}
    for category in EVIDENCE_CATEGORIES:
        total = 0
        agree = 0
        for task_records in grouped.values():
            labels = [
                record.get("category_labels", {}).get(category)
                for record in task_records
                if record.get("category_labels", {}).get(category) is not None
            ]
            for left, right in combinations(labels, 2):
                total += 1
                if left == right:
                    agree += 1
        agreements[category] = round(agree / total, 4) if total else None
    return agreements


def _two_annotators(records: list[dict[str, Any]]) -> list[str] | None:
    annotators = sorted({str(record.get("annotator_id")) for record in records if record.get("annotator_id") is not None})
    return annotators if len(annotators) == 2 else None


def cohen_kappa_by_category(records: list[dict[str, Any]]) -> dict[str, float | None]:
    """Compute pairwise Cohen's kappa when exactly two annotators are present."""
    annotators = _two_annotators(records)
    kappas: dict[str, float | None] = {category: None for category in EVIDENCE_CATEGORIES}
    if annotators is None:
        return kappas

    grouped = group_by_instance(records)
    for category in EVIDENCE_CATEGORIES:
        pairs: list[tuple[str, str]] = []
        for task_records in grouped.values():
            by_annotator = {str(record.get("annotator_id")): record for record in task_records}
            if not all(annotator in by_annotator for annotator in annotators):
                continue
            left = by_annotator[annotators[0]].get("category_labels", {}).get(category)
            right = by_annotator[annotators[1]].get("category_labels", {}).get(category)
            if left is not None and right is not None:
                pairs.append((str(left), str(right)))
        if not pairs:
            continue
        observed = sum(1 for left, right in pairs if left == right) / len(pairs)
        left_counts = Counter(left for left, _ in pairs)
        right_counts = Counter(right for _, right in pairs)
        expected = sum((left_counts[label] / len(pairs)) * (right_counts[label] / len(pairs)) for label in LABEL_VALUES)
        if expected == 1.0:
            kappas[category] = 1.0 if observed == 1.0 else 0.0
        else:
            kappas[category] = round((observed - expected) / (1 - expected), 4)
    return kappas


def majority_label_by_category(records: list[dict[str, Any]]) -> dict[str, str | None]:
    distribution = label_distribution(records)
    majority: dict[str, str | None] = {}
    for category, counts in distribution.items():
        if not any(counts.values()):
            majority[category] = None
            continue
        majority[category] = max(LABEL_VALUES, key=lambda label: (counts[label], -LABEL_VALUES.index(label)))
    return majority


def disagreement_cases(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped = group_by_instance(records)
    cases: list[dict[str, Any]] = []
    for group_id, task_records in grouped.items():
        task_disagreements = []
        severity = 0
        for category in EVIDENCE_CATEGORIES:
            labels = [
                str(record.get("category_labels", {}).get(category))
                for record in task_records
                if record.get("category_labels", {}).get(category) is not None
            ]
            unique = sorted(set(labels))
            if len(unique) <= 1:
                continue
            label_severity = max(LABEL_SEVERITY.get(label, 1) for label in unique) - min(
                LABEL_SEVERITY.get(label, 1) for label in unique
            )
            severity = max(severity, label_severity)
            task_disagreements.append({"category": category, "labels": unique, "severity": label_severity})
        if task_disagreements:
            cases.append(
                {
                    "instance_id": group_id,
                    "reliability_group_id": group_id,
                    "task_id": task_records[0].get("task_id"),
                    "annotator_ids": sorted(
                        str(record.get("annotator_id")) for record in task_records if record.get("annotator_id") is not None
                    ),
                    "severity": severity,
                    "disagreements": task_disagreements,
                }
            )
    return sorted(cases, key=lambda case: (case["severity"], len(case["disagreements"])), reverse=True)


def build_agreement_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    distribution = label_distribution(records)
    percent_agreement = percent_agreement_by_category(records)
    kappas = cohen_kappa_by_category(records)
    disagreements = disagreement_cases(records)
    grouped = group_by_instance(records)
    annotators = sorted({str(record.get("annotator_id")) for record in records if record.get("annotator_id") is not None})
    repeat_count = sum(1 for record in records if record.get("is_reliability_repeat"))
    disagreement_counts = Counter(
        disagreement["category"] for case in disagreements for disagreement in case.get("disagreements", [])
    )
    return {
        "total_tasks": len(grouped),
        "total_annotations": len(records),
        "reliability_repeat_annotations": repeat_count,
        "annotator_count": len(annotators),
        "evidence_categories": list(EVIDENCE_CATEGORIES),
        "label_distribution_by_category": distribution,
        "label_rates_by_category": category_rates(distribution),
        "percent_agreement_by_category": percent_agreement,
        "cohen_kappa_by_category": kappas,
        "majority_label_by_category": majority_label_by_category(records),
        "most_disagreed_categories": [
            {"category": category, "count": count} for category, count in disagreement_counts.most_common()
        ],
        "tasks_with_high_disagreement": disagreements[:10],
        "limitations": [
            "Cohen's kappa is reported only when exactly two distinct operators are present.",
            "For a single-operator audit, percent agreement is interpreted as delayed self-consistency when repeat tasks are included.",
            "Krippendorff's alpha is not implemented in this dependency-light MVP; add it before large multi-operator analysis."
        ],
    }


def _markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return "\n".join(lines)


def build_agreement_markdown(summary: dict[str, Any]) -> str:
    distribution_rows = []
    for category, counts in summary["label_distribution_by_category"].items():
        distribution_rows.append([category, counts["present"], counts["partially_present"], counts["missing"], counts["not_applicable"]])

    agreement_rows = []
    for category in summary["evidence_categories"]:
        agreement_rows.append(
            [
                category,
                summary["percent_agreement_by_category"].get(category),
                summary["cohen_kappa_by_category"].get(category),
                summary["majority_label_by_category"].get(category),
            ]
        )

    disagreement_rows = [
        [
            case["instance_id"],
            case["severity"],
            "; ".join(f"{item['category']}={','.join(item['labels'])}" for item in case["disagreements"]),
        ]
        for case in summary["tasks_with_high_disagreement"]
    ]

    sections = [
        "# MergeDossier-Bench Annotation Agreement Summary",
        "",
        "## Overview",
        "",
        f"- Total tasks: {summary['total_tasks']}",
        f"- Total annotations: {summary['total_annotations']}",
        f"- Reliability repeat annotations: {summary['reliability_repeat_annotations']}",
        f"- Operator count: {summary['annotator_count']}",
        "",
        "## Label distribution table",
        "",
        _markdown_table(["category", "present", "partially_present", "missing", "not_applicable"], distribution_rows),
        "",
        "## Agreement table",
        "",
        _markdown_table(["category", "percent_agreement", "cohen_kappa", "majority_label"], agreement_rows),
        "",
        "## Top disagreement cases",
        "",
        _markdown_table(["instance_id", "severity", "disagreements"], disagreement_rows)
        if disagreement_rows
        else "_No category disagreements detected._",
        "",
        "## Notes on limitations",
        "",
        "- These statistics summarize review-evidence availability audit codes, not patch correctness or mergeability.",
        "- With one operator, use delayed-repeat tasks and interpret percent agreement as self-consistency rather than inter-rater reliability.",
        "- Krippendorff's alpha is left as a future dependency-light extension for larger multi-operator batches.",
        "",
    ]
    return "\n".join(sections)


def write_annotation_stats(annotation_export: str | Path, out_dir: str | Path) -> dict[str, Any]:
    records = parse_annotation_export(annotation_export)
    summary = build_agreement_summary(records)
    disagreements = disagreement_cases(records)
    output_path = Path(out_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    with (output_path / "annotation_records.jsonl").open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    (output_path / "agreement_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (output_path / "agreement_summary.md").write_text(build_agreement_markdown(summary), encoding="utf-8")
    with (output_path / "disagreement_cases.jsonl").open("w", encoding="utf-8") as f:
        for case in disagreements:
            f.write(json.dumps(case, ensure_ascii=False) + "\n")
    return summary
