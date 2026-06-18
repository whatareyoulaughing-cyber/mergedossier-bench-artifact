"""Label Studio import/export helpers for MergeDossier-Bench."""

from __future__ import annotations

import csv
import json
import random
import re
from pathlib import Path
from typing import Any

from .corpus import _iter_dossier_inputs
from .provenance import collect_provenance
from .scoring import score_dossier

EVIDENCE_CATEGORIES: tuple[str, ...] = (
    "intent_evidence",
    "requirement_evidence",
    "test_evidence",
    "risk_analysis",
    "scope_evidence",
    "trace_evidence",
    "dependency_evidence",
    "regression_evidence",
    "rationale_evidence",
    "ownership_handoff",
)

LABEL_VALUES: tuple[str, ...] = ("present", "partially_present", "missing", "not_applicable")

CSV_BASE_FIELDS: tuple[str, ...] = (
    "annotator_id",
    "instance_id",
    "reliability_group_id",
    "is_reliability_repeat",
    "source",
    "repo",
    "pr_number",
    "pr_url",
    "title",
    "existing_score",
    "missing_evidence",
    "dossier_text",
)

DOSSIER_TO_ANNOTATION_CATEGORY: dict[str, str] = {
    "intent": "intent_evidence",
    "requirement_traceability": "requirement_evidence",
    "test_rationale": "test_evidence",
    "risk_analysis": "risk_analysis",
    "scope_justification": "scope_evidence",
    "agent_trace": "trace_evidence",
    "regression_safety": "regression_evidence",
    "reviewer_actionability": "rationale_evidence",
    "ownership_handoff": "ownership_handoff",
}


def _first_present(data: dict[str, Any], keys: tuple[str, ...], default: Any = "") -> Any:
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    metadata = data.get("metadata", {})
    if isinstance(metadata, dict):
        for key in keys:
            value = metadata.get(key)
            if value not in (None, ""):
                return value
    return default


def _pr_number(dossier: dict[str, Any]) -> str | None:
    explicit = _first_present(dossier, ("pr_number", "number"), None)
    if explicit is not None:
        return str(explicit)
    pr_url = str(dossier.get("pr_url", ""))
    match = re.search(r"/pull/(\d+)", pr_url)
    return match.group(1) if match else None


def _evidence_item_text(name: str, item: dict[str, Any]) -> str:
    grounding = item.get("grounding", []) or []
    refs = ", ".join(str(g.get("reference", "")) for g in grounding if isinstance(g, dict) and g.get("reference"))
    parts = [
        f"{name}:",
        f"  present: {item.get('present')}",
        f"  quality: {item.get('quality')}",
        f"  claim: {item.get('claim', '')}",
    ]
    if refs:
        parts.append(f"  grounding: {refs}")
    if item.get("notes"):
        parts.append(f"  notes: {item.get('notes')}")
    return "\n".join(parts)


def _evidence_sections(dossier: dict[str, Any]) -> dict[str, str]:
    evidence = dossier.get("evidence", {})
    if not isinstance(evidence, dict):
        return {}
    sections: dict[str, str] = {}
    for key, value in evidence.items():
        if isinstance(value, dict):
            sections[key] = _evidence_item_text(key, value)
        else:
            sections[key] = str(value)
    return sections


def _provenance_item_text(record: dict[str, Any]) -> str:
    status = record.get("status", "missing")
    source_type = record.get("source_type", "unknown")
    rule = record.get("extraction_rule", "")
    confidence = record.get("confidence", "")
    excerpt = str(record.get("excerpt") or record.get("notes") or "").replace("\n", " ").strip()
    if len(excerpt) > 180:
        excerpt = excerpt[:177] + "..."
    suffix = f": {excerpt}" if excerpt else ""
    return f"{status} from {source_type} via {rule} ({confidence}){suffix}"


def _provenance_sections(dossier: dict[str, Any]) -> dict[str, list[str]]:
    provenance = collect_provenance(dossier)
    sections: dict[str, list[str]] = {category: [] for category in EVIDENCE_CATEGORIES}
    for dossier_key, annotation_key in DOSSIER_TO_ANNOTATION_CATEGORY.items():
        for record in provenance.get(dossier_key, []):
            sections.setdefault(annotation_key, []).append(_provenance_item_text(record))
    for key in ("dependency_evidence", "rationale_evidence"):
        for record in provenance.get(key, []):
            sections.setdefault(key, []).append(_provenance_item_text(record))
    return sections


def _dossier_text(dossier: dict[str, Any]) -> str:
    sections = _evidence_sections(dossier)
    return "\n\n".join(sections[key] for key in sorted(sections))


def _annotation_missing_from_score(score: dict[str, Any]) -> list[str]:
    missing = []
    for dossier_key in score.get("missing_evidence", []):
        missing.append(DOSSIER_TO_ANNOTATION_CATEGORY.get(str(dossier_key), str(dossier_key)))
    return missing


def build_annotation_task(dossier: dict[str, Any], source: str) -> dict[str, Any]:
    """Build one Label Studio import task from a MergeDossier dictionary."""
    score = score_dossier(dossier)
    instance_id = dossier.get("instance_id", "")
    data = {
        "instance_id": instance_id,
        "reliability_group_id": instance_id,
        "is_reliability_repeat": False,
        "source": source,
        "repo": dossier.get("repository", ""),
        "pr_number": _pr_number(dossier),
        "pr_url": dossier.get("pr_url", ""),
        "title": _first_present(dossier, ("title", "pr_title"), ""),
        "pr_body": _first_present(dossier, ("pr_body", "body", "summary"), ""),
        "issue_summary": _first_present(dossier, ("issue_summary", "linked_issue_summary"), ""),
        "changed_files_summary": _first_present(dossier, ("changed_files_summary", "diff_summary"), ""),
        "dossier_text": _dossier_text(dossier),
        "evidence_sections": _evidence_sections(dossier),
        "provenance_sections": _provenance_sections(dossier),
        "existing_score": score.get("evidence_sufficiency_score"),
        "missing_evidence": _annotation_missing_from_score(score),
    }
    return {"data": data}


def export_annotation_tasks(dossiers: str | Path, out: str | Path) -> list[dict[str, Any]]:
    """Export a dossier corpus to a Label Studio importable JSON file."""
    tasks = []
    for source, dossier, load_error in _iter_dossier_inputs(Path(dossiers)):
        if load_error is not None or dossier is None:
            continue
        tasks.append(build_annotation_task(dossier, source))
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(tasks, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return tasks


def create_reliability_sample(
    tasks_path: str | Path,
    out: str | Path,
    rate: float = 0.2,
    min_count: int = 5,
    seed: int = 13,
) -> list[dict[str, Any]]:
    """Append delayed-repeat tasks for single-operator self-consistency checks.

    The repeated tasks keep a stable ``reliability_group_id`` but receive a
    distinct ``instance_id`` so Label Studio treats them as separate tasks.
    """
    tasks = json.loads(Path(tasks_path).read_text(encoding="utf-8"))
    if not tasks:
        Path(out).write_text("[]\n", encoding="utf-8")
        return []
    count = min(len(tasks), max(min_count, round(len(tasks) * rate)))
    rng = random.Random(seed)
    selected_indices = sorted(rng.sample(range(len(tasks)), count))
    repeated: list[dict[str, Any]] = []
    for repeat_number, index in enumerate(selected_indices, start=1):
        original = json.loads(json.dumps(tasks[index]))
        data = original.setdefault("data", {})
        original_id = str(data.get("reliability_group_id") or data.get("instance_id") or f"task_{index}")
        data["reliability_group_id"] = original_id
        data["source_instance_id"] = data.get("instance_id", original_id)
        data["instance_id"] = f"{original_id}__repeat_{repeat_number}"
        data["is_reliability_repeat"] = True
        repeated.append(original)
    output_tasks = tasks + repeated
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output_tasks, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output_tasks


def _csv_fields() -> list[str]:
    fields = list(CSV_BASE_FIELDS)
    for category in EVIDENCE_CATEGORIES:
        fields.extend([f"{category}_label", f"{category}_comment"])
    fields.extend(["overall_acceptability", "review_confidence"])
    return fields


def export_annotation_csv_template(tasks: str | Path, out: str | Path, annotator_id: str = "solo") -> list[dict[str, Any]]:
    """Flatten annotation task JSON into a CSV sheet for spreadsheet labeling."""
    task_rows = json.loads(Path(tasks).read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for task in task_rows:
        data = task.get("data", task)
        row: dict[str, Any] = {field: "" for field in _csv_fields()}
        for field in CSV_BASE_FIELDS:
            value = data.get(field, "")
            if isinstance(value, list):
                value = ";".join(str(item) for item in value)
            elif isinstance(value, dict):
                value = json.dumps(value, ensure_ascii=False)
            row[field] = value
        row["annotator_id"] = annotator_id
        for category in EVIDENCE_CATEGORIES:
            row[f"{category}_label"] = ""
            row[f"{category}_comment"] = ""
        rows.append(row)

    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_csv_fields())
        writer.writeheader()
        writer.writerows(rows)
    return rows


def _boolish(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _normalized_label(value: Any) -> str | None:
    label = str(value).strip()
    if not label:
        return None
    if label not in LABEL_VALUES:
        raise ValueError(f"Unknown annotation label {label!r}; expected one of {', '.join(LABEL_VALUES)}")
    return label


def _normalized_rating(value: Any) -> int | float | str | None:
    text = str(value).strip()
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return text
    return int(number) if number.is_integer() else number


def parse_annotation_csv(path: str | Path) -> list[dict[str, Any]]:
    """Normalize spreadsheet-style annotation CSV rows into annotation records."""
    records: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for index, row in enumerate(reader, start=1):
            instance_id = str(row.get("instance_id", "")).strip()
            if not instance_id:
                continue
            record: dict[str, Any] = {
                "task_id": instance_id,
                "instance_id": instance_id,
                "reliability_group_id": row.get("reliability_group_id") or instance_id,
                "is_reliability_repeat": _boolish(row.get("is_reliability_repeat", "")),
                "annotator_id": row.get("annotator_id") or "solo",
                "category_labels": {category: None for category in EVIDENCE_CATEGORIES},
                "category_comments": {category: "" for category in EVIDENCE_CATEGORIES},
                "overall_acceptability": row.get("overall_acceptability") or None,
                "review_confidence": _normalized_rating(row.get("review_confidence", "")),
                "raw_annotation_id": f"csv:{index}",
                "created_at": None,
                "updated_at": None,
            }
            for category in EVIDENCE_CATEGORIES:
                record["category_labels"][category] = _normalized_label(row.get(f"{category}_label", ""))
                record["category_comments"][category] = row.get(f"{category}_comment", "") or ""
            records.append(record)
    return records


def validate_annotation_csv(path: str | Path, require_complete: bool = True) -> dict[str, Any]:
    """Check a spreadsheet-style annotation CSV before agreement analysis."""
    csv_path = Path(path)
    required_fields = list(CSV_BASE_FIELDS)
    for category in EVIDENCE_CATEGORIES:
        required_fields.extend([f"{category}_label", f"{category}_comment"])
    required_fields.extend(["overall_acceptability", "review_confidence"])

    errors: list[str] = []
    warnings: list[str] = []
    missing_label_cells: list[dict[str, Any]] = []
    invalid_label_cells: list[dict[str, Any]] = []
    total_rows = 0
    primary_rows = 0
    repeat_rows = 0
    completed_rows = 0

    try:
        f = csv_path.open("r", encoding="utf-8-sig", newline="")
    except OSError as exc:
        return {
            "valid": False,
            "path": str(csv_path),
            "total_rows": 0,
            "primary_rows": 0,
            "repeat_rows": 0,
            "completed_rows": 0,
            "incomplete_rows": 0,
            "missing_label_cells": [],
            "invalid_label_cells": [],
            "errors": [f"Could not read CSV: {exc}"],
            "warnings": [],
        }

    with f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        missing_columns = [field for field in required_fields if field not in fieldnames]
        if missing_columns:
            errors.append(f"Missing required columns: {', '.join(missing_columns)}")

        for row_number, row in enumerate(reader, start=2):
            total_rows += 1
            instance_id = str(row.get("instance_id", "")).strip()
            if not instance_id:
                errors.append(f"Row {row_number}: missing instance_id")
            if _boolish(row.get("is_reliability_repeat", "")):
                repeat_rows += 1
            else:
                primary_rows += 1

            row_complete = True
            for category in EVIDENCE_CATEGORIES:
                field = f"{category}_label"
                value = str(row.get(field, "")).strip()
                cell = {"row": row_number, "instance_id": instance_id, "field": field}
                if not value:
                    row_complete = False
                    missing_label_cells.append(cell)
                    message = f"Row {row_number} {field}: missing label"
                    if require_complete:
                        errors.append(message)
                    else:
                        warnings.append(message)
                elif value not in LABEL_VALUES:
                    row_complete = False
                    invalid = {**cell, "value": value}
                    invalid_label_cells.append(invalid)
                    errors.append(
                        f"Row {row_number} {field}: unknown label {value!r}; "
                        f"expected one of {', '.join(LABEL_VALUES)}"
                    )
            if row_complete:
                completed_rows += 1

    if total_rows == 0:
        errors.append("CSV contains no annotation rows")

    incomplete_rows = total_rows - completed_rows
    return {
        "valid": not errors,
        "path": str(csv_path),
        "total_rows": total_rows,
        "primary_rows": primary_rows,
        "repeat_rows": repeat_rows,
        "completed_rows": completed_rows,
        "incomplete_rows": incomplete_rows,
        "missing_label_cells": missing_label_cells,
        "invalid_label_cells": invalid_label_cells,
        "errors": errors,
        "warnings": warnings,
    }


def _annotator_id(annotation: dict[str, Any]) -> str | None:
    for key in ("completed_by", "created_by", "annotator_id"):
        value = annotation.get(key)
        if isinstance(value, dict):
            for subkey in ("id", "email", "username"):
                if value.get(subkey) is not None:
                    return str(value[subkey])
        if value is not None:
            return str(value)
    return None


def _choice_value(result: dict[str, Any]) -> str | None:
    value = result.get("value", {})
    if not isinstance(value, dict):
        return None
    choices = value.get("choices")
    if isinstance(choices, list) and choices:
        return str(choices[0])
    if "choice" in value:
        return str(value["choice"])
    return None


def _text_value(result: dict[str, Any]) -> str:
    value = result.get("value", {})
    if not isinstance(value, dict):
        return ""
    text = value.get("text")
    if isinstance(text, list):
        return "\n".join(str(item) for item in text)
    if text is not None:
        return str(text)
    return ""


def _rating_value(result: dict[str, Any]) -> int | float | str | None:
    value = result.get("value", {})
    if not isinstance(value, dict):
        return None
    for key in ("rating", "number", "value"):
        if key in value:
            return value[key]
    return None


def parse_label_studio_export(path: str | Path) -> list[dict[str, Any]]:
    """Normalize Label Studio JSON exports into one record per annotation."""
    tasks = json.loads(Path(path).read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = []
    for task in tasks:
        data = task.get("data", task)
        annotations = task.get("annotations", [])
        if not annotations and "result" in task:
            annotations = [task]
        for annotation in annotations:
            record: dict[str, Any] = {
                "task_id": task.get("id"),
                "instance_id": data.get("instance_id", ""),
                "reliability_group_id": data.get("reliability_group_id") or data.get("instance_id", ""),
                "is_reliability_repeat": bool(data.get("is_reliability_repeat", False)),
                "annotator_id": _annotator_id(annotation),
                "category_labels": {category: None for category in EVIDENCE_CATEGORIES},
                "category_comments": {category: "" for category in EVIDENCE_CATEGORIES},
                "overall_acceptability": None,
                "review_confidence": None,
                "raw_annotation_id": annotation.get("id"),
                "created_at": annotation.get("created_at"),
                "updated_at": annotation.get("updated_at"),
            }
            for result in annotation.get("result", []):
                name = result.get("from_name")
                if name in EVIDENCE_CATEGORIES:
                    record["category_labels"][name] = _choice_value(result)
                elif isinstance(name, str) and name.endswith("_comment"):
                    category = name.removesuffix("_comment")
                    if category in EVIDENCE_CATEGORIES:
                        record["category_comments"][category] = _text_value(result)
                elif name == "overall_acceptability":
                    record["overall_acceptability"] = _choice_value(result)
                elif name == "review_confidence":
                    record["review_confidence"] = _rating_value(result)
            records.append(record)
    return records


def parse_annotation_export(path: str | Path) -> list[dict[str, Any]]:
    """Parse supported annotation exports: Label Studio JSON or spreadsheet CSV."""
    annotation_path = Path(path)
    if annotation_path.suffix.lower() == ".csv":
        return parse_annotation_csv(annotation_path)
    return parse_label_studio_export(annotation_path)
