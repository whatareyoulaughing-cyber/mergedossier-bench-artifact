"""Population-frame sampling and analysis utilities."""

from __future__ import annotations

import csv
import json
import math
import random
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .corpus import summarize_corpus
from .dossier_cards import make_dossier_cards
from .label_studio import (
    EVIDENCE_CATEGORIES,
    create_reliability_sample,
    export_annotation_csv_template,
    export_annotation_tasks,
    parse_annotation_export,
)
from .pilot_analysis import run_pilot_analysis
from .provenance import PROVENANCE_CATEGORIES, PROVENANCE_SOURCE_TYPES, audit_provenance, collect_provenance, iter_dossier_inputs, markdown_table
from .schema import EVIDENCE_TYPES
from .seed_builder import MANIFEST_COLUMNS, reconstruct_dossier_from_raw, write_seed_corpus
from .validators import validate_data


FRAME_EXTRA_COLUMNS: tuple[str, ...] = (
    "agent_tool",
    "created_at",
    "changed_file_count",
    "commit_count",
    "comment_count",
    "review_count",
    "artifact_completeness",
    "eligibility",
    "eligibility_reason",
    "size_tercile",
    "sampling_weight",
    "title",
    "body",
    "files_changed",
    "commit_messages",
    "comments",
    "reviews",
    "ci_status",
)

FRAME_COLUMNS: tuple[str, ...] = MANIFEST_COLUMNS + FRAME_EXTRA_COLUMNS

AGENT_ALIASES = {
    "codex": "codex",
    "openai codex": "codex",
    "openai": "codex",
    "claude": "claude_code",
    "claude code": "claude_code",
    "anthropic claude": "claude_code",
    "copilot": "copilot",
    "github copilot": "copilot",
    "cursor": "cursor",
    "devin": "devin",
    "aider": "aider",
}

TASK_ALIASES = {
    "bug": "bug_fix",
    "bugfix": "bug_fix",
    "bug_fix": "bug_fix",
    "fix": "bug_fix",
    "feature": "feature",
    "refactor": "refactor",
    "test": "test",
    "tests": "test",
    "docs": "docs",
    "documentation": "docs",
    "dependency": "dependency",
    "dependencies": "dependency",
}

OUTCOME_ALIASES = {
    "merged": "merged",
    "merge": "merged",
    "closed_unmerged": "closed_unmerged",
    "closed": "closed_unmerged",
    "rejected": "closed_unmerged",
    "open": "open",
    "draft_open": "open",
}

CLAIMS_NONCLAIMS: tuple[tuple[str, str], ...] = (
    ("Handoff-evidence gap within AIDev-pop", "All-GitHub AI-authored PR rates"),
    ("Category-level evidence visibility and missing evidence rates", "Patch correctness"),
    ("Provenance-backed auditability of reconstructed PR evidence", "Mergeability"),
    ("Delayed-repeat self-consistency for one operator", "Inter-rater reliability"),
    ("Dependency evidence availability among detected manifest/lockfile candidates", "Full-sample dependency prevalence"),
    ("Artifact reproducibility and offline inspectability", "Reviewer utility"),
    ("Descriptive population-frame estimates", "AI-vs-human causal effects"),
)

COMPACT_SENSITIVITY_CATEGORIES: tuple[tuple[str, str, str], ...] = (
    ("intent_evidence", "Intent", "robust high"),
    ("test_evidence", "Test", "partial-sensitive"),
    ("risk_analysis", "Risk", "robust low"),
    ("scope_evidence", "Scope", "partial-sensitive"),
    ("trace_evidence", "Trace", "robust low"),
    ("regression_evidence", "Regression", "robust low"),
    ("rationale_evidence", "Rationale", "robust low"),
    ("ownership_handoff", "Ownership", "robust low"),
)

COMPACT_PROVENANCE_CATEGORIES: tuple[tuple[str, str, str], ...] = (
    ("intent", "Intent", "direct visible intent"),
    ("test_rationale", "Test", "test text or file-derived signal"),
    ("risk_analysis", "Risk", "risk or rollback text when visible"),
    ("scope_justification", "Scope", "often metadata-inferred scope signal"),
    ("agent_trace", "Trace", "trace evidence absent in reconstructed dossiers"),
    ("regression_safety", "Regression", "explicit regression boundary when visible"),
    ("reviewer_actionability", "Rationale", "annotation-family rationale proxy"),
    ("ownership_handoff", "Ownership", "handoff or follow-up text when visible"),
)

AVAILABILITY_INTERVAL_CATEGORIES: tuple[tuple[str, str, str], ...] = (
    ("intent_evidence", "Intent", "core"),
    ("requirement_evidence", "Requirement", "context"),
    ("test_evidence", "Test", "core"),
    ("risk_analysis", "Risk", "handoff"),
    ("scope_evidence", "Scope", "core"),
    ("trace_evidence", "Trace", "handoff"),
    ("regression_evidence", "Regression", "handoff"),
    ("rationale_evidence", "Rationale", "handoff"),
    ("ownership_handoff", "Ownership", "handoff"),
)

CORE_EVIDENCE_CATEGORIES: tuple[str, ...] = ("intent_evidence", "test_evidence", "scope_evidence")
HANDOFF_EVIDENCE_CATEGORIES: tuple[str, ...] = (
    "risk_analysis",
    "trace_evidence",
    "regression_evidence",
    "rationale_evidence",
    "ownership_handoff",
)
TIPPING_POINT_THRESHOLD = 0.5


def read_csv_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        return [{key: value or "" for key, value in row.items()} for row in csv.DictReader(f)]


def write_csv_rows(path: str | Path, rows: list[dict[str, Any]], fieldnames: Iterable[str] = FRAME_COLUMNS) -> None:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(fieldnames)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def _first(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return ""


def _parse_int(value: Any, default: int = 0) -> int:
    if value in (None, ""):
        return default
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    try:
        return int(float(text))
    except ValueError:
        return default


def _parse_repo_from_url(url: str) -> tuple[str, str]:
    match = re.search(r"github\.com/([^/\s]+)/([^/\s]+)/pull/(\d+)", url)
    if not match:
        return "", ""
    return f"{match.group(1)}/{match.group(2)}", match.group(3)


def normalize_agent(value: str, *fallback_texts: str) -> str:
    text = " ".join([value, *fallback_texts]).lower()
    for needle, normalized in AGENT_ALIASES.items():
        if needle in text:
            return normalized
    return "unknown"


def normalize_task(value: str) -> str:
    text = value.lower().strip()
    return TASK_ALIASES.get(text, "unknown")


def normalize_outcome(row: dict[str, Any]) -> str:
    explicit = _first(row, "outcome", "state", "status")
    if explicit.lower() in OUTCOME_ALIASES:
        return OUTCOME_ALIASES[explicit.lower()]
    merged_at = _first(row, "merged_at", "merge_commit_sha")
    closed_at = _first(row, "closed_at")
    if merged_at:
        return "merged"
    if closed_at:
        return "closed_unmerged"
    return "open" if explicit.lower() == "open" else "unknown"


def _pr_url(repo: str, pr_number: str, row: dict[str, Any]) -> str:
    explicit = _first(row, "pr_url", "html_url", "url")
    if explicit.startswith("http") and "/pull/" in explicit:
        return explicit
    return f"https://github.com/{repo}/pull/{pr_number}" if repo and pr_number else explicit


def _artifact_completeness(row: dict[str, Any]) -> str:
    has_text = bool(_first(row, "title", "body", "description"))
    has_counts = any(_first(row, key) for key in ("changed_file_count", "files_changed", "commits", "commit_count"))
    if has_text and has_counts:
        return "metadata_text_counts"
    if has_text:
        return "metadata_text"
    if has_counts:
        return "metadata_counts"
    return "metadata_only"


def normalize_population_row(row: dict[str, Any]) -> dict[str, str]:
    pr_url = _first(row, "pr_url", "html_url", "url")
    repo = _first(row, "repo", "repository", "full_name")
    pr_number = _first(row, "pr_number", "number", "pull_number")
    if not (repo and pr_number) and pr_url:
        parsed_repo, parsed_number = _parse_repo_from_url(pr_url)
        repo = repo or parsed_repo
        pr_number = pr_number or parsed_number

    title = _first(row, "title", "pr_title")
    body = _first(row, "body", "pr_body", "description")
    agent_raw = _first(row, "agent_name", "source_agent", "agent", "tool", "model")
    author = _first(row, "author", "user_login", "creator", "login")
    labels = _first(row, "labels", "label_names")
    notes = _first(row, "notes")
    agent_name = normalize_agent(agent_raw, author, title, body, labels, notes)
    explicit_author_type = _first(row, "author_type")
    author_type = explicit_author_type if explicit_author_type in {"ai_authored", "mixed", "human_authored", "unknown"} else ""
    if not author_type:
        author_type = "ai_authored" if agent_name != "unknown" else "unknown"

    changed_file_count = _parse_int(_first(row, "changed_file_count", "changed_files_count", "files_count", "num_files"))
    commit_count = _parse_int(_first(row, "commit_count", "commits_count", "num_commits"))
    comment_count = _parse_int(_first(row, "comment_count", "comments_count", "issue_comment_count"))
    review_count = _parse_int(_first(row, "review_count", "reviews_count", "review_comment_count"))
    completeness = _artifact_completeness(row)
    eligible = bool(repo and pr_number and agent_name != "unknown" and author_type in {"ai_authored", "mixed"})
    if not repo or not pr_number:
        reason = "missing_repo_or_pr_number"
    elif agent_name == "unknown" or author_type not in {"ai_authored", "mixed"}:
        reason = "missing_ai_authorship_evidence"
    else:
        reason = "eligible"

    instance_id = _first(row, "instance_id", "id")
    if not instance_id and repo and pr_number:
        instance_id = f"pop_{repo.replace('/', '_')}_{pr_number}"
    normalized = {
        "instance_id": instance_id,
        "repo": repo,
        "pr_number": str(_parse_int(pr_number, 0)),
        "pr_url": _pr_url(repo, str(_parse_int(pr_number, 0)), row),
        "source": _first(row, "source") or "aidev_curated_frame",
        "author_type": author_type,
        "agent_name": agent_name,
        "task_type": normalize_task(_first(row, "task_type", "type", "category")),
        "language": _first(row, "language", "primary_language", "ecosystem") or "unknown",
        "outcome": normalize_outcome(row),
        "sample_split": _first(row, "sample_split") or "test",
        "notes": notes or f"Population frame row from AIDev-like source; eligibility={reason}.",
        "agent_tool": agent_raw or agent_name,
        "created_at": _first(row, "created_at", "opened_at"),
        "changed_file_count": str(changed_file_count),
        "commit_count": str(commit_count),
        "comment_count": str(comment_count),
        "review_count": str(review_count),
        "artifact_completeness": completeness,
        "eligibility": "eligible" if eligible else "excluded",
        "eligibility_reason": reason,
        "size_tercile": "",
        "sampling_weight": "",
        "title": title,
        "body": body,
        "files_changed": _first(row, "files_changed", "changed_files", "file_paths"),
        "commit_messages": _first(row, "commit_messages", "commits"),
        "comments": _first(row, "comments", "issue_comments", "review_comments"),
        "reviews": _first(row, "reviews"),
        "ci_status": _first(row, "ci_status", "check_status", "status_checks"),
    }
    return normalized


def assign_size_terciles(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    eligible_counts = sorted(_parse_int(row.get("changed_file_count")) for row in rows if row.get("eligibility") == "eligible")
    if not eligible_counts:
        return rows
    low_index = max(0, math.floor((len(eligible_counts) - 1) / 3))
    high_index = max(0, math.floor(2 * (len(eligible_counts) - 1) / 3))
    low_cut = eligible_counts[low_index]
    high_cut = eligible_counts[high_index]
    for row in rows:
        count = _parse_int(row.get("changed_file_count"))
        if row.get("eligibility") != "eligible":
            row["size_tercile"] = "excluded"
        elif count <= low_cut:
            row["size_tercile"] = "small"
        elif count <= high_cut:
            row["size_tercile"] = "medium"
        else:
            row["size_tercile"] = "large"
    return rows


def build_population_frame(rows: list[dict[str, Any]]) -> tuple[list[dict[str, str]], dict[str, Any]]:
    normalized = assign_size_terciles([normalize_population_row(row) for row in rows])
    counts = Counter(row["eligibility"] for row in normalized)
    summary = {
        "frame_size": len(normalized),
        "eligible_size": counts.get("eligible", 0),
        "excluded_size": len(normalized) - counts.get("eligible", 0),
        "eligibility_reason_counts": dict(Counter(row["eligibility_reason"] for row in normalized)),
        "agent_counts": dict(Counter(row["agent_name"] for row in normalized if row["eligibility"] == "eligible")),
        "language_counts": dict(Counter(row["language"] for row in normalized if row["eligibility"] == "eligible")),
        "outcome_counts": dict(Counter(row["outcome"] for row in normalized if row["eligibility"] == "eligible")),
        "size_tercile_counts": dict(Counter(row["size_tercile"] for row in normalized if row["eligibility"] == "eligible")),
    }
    return normalized, summary


def _proportional_targets(counts: dict[str, int], total: int) -> dict[str, int]:
    available_total = sum(counts.values())
    if available_total == 0 or total <= 0:
        return {key: 0 for key in counts}
    raw = {key: total * value / available_total for key, value in counts.items()}
    targets = {key: min(counts[key], math.floor(value)) for key, value in raw.items()}
    remaining = total - sum(targets.values())
    for key, _ in sorted(raw.items(), key=lambda item: (item[1] - math.floor(item[1]), item[0]), reverse=True):
        if remaining <= 0:
            break
        if targets[key] < counts[key]:
            targets[key] += 1
            remaining -= 1
    return targets


def allocate_agent_targets(
    eligible_rows: list[dict[str, str]],
    n: int,
    min_per_agent: int = 50,
) -> dict[str, int]:
    counts = Counter(row["agent_name"] for row in eligible_rows)
    target_total = min(n, len(eligible_rows))
    agents = sorted(counts)
    if not agents:
        return {}
    targets = {agent: 0 for agent in agents}
    if len(agents) * min_per_agent <= target_total:
        for agent in agents:
            targets[agent] = min(min_per_agent, counts[agent])
        remaining = target_total - sum(targets.values())
        residual_counts = {agent: counts[agent] - targets[agent] for agent in agents}
        residual_targets = _proportional_targets(residual_counts, remaining)
        for agent, extra in residual_targets.items():
            targets[agent] += extra
    else:
        targets = _proportional_targets(dict(counts), target_total)
    return targets


def _sample_within_agent(rows: list[dict[str, str]], target: int, rng: random.Random) -> list[dict[str, str]]:
    if target >= len(rows):
        return list(rows)
    strata: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        strata[(row.get("language", "unknown"), row.get("outcome", "unknown"), row.get("size_tercile", "unknown"))].append(row)
    counts = {stratum: len(items) for stratum, items in strata.items()}
    targets = _proportional_targets({str(key): value for key, value in counts.items()}, target)
    str_key_map = {str(key): key for key in strata}
    selected: list[dict[str, str]] = []
    for key_text, count in targets.items():
        items = list(strata[str_key_map[key_text]])
        rng.shuffle(items)
        selected.extend(items[:count])
    if len(selected) < target:
        selected_ids = {row["instance_id"] for row in selected}
        leftovers = [row for row in rows if row["instance_id"] not in selected_ids]
        rng.shuffle(leftovers)
        selected.extend(leftovers[: target - len(selected)])
    return selected[:target]


def sample_population_prs(
    frame_rows: list[dict[str, str]],
    n: int = 500,
    seed: int = 20260616,
    min_per_agent: int = 50,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    eligible = [row for row in frame_rows if row.get("eligibility") == "eligible"]
    rng = random.Random(seed)
    by_agent: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in eligible:
        by_agent[row["agent_name"]].append(row)
    targets = allocate_agent_targets(eligible, n=n, min_per_agent=min_per_agent)
    selected: list[dict[str, str]] = []
    for agent in sorted(targets):
        rows = sorted(by_agent[agent], key=lambda row: row["instance_id"])
        selected.extend(_sample_within_agent(rows, targets[agent], rng))
    selected = sorted(selected, key=lambda row: row["instance_id"])
    selected_ids = {row["instance_id"] for row in selected}
    weights = {agent: (len(by_agent[agent]) / targets[agent] if targets.get(agent) else "") for agent in by_agent}
    output_rows: list[dict[str, str]] = []
    for row in selected:
        copied = dict(row)
        copied["sampling_weight"] = f"{weights.get(row['agent_name'], ''):.6f}" if weights.get(row["agent_name"]) else ""
        output_rows.append(copied)
    report = {
        "random_seed": seed,
        "requested_sample_size": n,
        "eligible_size": len(eligible),
        "sample_size": len(output_rows),
        "shortfall": max(0, n - len(output_rows)),
        "min_per_agent": min_per_agent,
        "agent_targets": targets,
        "agent_frame_counts": dict(Counter(row["agent_name"] for row in eligible)),
        "agent_sample_counts": dict(Counter(row["agent_name"] for row in output_rows)),
        "language_sample_counts": dict(Counter(row["language"] for row in output_rows)),
        "outcome_sample_counts": dict(Counter(row["outcome"] for row in output_rows)),
        "size_tercile_sample_counts": dict(Counter(row["size_tercile"] for row in output_rows)),
        "excluded_count": len(frame_rows) - len(eligible),
        "replacement": "without_replacement",
        "fill_rules": "Minimum per available agent when feasible, then proportional allocation and within-agent stratified sampling.",
        "selected_instance_ids": sorted(selected_ids),
    }
    return output_rows, report


def _split_text_list(value: str) -> list[str]:
    text = value.strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [str(item.get("filename", item.get("path", item))) if isinstance(item, dict) else str(item) for item in parsed]
    except json.JSONDecodeError:
        pass
    return [part.strip() for part in re.split(r"[;|,\n]", text) if part.strip()]


def frame_row_to_raw_pr(row: dict[str, str]) -> dict[str, Any]:
    files = [{"filename": filename, "additions": 0, "deletions": 0} for filename in _split_text_list(row.get("files_changed", ""))]
    commits = [{"message": message} for message in _split_text_list(row.get("commit_messages", ""))]
    checks = []
    ci_status = row.get("ci_status", "")
    if ci_status:
        checks.append({"name": "metadata_ci_status", "conclusion": ci_status})
    return {
        "instance_id": row.get("instance_id", ""),
        "repo": row.get("repo", ""),
        "pr_number": _parse_int(row.get("pr_number")),
        "pr_url": row.get("pr_url", ""),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "fetch_mode": "aidev_metadata",
        "manifest_metadata": {key: row.get(key, "") for key in FRAME_COLUMNS},
        "pr": {"title": row.get("title", ""), "body": row.get("body", ""), "created_at": row.get("created_at", "")},
        "files": files,
        "commits": commits,
        "reviews": [{"body": item} for item in _split_text_list(row.get("reviews", ""))],
        "review_comments": [],
        "issue_comments": [{"body": item} for item in _split_text_list(row.get("comments", ""))],
        "checks": checks,
        "linked_issues": [],
        "errors": [],
    }


def build_population_corpus_from_metadata(sample_manifest: str | Path, out_dir: str | Path) -> dict[str, Any]:
    output = Path(out_dir)
    for child in ("raw", "dossiers", "manifests", "logs"):
        (output / child).mkdir(parents=True, exist_ok=True)
    rows = read_csv_rows(sample_manifest)
    logs = []
    valid = 0
    for row in rows:
        raw = frame_row_to_raw_pr(row)
        raw_path = output / "raw" / f"{row['instance_id']}.json"
        raw_path.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        dossier = reconstruct_dossier_from_raw(raw)
        (output / "dossiers" / f"{row['instance_id']}.json").write_text(
            json.dumps(dossier, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        valid += 1
        logs.append({"instance_id": row["instance_id"], "status": "metadata_reconstructed", "raw_path": str(raw_path)})
    write_csv_rows(output / "manifests" / "resolved_manifest.csv", rows)
    with (output / "logs" / "build_population_corpus_log.jsonl").open("w", encoding="utf-8") as f:
        for row in logs:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    summary = {
        "total_manifest_rows": len(rows),
        "reconstructed_dossiers": valid,
        "fetch_mode": "aidev_metadata",
        "warning": "Metadata-only reconstruction is conservative; use GitHub live enrichment for richer artifacts.",
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output / "summary.md").write_text(
        "\n".join(
            [
                "# Population Corpus Build",
                "",
                f"- Total manifest rows: {len(rows)}",
                f"- Reconstructed dossiers: {valid}",
                "- Fetch mode: aidev_metadata",
                "",
                summary["warning"],
                "",
            ]
        ),
        encoding="utf-8",
    )
    return summary


def run_population_corpus_pipeline(
    sample_manifest: str | Path,
    out_dir: str | Path,
    *,
    live: bool = False,
    github_token: str | None = None,
    force: bool = False,
    annotation_repeat_count: int = 50,
    seed: int = 20260616,
) -> dict[str, Any]:
    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    if live:
        build_summary = write_seed_corpus(sample_manifest, output, live=True, github_token=github_token, force=force)
    else:
        build_summary = build_population_corpus_from_metadata(sample_manifest, output)
    dossier_dir = output / "dossiers"
    reports = output / "reports"
    reports.mkdir(exist_ok=True)
    corpus_summary = summarize_corpus(dossier_dir, reports / "corpus_summary")
    provenance_summary = audit_provenance(dossier_dir, reports / "provenance_audit")
    cards_summary = make_dossier_cards(dossier_dir, reports / "dossier_cards")
    pilot_summary = run_pilot_analysis(dossier_dir, reports / "pilot_analysis")
    tasks_path = reports / "annotation_tasks.json"
    repeat_tasks_path = reports / "annotation_tasks_with_repeats.json"
    annotation_sheet_path = reports / "annotation_sheet.csv"
    tasks = export_annotation_tasks(dossier_dir, tasks_path)
    repeated = create_reliability_sample(tasks_path, repeat_tasks_path, rate=0.1, min_count=annotation_repeat_count, seed=seed)
    annotation_rows = export_annotation_csv_template(repeat_tasks_path, annotation_sheet_path, annotator_id="solo")
    summary = {
        "build_summary": build_summary,
        "corpus_summary": corpus_summary,
        "provenance_summary": provenance_summary,
        "cards_summary": {"total_cards": cards_summary["total_cards"], "invalid_dossiers": cards_summary["invalid_dossiers"]},
        "pilot_analysis_summary": pilot_summary,
        "annotation_tasks": len(tasks),
        "annotation_tasks_with_repeats": len(repeated),
        "repeat_tasks": len(repeated) - len(tasks),
        "annotation_repeat_seed": seed,
        "annotation_repeat_min_count": annotation_repeat_count,
        "annotation_sheet_csv": str(annotation_sheet_path),
        "annotation_sheet_rows": len(annotation_rows),
    }
    (reports / "population_pipeline_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return summary


def wilson_interval(successes: int, total: int, z: float = 1.96) -> dict[str, float | int | None]:
    if total <= 0:
        return {"successes": successes, "total": total, "proportion": None, "lower": None, "upper": None}
    phat = successes / total
    denom = 1 + z**2 / total
    center = (phat + z**2 / (2 * total)) / denom
    half = z * math.sqrt((phat * (1 - phat) + z**2 / (4 * total)) / total) / denom
    return {
        "successes": successes,
        "total": total,
        "proportion": round(phat, 4),
        "lower": round(max(0.0, center - half), 4),
        "upper": round(min(1.0, center + half), 4),
    }


def _weight_by_instance(sample_rows: list[dict[str, str]]) -> dict[str, float]:
    weights = {}
    for row in sample_rows:
        try:
            weights[row["instance_id"]] = float(row.get("sampling_weight") or 1.0)
        except ValueError:
            weights[row["instance_id"]] = 1.0
    return weights


def build_population_estimates(annotation_export: str | Path, sample_manifest: str | Path) -> dict[str, Any]:
    records = [record for record in parse_annotation_export(annotation_export) if not record.get("is_reliability_repeat")]
    sample_rows = read_csv_rows(sample_manifest)
    weights = _weight_by_instance(sample_rows)
    estimates: dict[str, Any] = {}
    for category in EVIDENCE_CATEGORIES:
        denominator = 0
        successes = 0
        missing = 0
        weighted_denominator = 0.0
        weighted_success = 0.0
        weighted_missing = 0.0
        label_counts: Counter[str] = Counter()
        for record in records:
            label = record.get("category_labels", {}).get(category)
            if label is None:
                continue
            label_counts[str(label)] += 1
            if label == "not_applicable":
                continue
            denominator += 1
            weight = weights.get(str(record.get("reliability_group_id") or record.get("instance_id")), 1.0)
            weighted_denominator += weight
            if label in {"present", "partially_present"}:
                successes += 1
                weighted_success += weight
            if label == "missing":
                missing += 1
                weighted_missing += weight
        interval = wilson_interval(successes, denominator)
        estimates[category] = {
            "eligible_records": denominator,
            "positive_records": successes,
            "missing_records": missing,
            "coverage_rate": interval["proportion"],
            "coverage_ci_lower": interval["lower"],
            "coverage_ci_upper": interval["upper"],
            "missing_rate": round(missing / denominator, 4) if denominator else None,
            "weighted_coverage_rate": round(weighted_success / weighted_denominator, 4) if weighted_denominator else None,
            "weighted_missing_rate": round(weighted_missing / weighted_denominator, 4) if weighted_denominator else None,
            "label_counts": {label: label_counts.get(label, 0) for label in ("present", "partially_present", "missing", "not_applicable")},
        }
    return {
        "population_frame": "AIDev curated public agentic-PR frame",
        "annotation_records": len(records),
        "sample_manifest_rows": len(sample_rows),
        "category_estimates": estimates,
        "interpretation": (
            "Population estimates are limited to the declared sampling frame and single-operator audit codes. "
            "They are not AI-vs-human causal effects or reviewer-utility results."
        ),
    }


def build_availability_sensitivity(annotation_export: str | Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Compute main/strict/conservative availability from primary audit codes."""
    records = [record for record in parse_annotation_export(annotation_export) if not record.get("is_reliability_repeat")]
    rows: list[dict[str, Any]] = []
    for category in EVIDENCE_CATEGORIES:
        label_counts: Counter[str] = Counter()
        for record in records:
            label = record.get("category_labels", {}).get(category)
            if label is not None:
                label_counts[str(label)] += 1
        denominator = label_counts["present"] + label_counts["partially_present"] + label_counts["missing"]
        present = label_counts["present"]
        partial = label_counts["partially_present"]
        missing = label_counts["missing"]
        main_positive = present + partial
        strict_positive = present
        rows.append(
            {
                "category": category,
                "eligible_records": denominator,
                "present_count": present,
                "partial_count": partial,
                "missing_count": missing,
                "not_applicable_count": label_counts["not_applicable"],
                "availability_main": round(main_positive / denominator, 4) if denominator else None,
                "availability_strict": round(strict_positive / denominator, 4) if denominator else None,
                "availability_conservative": round(strict_positive / denominator, 4) if denominator else None,
                "missing_main": round(missing / denominator, 4) if denominator else None,
                "missing_strict": round((missing + partial) / denominator, 4) if denominator else None,
                "missing_conservative": round((missing + partial) / denominator, 4) if denominator else None,
            }
        )

    handoff_critical = {"trace_evidence", "regression_evidence", "rationale_evidence", "ownership_handoff", "risk_analysis"}
    robustly_high = [
        row["category"]
        for row in rows
        if row["availability_main"] is not None and row["availability_main"] >= 0.8 and row["availability_strict"] >= 0.8
    ]
    robustly_low = [
        row["category"]
        for row in rows
        if row["availability_main"] is not None and row["availability_main"] < 0.5 and row["availability_strict"] < 0.5
    ]
    sensitive_to_partial = [
        row["category"]
        for row in rows
        if row["availability_main"] is not None
        and row["availability_main"] >= 0.5
        and row["availability_strict"] < 0.5
    ]
    strict_low = {row["category"] for row in rows if row["availability_strict"] is not None and row["availability_strict"] < 0.5}
    handoff_gap_remains = handoff_critical.issubset(strict_low)
    summary = {
        "construct": "Review-Evidence Availability",
        "annotation_records": len(records),
        "main_rule": "present + partially_present counted positive",
        "strict_rule": "only present counted positive",
        "conservative_rule": "partially_present counted missing",
        "robustly_high_categories": robustly_high,
        "robustly_low_categories": robustly_low,
        "partial_sensitive_categories": sensitive_to_partial,
        "handoff_critical_gap_remains_under_strict_coding": handoff_gap_remains,
        "interpretation": (
            "The handoff-critical evidence gap remains under stricter treatment of partial evidence."
            if handoff_gap_remains
            else "The handoff-critical evidence-gap pattern changes under strict coding; inspect category rows."
        ),
    }
    return rows, summary


def _default_population_dossier_dir() -> Path | None:
    root = Path(__file__).resolve().parents[2]
    candidate = root / "outputs" / "population_ai_pr_500_20260616" / "dossiers"
    return candidate if candidate.exists() else None


def build_provenance_paper_tables(dossiers: str | Path | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Build paper-facing provenance status and source-type tables."""
    root = Path(__file__).resolve().parents[2]
    dossier_path = Path(dossiers) if dossiers is not None else _default_population_dossier_dir()
    valid: list[dict[str, Any]] = []
    invalid_rows: list[dict[str, Any]] = []
    if dossier_path is not None and dossier_path.exists():
        for source, dossier, load_error in iter_dossier_inputs(dossier_path):
            if load_error is not None or dossier is None:
                invalid_rows.append({"source": source, "error": load_error or "missing dossier"})
                continue
            errors = validate_data(dossier, "dossier")
            if errors:
                invalid_rows.append({"source": source, "error": errors[0]})
                continue
            valid.append(dossier)

    status_rows: list[dict[str, Any]] = []
    source_rows: list[dict[str, Any]] = []
    for category in PROVENANCE_CATEGORIES:
        status_counts: Counter[str] = Counter()
        source_counts: Counter[str] = Counter()
        for dossier in valid:
            records = collect_provenance(dossier).get(category, [])
            if not records:
                status_counts["missing"] += 1
                continue
            for record in records:
                status = str(record.get("status", "missing"))
                status_counts[status if status in {"observed", "inferred", "missing", "not_applicable"} else "missing"] += 1
                source_type = str(record.get("source_type", "unknown") or "unknown")
                source_counts[source_type if source_type in PROVENANCE_SOURCE_TYPES else "unknown"] += 1
        status_rows.append(
            {
                "category": category,
                "observed": status_counts.get("observed", 0),
                "inferred": status_counts.get("inferred", 0),
                "missing": status_counts.get("missing", 0),
                "not_applicable": status_counts.get("not_applicable", 0),
            }
        )
        for source_type in PROVENANCE_SOURCE_TYPES:
            count = source_counts.get(source_type, 0)
            if count:
                source_rows.append({"category": category, "source_type": source_type, "count": count})

    if dossier_path is not None:
        try:
            source_text = str(dossier_path.relative_to(root))
        except ValueError:
            source_text = str(dossier_path)
    else:
        source_text = None
    summary = {
        "dossier_source": source_text,
        "valid_dossiers": len(valid),
        "invalid_dossiers": len(invalid_rows),
        "invalid_rows": invalid_rows[:20],
        "interpretation": (
            "Provenance rows summarize inspectable evidence sources and reconstruction status; they do not establish "
            "patch correctness, mergeability, reviewer utility, or inter-rater reliability."
        ),
    }
    if dossier_path is None or not dossier_path.exists():
        summary["warning"] = "No dossier directory was available; provenance tables were emitted with zero counts."
    return status_rows, source_rows, summary


def write_claims_nonclaims_tables(output: Path) -> None:
    rows = [{"claim": claim, "non_claim": nonclaim} for claim, nonclaim in CLAIMS_NONCLAIMS]
    write_csv_rows(output / "paper_table_claims_nonclaims.csv", rows, ["claim", "non_claim"])
    (output / "paper_table_claims_nonclaims.md").write_text(
        "\n".join(
            [
                "# Claims and Non-Claims",
                "",
                markdown_table(["This paper estimates", "This paper does not estimate"], [[row["claim"], row["non_claim"]] for row in rows]),
                "",
            ]
        ),
        encoding="utf-8",
    )
    tex_lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Claims and non-claims for review-evidence availability measurement.}",
        r"\label{tab:claims-nonclaims}",
        r"\footnotesize",
        r"\begin{tabular}{@{}p{0.44\columnwidth}p{0.44\columnwidth}@{}}",
        r"\toprule",
        r"This paper estimates & This paper does not estimate \\",
        r"\midrule",
    ]
    for row in rows:
        tex_lines.append(f"{_tex(row['claim'])} & {_tex(row['non_claim'])} \\\\")
    tex_lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    (output / "paper_table_claims_nonclaims.tex").write_text("\n".join(tex_lines), encoding="utf-8")


def compact_sensitivity_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return the eight paper-facing sensitivity rows used in the manuscript."""
    by_category = {row["category"]: row for row in rows}
    compact_rows: list[dict[str, Any]] = []
    for category, family, note in COMPACT_SENSITIVITY_CATEGORIES:
        row = by_category.get(category, {})
        compact_rows.append(
            {
                "family": family,
                "category": category,
                "availability_main": row.get("availability_main"),
                "availability_strict": row.get("availability_strict"),
                "availability_conservative": row.get("availability_conservative"),
                "note": note,
            }
        )
    return compact_rows


def compact_provenance_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return the eight paper-facing provenance rows used in the manuscript."""
    by_category = {row["category"]: row for row in rows}
    compact_rows: list[dict[str, Any]] = []
    for category, family, audit_note in COMPACT_PROVENANCE_CATEGORIES:
        row = by_category.get(category, {})
        compact_rows.append(
            {
                "family": family,
                "category": category,
                "observed": row.get("observed", 0),
                "inferred": row.get("inferred", 0),
                "missing": row.get("missing", 0),
                "not_applicable": row.get("not_applicable", 0),
                "audit_note": audit_note,
            }
        )
    return compact_rows


def availability_interval_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compute per-family availability intervals from sensitivity rows."""
    by_category = {row["category"]: row for row in rows}
    interval_rows: list[dict[str, Any]] = []
    for category, family, family_set in AVAILABILITY_INTERVAL_CATEGORIES:
        row = by_category.get(category, {})
        denominator = int(row.get("eligible_records") or 0)
        present = int(row.get("present_count") or 0)
        partial = int(row.get("partial_count") or 0)
        missing = int(row.get("missing_count") or 0)
        lower = round(present / denominator, 4) if denominator else None
        upper = round((present + partial) / denominator, 4) if denominator else None
        interval_rows.append(
            {
                "family": family,
                "category": category,
                "set": family_set,
                "applicable_records": denominator,
                "present_count": present,
                "partial_count": partial,
                "missing_count": missing,
                "availability_lower": lower,
                "availability_upper": upper,
            }
        )
    return interval_rows


def handoff_gap_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Compute HEA, HEG, core availability, and minimum separation."""
    intervals = {row["category"]: row for row in availability_interval_rows(rows)}

    def average(categories: tuple[str, ...], key: str) -> float:
        values = [float(intervals[category][key]) for category in categories if intervals[category][key] is not None]
        return round(sum(values) / len(values), 4) if values else 0.0

    hea_lower = average(HANDOFF_EVIDENCE_CATEGORIES, "availability_lower")
    hea_upper = average(HANDOFF_EVIDENCE_CATEGORIES, "availability_upper")
    heg_lower = round(1 - hea_upper, 4)
    heg_upper = round(1 - hea_lower, 4)
    core_lower = average(CORE_EVIDENCE_CATEGORIES, "availability_lower")
    core_upper = average(CORE_EVIDENCE_CATEGORIES, "availability_upper")
    separation_min = round(core_lower - hea_upper, 4)
    rows_out = [
        {
            "metric": "Core evidence availability",
            "lower": core_lower,
            "upper": core_upper,
            "value": "",
            "unit": "proportion",
            "interpretation": "Intent, Test, and Scope availability interval.",
        },
        {
            "metric": "Handoff Evidence Availability",
            "lower": hea_lower,
            "upper": hea_upper,
            "value": "",
            "unit": "proportion",
            "interpretation": "Average availability interval over Risk, Trace, Regression, Rationale, and Ownership.",
        },
        {
            "metric": "Handoff-Evidence Gap",
            "lower": heg_lower,
            "upper": heg_upper,
            "value": "",
            "unit": "proportion",
            "interpretation": "One minus handoff evidence availability.",
        },
        {
            "metric": "Minimum robust separation",
            "lower": "",
            "upper": "",
            "value": separation_min,
            "unit": "percentage points",
            "interpretation": "Core strict lower bound minus handoff lenient upper bound.",
        },
    ]
    summary = {
        "core_categories": list(CORE_EVIDENCE_CATEGORIES),
        "handoff_categories": list(HANDOFF_EVIDENCE_CATEGORIES),
        "core_availability_interval": [core_lower, core_upper],
        "handoff_evidence_availability_interval": [hea_lower, hea_upper],
        "handoff_evidence_gap_interval": [heg_lower, heg_upper],
        "minimum_robust_separation": separation_min,
        "interpretation": (
            "Surface/core evidence remains separated from handoff-critical evidence even under strict coding for core "
            "categories and lenient coding for handoff categories."
        ),
    }
    return rows_out, summary


def tipping_point_rows(rows: list[dict[str, Any]], threshold: float = TIPPING_POINT_THRESHOLD) -> list[dict[str, Any]]:
    """Compute flips needed for handoff categories to reach a target availability."""
    by_category = {row["category"]: row for row in rows}
    family_names = {category: family for category, family, _ in AVAILABILITY_INTERVAL_CATEGORIES}
    out_rows: list[dict[str, Any]] = []
    for category in HANDOFF_EVIDENCE_CATEGORIES:
        row = by_category.get(category, {})
        denominator = int(row.get("eligible_records") or 0)
        present = int(row.get("present_count") or 0)
        partial = int(row.get("partial_count") or 0)
        positive = present + partial
        required = math.ceil(threshold * denominator) if denominator else 0
        flips = max(0, required - positive)
        out_rows.append(
            {
                "family": family_names[category],
                "category": category,
                "threshold": threshold,
                "applicable_records": denominator,
                "positive_count": positive,
                "required_positive_count": required,
                "flips_needed": flips,
                "current_availability": round(positive / denominator, 4) if denominator else None,
            }
        )
    return out_rows


def write_population_results(annotation_export: str | Path, sample_manifest: str | Path, out_dir: str | Path) -> dict[str, Any]:
    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    summary = build_population_estimates(annotation_export, sample_manifest)
    sensitivity_rows, sensitivity_summary = build_availability_sensitivity(annotation_export)
    provenance_rows, source_type_rows, provenance_summary = build_provenance_paper_tables()
    compact_sensitivity = compact_sensitivity_rows(sensitivity_rows)
    compact_provenance = compact_provenance_rows(provenance_rows)
    interval_rows = availability_interval_rows(sensitivity_rows)
    handoff_rows, handoff_summary = handoff_gap_rows(sensitivity_rows)
    tipping_rows = tipping_point_rows(sensitivity_rows)
    summary["sensitivity_summary"] = sensitivity_summary
    summary["provenance_status_summary"] = provenance_summary
    summary["handoff_gap_summary"] = handoff_summary
    (output / "population_estimates.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    rows = []
    for category, values in summary["category_estimates"].items():
        row = {"category": category, **{key: value for key, value in values.items() if key != "label_counts"}}
        rows.append(row)
    fieldnames = [
        "category",
        "eligible_records",
        "positive_records",
        "missing_records",
        "coverage_rate",
        "coverage_ci_lower",
        "coverage_ci_upper",
        "missing_rate",
        "weighted_coverage_rate",
        "weighted_missing_rate",
    ]
    write_csv_rows(output / "population_category_estimates.csv", rows, fieldnames)
    sensitivity_fields = [
        "category",
        "eligible_records",
        "present_count",
        "partial_count",
        "missing_count",
        "not_applicable_count",
        "availability_main",
        "availability_strict",
        "availability_conservative",
        "missing_main",
        "missing_strict",
        "missing_conservative",
    ]
    write_csv_rows(output / "paper_table_sensitivity_by_category.csv", sensitivity_rows, sensitivity_fields)
    write_csv_rows(
        output / "paper_table_provenance_by_category.csv",
        provenance_rows,
        ["category", "observed", "inferred", "missing", "not_applicable"],
    )
    write_csv_rows(
        output / "paper_table_source_type_by_category.csv",
        source_type_rows,
        ["category", "source_type", "count"],
    )
    write_csv_rows(
        output / "paper_table_sensitivity_compact.csv",
        compact_sensitivity,
        ["family", "category", "availability_main", "availability_strict", "availability_conservative", "note"],
    )
    write_csv_rows(
        output / "paper_table_provenance_compact.csv",
        compact_provenance,
        ["family", "category", "observed", "inferred", "missing", "not_applicable", "audit_note"],
    )
    write_csv_rows(
        output / "paper_table_availability_intervals.csv",
        interval_rows,
        [
            "family",
            "category",
            "set",
            "applicable_records",
            "present_count",
            "partial_count",
            "missing_count",
            "availability_lower",
            "availability_upper",
        ],
    )
    write_csv_rows(
        output / "paper_table_handoff_gap.csv",
        handoff_rows,
        ["metric", "lower", "upper", "value", "unit", "interpretation"],
    )
    write_csv_rows(
        output / "paper_table_tipping_point.csv",
        tipping_rows,
        [
            "family",
            "category",
            "threshold",
            "applicable_records",
            "positive_count",
            "required_positive_count",
            "flips_needed",
            "current_availability",
        ],
    )
    (output / "sensitivity_summary.json").write_text(json.dumps(sensitivity_summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    sensitivity_md_rows = [
        [
            row["category"],
            _pct(row["availability_main"]),
            _pct(row["availability_strict"]),
            _pct(row["availability_conservative"]),
            _pct(row["missing_conservative"]),
        ]
        for row in sensitivity_rows
    ]
    (output / "sensitivity_summary.md").write_text(
        "\n".join(
            [
                "# Review-Evidence Availability Sensitivity",
                "",
                sensitivity_summary["interpretation"],
                "",
                f"- Main rule: {sensitivity_summary['main_rule']}",
                f"- Strict rule: {sensitivity_summary['strict_rule']}",
                f"- Conservative rule: {sensitivity_summary['conservative_rule']}",
                f"- Robustly high categories: {', '.join(sensitivity_summary['robustly_high_categories']) or 'none'}",
                f"- Robustly low categories: {', '.join(sensitivity_summary['robustly_low_categories']) or 'none'}",
                f"- Partial-sensitive categories: {', '.join(sensitivity_summary['partial_sensitive_categories']) or 'none'}",
                "",
                markdown_table(["category", "main", "strict", "conservative", "conservative missing"], sensitivity_md_rows),
                "",
            ]
        ),
        encoding="utf-8",
    )
    provenance_md_rows = [
        [row["category"], row["observed"], row["inferred"], row["missing"], row["not_applicable"]]
        for row in provenance_rows
    ]
    source_md_rows = [[row["category"], row["source_type"], row["count"]] for row in source_type_rows[:40]]
    (output / "provenance_status_summary.md").write_text(
        "\n".join(
            [
                "# Provenance Status Summary",
                "",
                provenance_summary["interpretation"],
                "",
                f"- Dossier source: {provenance_summary.get('dossier_source') or 'unavailable'}",
                f"- Valid dossiers: {provenance_summary['valid_dossiers']}",
                f"- Invalid dossiers: {provenance_summary['invalid_dossiers']}",
                "",
                "## Status By Category",
                "",
                markdown_table(["category", "observed", "inferred", "missing", "not_applicable"], provenance_md_rows),
                "",
                "## Source Types By Category",
                "",
                markdown_table(["category", "source_type", "count"], source_md_rows) if source_md_rows else "_No provenance source-type rows._",
                "",
            ]
        ),
        encoding="utf-8",
    )
    write_claims_nonclaims_tables(output)
    md_rows = [
        [
            row["category"],
            row["eligible_records"],
            row["coverage_rate"],
            f"{row['coverage_ci_lower']}--{row['coverage_ci_upper']}",
            row["weighted_coverage_rate"],
            row["missing_rate"],
        ]
        for row in rows
    ]
    (output / "population_results.md").write_text(
        "\n".join(
            [
                "# Population Evidence Estimates",
                "",
                summary["interpretation"],
                "",
                f"- Sampling frame: {summary['population_frame']}",
                f"- Primary annotation records: {summary['annotation_records']}",
                "",
                markdown_table(
                    ["category", "n", "coverage", "Wilson 95% CI", "weighted coverage", "missing"],
                    md_rows,
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )
    tex_lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Population-frame evidence coverage estimates.}",
        r"\label{tab:population-evidence-estimates}",
        r"\footnotesize",
        r"\begin{tabular}{@{}lrrrr@{}}",
        r"\toprule",
        r"Category & $n$ & Coverage & 95\% CI & Missing \\",
        r"\midrule",
    ]
    for row in rows:
        tex_lines.append(
            f"{row['category'].replace('_', r'\_')} & {row['eligible_records']} & "
            f"{_pct(row['coverage_rate'])} & {_pct(row['coverage_ci_lower'])}--{_pct(row['coverage_ci_upper'])} & "
            f"{_pct(row['missing_rate'])} \\\\"
        )
    tex_lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    (output / "population_evidence_estimates_table.tex").write_text("\n".join(tex_lines), encoding="utf-8")
    _write_sensitivity_tex(output / "paper_table_sensitivity_by_category.tex", sensitivity_rows)
    _write_provenance_tex(output / "paper_table_provenance_by_category.tex", provenance_rows)
    _write_source_type_tex(output / "paper_table_source_type_by_category.tex", source_type_rows)
    _write_compact_sensitivity_tex(output / "paper_table_sensitivity_compact.tex", compact_sensitivity)
    _write_compact_provenance_tex(output / "paper_table_provenance_compact.tex", compact_provenance)
    _write_availability_intervals_tex(output / "paper_table_availability_intervals.tex", interval_rows)
    _write_handoff_gap_tex(output / "paper_table_handoff_gap.tex", handoff_rows)
    _write_tipping_point_tex(output / "paper_table_tipping_point.tex", tipping_rows)
    return summary


def _pct(value: Any) -> str:
    if value is None or value == "":
        return "--"
    return f"{float(value) * 100:.1f}\\%"


def _pct2(value: Any) -> str:
    if value is None or value == "":
        return "--"
    return f"{float(value) * 100:.2f}\\%"


def _tex(value: Any) -> str:
    return str(value).replace("\\", r"\textbackslash{}").replace("&", r"\&").replace("_", r"\_").replace("%", r"\%")


def _write_sensitivity_tex(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Review-evidence availability sensitivity by category.}",
        r"\label{tab:availability-sensitivity}",
        r"\footnotesize",
        r"\begin{tabular}{@{}lrrrr@{}}",
        r"\toprule",
        r"Category & $n$ & Main & Strict & Conservative \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            f"{_tex(row['category'])} & {row['eligible_records']} & {_pct(row['availability_main'])} & "
            f"{_pct(row['availability_strict'])} & {_pct(row['availability_conservative'])} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_provenance_tex(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Provenance status by evidence category.}",
        r"\label{tab:provenance-by-category}",
        r"\footnotesize",
        r"\begin{tabular}{@{}lrrrr@{}}",
        r"\toprule",
        r"Category & Observed & Inferred & Missing & N/A \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            f"{_tex(row['category'])} & {row['observed']} & {row['inferred']} & {row['missing']} & {row['not_applicable']} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_compact_sensitivity_tex(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Compact sensitivity check for review-evidence availability.}",
        r"\label{tab:availability-sensitivity-compact}",
        r"\footnotesize",
        r"\begin{tabular}{@{}lrrrl@{}}",
        r"\toprule",
        r"Family & Main & Strict & Cons. & Note \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            f"{_tex(row['family'])} & {_pct(row['availability_main'])} & "
            f"{_pct(row['availability_strict'])} & {_pct(row['availability_conservative'])} & "
            f"{_tex(row['note'])} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_compact_provenance_tex(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Compact provenance-status check for the result categories.}",
        r"\label{tab:provenance-compact}",
        r"\footnotesize",
        r"\begin{tabular}{@{}lrrrr@{}}",
        r"\toprule",
        r"Family & Obs. & Inf. & Miss. & N/A \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            f"{_tex(row['family'])} & {row['observed']} & {row['inferred']} & "
            f"{row['missing']} & {row['not_applicable']} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def _interval_pct(lower: Any, upper: Any) -> str:
    if lower in (None, "") or upper in (None, ""):
        return "--"
    return f"[{_pct(lower)}, {_pct(upper)}]"


def _interval_pct2(lower: Any, upper: Any) -> str:
    if lower in (None, "") or upper in (None, ""):
        return "--"
    return f"[{_pct2(lower)}, {_pct2(upper)}]"


def _write_availability_intervals_tex(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Availability intervals by evidence family. Partial evidence is treated as threshold uncertainty.}",
        r"\label{tab:availability-intervals}",
        r"\footnotesize",
        r"\begin{tabular}{@{}L{0.25\columnwidth}L{0.17\columnwidth}rL{0.31\columnwidth}@{}}",
        r"\toprule",
        r"Family & Set & $n$ & Interval \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            f"{_tex(row['family'])} & {_tex(row['set'])} & {row['applicable_records']} & "
            f"{_interval_pct(row['availability_lower'], row['availability_upper'])} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_handoff_gap_tex(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Handoff-evidence gap and robust separation.}",
        r"\label{tab:handoff-gap}",
        r"\footnotesize",
        r"\begin{tabular}{@{}L{0.48\columnwidth}L{0.42\columnwidth}@{}}",
        r"\toprule",
        r"Quantity & Estimate \\",
        r"\midrule",
    ]
    for row in rows:
        if row.get("value") not in (None, ""):
            estimate = f"{float(row['value']) * 100:.2f} pp"
        else:
            estimate = _interval_pct2(row.get("lower"), row.get("upper"))
        lines.append(f"{_tex(row['metric'])} & {estimate} \\\\")
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_tipping_point_tex(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Tipping-point analysis for handoff-critical evidence at $\tau=0.5$.}",
        r"\label{tab:tipping-point}",
        r"\footnotesize",
        r"\begin{tabular}{@{}L{0.31\columnwidth}rrr@{}}",
        r"\toprule",
        r"Family & Positive & Required & Flips \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            f"{_tex(row['family'])} & {row['positive_count']} & "
            f"{row['required_positive_count']} & {row['flips_needed']} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_source_type_tex(path: Path, rows: list[dict[str, Any]]) -> None:
    top_rows = sorted(rows, key=lambda row: int(row.get("count", 0)), reverse=True)[:20]
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Top provenance source types by evidence category.}",
        r"\label{tab:source-type-by-category}",
        r"\footnotesize",
        r"\begin{tabular}{@{}llr@{}}",
        r"\toprule",
        r"Category & Source type & Count \\",
        r"\midrule",
    ]
    for row in top_rows:
        lines.append(f"{_tex(row['category'])} & {_tex(row['source_type'])} & {row['count']} \\\\")
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")
