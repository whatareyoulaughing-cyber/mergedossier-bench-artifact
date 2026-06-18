"""Build initial MergeDossier skeletons from normalized PR instances."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .schema import EVIDENCE_TYPES


def _empty_evidence_item(notes: str = "") -> dict[str, Any]:
    return {"present": False, "quality": 0, "claim": "", "grounding": [], "notes": notes}


def _grounded_item(claim: str, artifact_type: str, reference: str, excerpt: str = "", quality: int = 1, notes: str = "") -> dict[str, Any]:
    return {
        "present": True,
        "quality": quality,
        "claim": claim,
        "grounding": [{"artifact_type": artifact_type, "reference": reference, "excerpt": excerpt}],
        "notes": notes,
    }


def build_skeleton_dossier(instance: dict[str, Any]) -> dict[str, Any]:
    """Create a conservative dossier skeleton from a PR instance.

    This function intentionally does not hallucinate evidence. It fills only
    categories supported by obvious PR artifacts and marks the rest missing.
    """
    evidence = {key: _empty_evidence_item("No automatic evidence extracted.") for key in EVIDENCE_TYPES}

    title = instance.get("title", "") or ""
    body = instance.get("body", "") or ""
    issue_links = instance.get("issue_links", []) or []
    files = instance.get("files_changed", []) or []
    tests = instance.get("tests", []) or []
    ci_runs = instance.get("ci_runs", []) or []
    trace = instance.get("agent_trace", []) or []

    if title or body:
        evidence["intent"] = _grounded_item(
            claim=(title or body[:180]),
            artifact_type="pr_title_body",
            reference="title/body",
            excerpt=(body[:300] if body else title),
            quality=1,
            notes="Automatically extracted from PR title/body; human validation needed.",
        )
        evidence["change_summary"] = _grounded_item(
            claim=f"PR changes {len(files)} file(s): " + ", ".join(f.get("path", "?") for f in files[:5]),
            artifact_type="changed_files",
            reference="files_changed",
            quality=1,
            notes="File-level automatic summary.",
        )

    if issue_links:
        evidence["requirement_traceability"] = _grounded_item(
            claim="PR links to issue(s): " + ", ".join(issue_links),
            artifact_type="issue_links",
            reference="issue_links",
            quality=1,
            notes="Link exists, but requirement mapping may be incomplete.",
        )

    if tests:
        test_names = ", ".join(str(t.get("name", t.get("path", "test"))) for t in tests[:5])
        evidence["test_rationale"] = _grounded_item(
            claim=f"PR includes test evidence: {test_names}",
            artifact_type="tests",
            reference="tests",
            quality=1,
            notes="Presence of tests detected; rationale still requires human or model extraction.",
        )

    if ci_runs:
        successes = [run for run in ci_runs if str(run.get("status", "")).lower() in {"success", "passed", "pass"}]
        evidence["regression_safety"] = _grounded_item(
            claim=f"Detected {len(successes)}/{len(ci_runs)} successful CI run(s).",
            artifact_type="ci_runs",
            reference="ci_runs",
            quality=1 if successes else 0,
            notes="CI status is not a complete regression argument.",
        )

    if files:
        evidence["scope_justification"] = _grounded_item(
            claim=f"Changed-file scope: {len(files)} file(s), {sum(int(f.get('additions', 0)) for f in files)} additions, {sum(int(f.get('deletions', 0)) for f in files)} deletions.",
            artifact_type="changed_files",
            reference="files_changed",
            quality=1,
            notes="Scope is described but not justified.",
        )

    if trace:
        evidence["agent_trace"] = _grounded_item(
            claim=f"Agent trace contains {len(trace)} step(s).",
            artifact_type="agent_trace",
            reference="agent_trace",
            quality=1,
            notes="Trace presence detected; usefulness requires review.",
        )

    return {
        "schema_version": "0.1.0",
        "dossier_id": f"dossier-{instance.get('instance_id', 'unknown')}",
        "instance_id": instance.get("instance_id", "unknown"),
        "repository": instance.get("repository", "unknown"),
        "pr_url": instance.get("pr_url", ""),
        "source_agent": instance.get("source_agent", "unknown"),
        "created_at": instance.get("created_at", ""),
        "dossier_created_at": datetime.now(timezone.utc).isoformat(),
        "evidence": evidence,
        "limitations": ["Automatically generated skeleton; must be validated before use in research."],
        "metadata": {"builder": "mergedossier_bench.dossier_builder.build_skeleton_dossier"},
    }
