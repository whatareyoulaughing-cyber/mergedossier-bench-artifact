"""Evidence Sufficiency Score for MergeDossier-Bench."""

from __future__ import annotations

from typing import Any

from .schema import EVIDENCE_TYPES

# Weights sum to 1.0. Test rationale, risk, scope, and requirement traceability
# receive slightly higher weight because they are most directly tied to reviewer
# decision support.
DEFAULT_WEIGHTS: dict[str, float] = {
    "intent": 0.08,
    "requirement_traceability": 0.12,
    "test_rationale": 0.13,
    "regression_safety": 0.10,
    "risk_analysis": 0.12,
    "scope_justification": 0.11,
    "change_summary": 0.07,
    "agent_trace": 0.08,
    "limitations": 0.07,
    "reviewer_actionability": 0.07,
    "ownership_handoff": 0.05,
}


def readiness_band(score: float) -> str:
    """Map a 0-100 Evidence Sufficiency Score to a qualitative band."""
    if score < 40:
        return "insufficient"
    if score < 60:
        return "thin"
    if score < 75:
        return "adequate"
    return "strong"


def score_evidence_item(item: dict[str, Any]) -> float:
    """Score one evidence item on a 0-1 scale.

    Quality is the primary signal. Grounding adds a small bonus only when the
    item is present and specific enough to have quality > 0. False or misleading
    claims should be assigned quality 0 by annotation/extraction.
    """
    quality = float(item.get("quality", 0))
    present = bool(item.get("present", False))
    grounding = item.get("grounding", []) or []
    if not present:
        return 0.0
    base = max(0.0, min(quality, 2.0)) / 2.0
    grounded_bonus = 0.05 if base > 0 and grounding else 0.0
    return min(1.0, base + grounded_bonus)


def score_dossier(dossier: dict[str, Any], weights: dict[str, float] | None = None) -> dict[str, Any]:
    """Compute a score report for a MergeDossier dictionary."""
    weights = weights or DEFAULT_WEIGHTS
    evidence = dossier.get("evidence", {})
    category_scores: dict[str, float] = {}
    missing: list[str] = []
    warnings: list[str] = []

    total = 0.0
    total_weight = 0.0
    for evidence_type in EVIDENCE_TYPES:
        weight = weights.get(evidence_type, 0.0)
        total_weight += weight
        item = evidence.get(evidence_type)
        if item is None:
            category_scores[evidence_type] = 0.0
            missing.append(evidence_type)
            warnings.append(f"Missing evidence category: {evidence_type}")
            continue
        item_score = score_evidence_item(item)
        category_scores[evidence_type] = round(item_score * 100, 2)
        if not item.get("present", False) or item_score == 0:
            missing.append(evidence_type)
        if item.get("present") and item.get("quality", 0) == 0:
            warnings.append(f"Evidence marked present but quality=0: {evidence_type}")
        total += weight * item_score

    normalized = 0.0 if total_weight == 0 else (total / total_weight) * 100
    normalized = round(normalized, 2)
    return {
        "schema_version": "0.1.0",
        "dossier_id": dossier.get("dossier_id", "UNKNOWN"),
        "evidence_sufficiency_score": normalized,
        "readiness_band": readiness_band(normalized),
        "category_scores": category_scores,
        "missing_evidence": missing,
        "warnings": warnings,
    }
