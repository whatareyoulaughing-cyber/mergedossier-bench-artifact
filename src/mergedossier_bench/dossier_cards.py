"""Compact Markdown dossier cards for audit and release browsing."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .provenance import PROVENANCE_CATEGORIES, collect_provenance, iter_dossier_inputs, markdown_table
from .schema import EVIDENCE_TYPES
from .scoring import score_dossier
from .validators import validate_data


def _safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._")
    return cleaned or "UNKNOWN"


def _snippet(record: dict[str, Any]) -> str:
    excerpt = str(record.get("excerpt") or record.get("notes") or "").replace("\n", " ").strip()
    if len(excerpt) > 120:
        excerpt = excerpt[:117] + "..."
    return excerpt


def _status_summary(records: list[dict[str, Any]]) -> str:
    if not records:
        return "missing"
    statuses = [str(record.get("status", "missing")) for record in records]
    return ",".join(dict.fromkeys(statuses))


def _category_rows(dossier: dict[str, Any], score: dict[str, Any]) -> list[list[Any]]:
    evidence = dossier.get("evidence", {}) if isinstance(dossier.get("evidence"), dict) else {}
    provenance = collect_provenance(dossier)
    rows: list[list[Any]] = []
    for category in EVIDENCE_TYPES:
        item = evidence.get(category, {}) if isinstance(evidence.get(category), dict) else {}
        records = provenance.get(category, [])
        snippet = "; ".join(filter(None, (_snippet(record) for record in records[:2])))
        rows.append(
            [
                category,
                bool(item.get("present", False)),
                item.get("quality", ""),
                score.get("category_scores", {}).get(category, 0),
                _status_summary(records),
                snippet,
            ]
        )
    return rows


def _provenance_extra_rows(dossier: dict[str, Any]) -> list[list[Any]]:
    provenance = collect_provenance(dossier)
    rows: list[list[Any]] = []
    for category in PROVENANCE_CATEGORIES:
        if category in EVIDENCE_TYPES:
            continue
        records = provenance.get(category, [])
        if not records:
            continue
        rows.append(
            [
                category,
                _status_summary(records),
                "; ".join(str(record.get("source_type", "")) for record in records),
                "; ".join(filter(None, (_snippet(record) for record in records[:2]))),
            ]
        )
    return rows


def _card_markdown(dossier: dict[str, Any], source: str) -> str:
    score = score_dossier(dossier)
    dossier_id = str(dossier.get("dossier_id") or dossier.get("instance_id") or "UNKNOWN")
    metadata = dossier.get("metadata", {}) if isinstance(dossier.get("metadata"), dict) else {}
    manifest = metadata.get("manifest_metadata", {}) if isinstance(metadata.get("manifest_metadata"), dict) else {}
    sections = [
        f"# {dossier_id}",
        "",
        "## Metadata",
        "",
        f"- Source: `{source}`",
        f"- Repository: `{dossier.get('repository', '')}`",
        f"- PR URL: {dossier.get('pr_url', '')}",
        f"- Source agent: `{dossier.get('source_agent', metadata.get('agent_name', ''))}`",
        f"- Author type: `{metadata.get('author_type', manifest.get('author_type', ''))}`",
        f"- Outcome: `{metadata.get('outcome', manifest.get('outcome', ''))}`",
        "",
        "## Legacy Artifact Triage",
        "",
        f"- Legacy Evidence Sufficiency Score: {score['evidence_sufficiency_score']}",
        f"- Legacy triage band: `{score['readiness_band']}`",
        f"- Missing evidence: {', '.join(score['missing_evidence']) if score['missing_evidence'] else 'none'}",
        "",
        "## Evidence And Provenance",
        "",
        markdown_table(
            ["category", "present", "quality", "score", "provenance_status", "snippet"],
            _category_rows(dossier, score),
        ),
    ]
    extra_rows = _provenance_extra_rows(dossier)
    if extra_rows:
        sections.extend(
            [
                "",
                "## Crosswalk Provenance",
                "",
                markdown_table(["category", "status", "source_type", "snippet"], extra_rows),
            ]
        )
    sections.extend(
        [
            "",
            "## Audit Notes",
            "",
            "This card reports visible evidence and citation provenance. It is not a patch-correctness or mergeability judgment.",
            "",
        ]
    )
    return "\n".join(sections)


def make_dossier_cards(dossiers: str | Path, out_dir: str | Path, fmt: str = "md") -> dict[str, Any]:
    """Write compact dossier cards and an index."""
    if fmt != "md":
        raise ValueError("Only Markdown dossier cards are currently supported")
    output_path = Path(out_dir)
    cards_path = output_path / "cards"
    cards_path.mkdir(parents=True, exist_ok=True)

    cards: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []
    for source, dossier, load_error in iter_dossier_inputs(dossiers):
        if load_error is not None or dossier is None:
            invalid.append({"source": source, "error": load_error or "missing dossier"})
            continue
        errors = validate_data(dossier, "dossier")
        if errors:
            invalid.append({"source": source, "error": errors[0], "validation_errors": errors})
            continue
        score = score_dossier(dossier)
        dossier_id = str(dossier.get("dossier_id") or dossier.get("instance_id") or "UNKNOWN")
        file_name = _safe_name(dossier_id) + ".md"
        (cards_path / file_name).write_text(_card_markdown(dossier, source), encoding="utf-8")
        cards.append(
            {
                "dossier_id": dossier_id,
                "card_path": f"cards/{file_name}",
                "score": score["evidence_sufficiency_score"],
                "readiness_band": score["readiness_band"],
                "missing_evidence": score["missing_evidence"],
            }
        )

    cards.sort(key=lambda row: float(row["score"]))
    summary = {"total_cards": len(cards), "invalid_dossiers": len(invalid), "cards": cards, "invalid": invalid}
    (output_path / "cards_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    index_rows = [[row["dossier_id"], row["score"], row["readiness_band"], row["card_path"]] for row in cards]
    (output_path / "index.md").write_text(
        "\n".join(
            [
                "# MergeDossier Cards",
                "",
                "Compact audit cards for visible evidence and provenance. A dossier must cite its evidence.",
                "",
                markdown_table(["dossier_id", "score", "readiness_band", "card"], index_rows) if index_rows else "_No valid dossiers._",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return summary
