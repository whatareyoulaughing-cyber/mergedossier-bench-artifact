"""Typed schema helpers for MergeDossier-Bench.

The project uses JSON Schema for interchange. These dataclasses are lightweight
helpers for code that wants typed objects without depending on Pydantic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


EVIDENCE_TYPES: tuple[str, ...] = (
    "intent",
    "requirement_traceability",
    "test_rationale",
    "regression_safety",
    "risk_analysis",
    "scope_justification",
    "change_summary",
    "agent_trace",
    "limitations",
    "reviewer_actionability",
    "ownership_handoff",
)


@dataclass(frozen=True)
class Grounding:
    """A pointer from an evidence claim to a PR artifact."""

    artifact_type: str
    reference: str
    excerpt: str = ""


@dataclass(frozen=True)
class EvidenceItem:
    """One evidence category in a MergeDossier."""

    present: bool
    quality: int
    claim: str
    grounding: list[Grounding] = field(default_factory=list)
    notes: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceItem":
        return cls(
            present=bool(data.get("present", False)),
            quality=int(data.get("quality", 0)),
            claim=str(data.get("claim", "")),
            grounding=[Grounding(**g) for g in data.get("grounding", [])],
            notes=str(data.get("notes", "")),
        )


@dataclass(frozen=True)
class MergeDossier:
    """A structured evidence packet attached to an AI-authored PR."""

    dossier_id: str
    instance_id: str
    repository: str
    pr_url: str
    source_agent: str
    evidence: dict[str, EvidenceItem]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MergeDossier":
        evidence_raw = data.get("evidence", {})
        return cls(
            dossier_id=str(data["dossier_id"]),
            instance_id=str(data["instance_id"]),
            repository=str(data["repository"]),
            pr_url=str(data["pr_url"]),
            source_agent=str(data["source_agent"]),
            evidence={key: EvidenceItem.from_dict(value) for key, value in evidence_raw.items()},
        )
