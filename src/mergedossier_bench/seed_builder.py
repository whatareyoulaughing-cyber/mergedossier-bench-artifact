"""Offline-first seed corpus builder for MergeDossier-Bench."""

from __future__ import annotations

import csv
import json
import os
import re
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .github_miner import GitHubClient
from .provenance import make_provenance_record
from .schema import EVIDENCE_TYPES
from .validators import load_json, validate_data

MANIFEST_COLUMNS: tuple[str, ...] = (
    "instance_id",
    "repo",
    "pr_number",
    "pr_url",
    "source",
    "author_type",
    "agent_name",
    "task_type",
    "language",
    "outcome",
    "sample_split",
    "notes",
)

ALLOWED_VALUES: dict[str, set[str]] = {
    "author_type": {"ai_authored", "human_authored", "mixed", "unknown"},
    "agent_name": {"codex", "claude_code", "copilot", "cursor", "devin", "aider", "human", "unknown"},
    "task_type": {"bug_fix", "feature", "refactor", "test", "docs", "dependency", "unknown"},
    "outcome": {"merged", "closed_unmerged", "open", "unknown"},
    "sample_split": {"pilot", "train", "dev", "test"},
}

RISK_TERMS = ("risk", "breaking", "compatibility", "security", "migration", "rollback", "regression risk")
TRACE_TERMS = ("agent trace", "tool log", "command log", "commands run", "reasoning summary")
LIMITATION_TERMS = ("limitation", "known gap", "follow-up", "todo", "partial", "constraint")
OWNERSHIP_TERMS = ("owner", "rollout", "monitoring", "manual step", "follow-up responsibility", "handoff", "rollback")
REVIEWER_TERMS = ("reviewer", "please verify", "validation step", "test command", "run pytest", "inspect")
RATIONALE_TERMS = ("rationale", "design", "approach", "why", "implementation notes", "tradeoff", "alternative")
DEPENDENCY_FILES = (
    "package.json",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "requirements.txt",
    "pyproject.toml",
    "poetry.lock",
    "pom.xml",
    "build.gradle",
    "cargo.toml",
    "cargo.lock",
    "go.mod",
    "go.sum",
    "gemfile",
    "gemfile.lock",
)


def load_seed_manifest(path: str | Path) -> list[dict[str, str]]:
    """Load a seed PR CSV manifest."""
    with Path(path).open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return [{key: (row.get(key) or "").strip() for key in MANIFEST_COLUMNS} for row in reader]


def validate_seed_manifest(rows: list[dict[str, str]]) -> list[str]:
    """Validate required columns, unique instance IDs, and controlled values."""
    errors: list[str] = []
    seen: set[str] = set()
    for index, row in enumerate(rows, start=1):
        for column in MANIFEST_COLUMNS:
            if column not in row:
                errors.append(f"row {index}: missing column {column}")
        instance_id = row.get("instance_id", "")
        if not instance_id:
            errors.append(f"row {index}: missing instance_id")
        elif instance_id in seen:
            errors.append(f"row {index}: duplicate instance_id {instance_id}")
        seen.add(instance_id)
        for column, allowed in ALLOWED_VALUES.items():
            value = row.get(column, "")
            if value and value not in allowed:
                errors.append(f"row {index}: invalid {column}={value!r}; expected one of {sorted(allowed)}")
    return errors


def lint_seed_manifest(rows: list[dict[str, str]]) -> dict[str, list[str]]:
    """Lint a seed manifest and separate blocking errors from warnings."""
    errors = validate_seed_manifest(rows)
    warnings: list[str] = []
    seen: set[str] = set()
    for index, row in enumerate(rows, start=1):
        instance_id = row.get("instance_id", "")
        if instance_id in seen:
            continue
        seen.add(instance_id)
        repo = row.get("repo", "")
        pr_number = row.get("pr_number", "")
        pr_url = row.get("pr_url", "")
        if repo and not re.match(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", repo):
            errors.append(f"row {index}: repo must look like owner/name")
        if pr_number:
            try:
                int(pr_number)
            except ValueError:
                errors.append(f"row {index}: pr_number must be an integer")
        if pr_url and not re.match(r"^https?://[^/]+/.+/.+/pull/\d+", pr_url):
            errors.append(f"row {index}: pr_url is not parseable as a pull request URL")
        if not ((repo and pr_number) or pr_url):
            errors.append(f"row {index}: either repo+pr_number or pr_url is required")
        if row.get("author_type") == "unknown":
            warnings.append(f"row {index}: author_type is unknown")
        if row.get("agent_name") == "unknown":
            warnings.append(f"row {index}: agent_name is unknown")
        if row.get("author_type") in {"unknown", "mixed"} and not row.get("notes"):
            warnings.append(f"row {index}: ambiguous authorship should include notes")
    return {"errors": errors, "warnings": warnings}


def load_fixture_raw_pr(fixture_dir: str | Path, manifest_row: dict[str, str]) -> dict[str, Any]:
    """Load a synthetic raw PR fixture matching a manifest instance_id."""
    fixture_path = Path(fixture_dir) / f"{manifest_row['instance_id']}.json"
    raw = load_json(fixture_path)
    raw["manifest_metadata"] = {**manifest_row, **raw.get("manifest_metadata", {})}
    return raw


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _pr_url(row: dict[str, str]) -> str:
    if row.get("pr_url"):
        return row["pr_url"]
    if row.get("repo") and row.get("pr_number"):
        return f"https://github.com/{row['repo']}/pull/{row['pr_number']}"
    return ""


def _result_data(result: dict[str, Any], default: Any) -> Any:
    if result.get("ok"):
        return result.get("data", default)
    return default


def _collect_errors(endpoint: str, result: dict[str, Any]) -> list[dict[str, Any]]:
    if "errors" in result:
        return [dict(error, endpoint=error.get("endpoint", endpoint)) for error in result.get("errors", []) if error]
    error = result.get("error")
    return [dict(error, endpoint=error.get("endpoint", endpoint))] if error else []


def fetch_live_raw_pr(
    manifest_row: dict[str, str],
    client: GitHubClient,
    sleep_seconds: float = 0.0,
) -> dict[str, Any]:
    """Fetch live GitHub PR artifacts into the raw PR schema shape."""
    repo = manifest_row["repo"]
    pr_number = manifest_row["pr_number"]
    errors: list[dict[str, Any]] = []

    pr_result = client.fetch_pull_request(repo, pr_number)
    errors.extend(_collect_errors("pull_request", pr_result))
    pr = _result_data(pr_result, {})
    if sleep_seconds:
        time.sleep(sleep_seconds)

    commits_result = client.fetch_pull_commits(repo, pr_number)
    errors.extend(_collect_errors("commits", commits_result))
    if sleep_seconds:
        time.sleep(sleep_seconds)

    files_result = client.fetch_pull_files(repo, pr_number)
    errors.extend(_collect_errors("files", files_result))
    if sleep_seconds:
        time.sleep(sleep_seconds)

    reviews_result = client.fetch_pull_reviews(repo, pr_number)
    errors.extend(_collect_errors("reviews", reviews_result))
    review_comments_result = client.fetch_pull_review_comments(repo, pr_number)
    errors.extend(_collect_errors("review_comments", review_comments_result))

    issue_comments_result = client.fetch_issue_comments(repo, pr_number)
    errors.extend(_collect_errors("issue_comments", issue_comments_result))
    issue_comments = _result_data(issue_comments_result, [])

    linked_result = client.fetch_linked_issues_best_effort(repo, str(pr.get("body", "") if isinstance(pr, dict) else ""), issue_comments)
    errors.extend(_collect_errors("linked_issues", linked_result))

    head_sha = ""
    if isinstance(pr, dict):
        head_sha = str((pr.get("head") or {}).get("sha", "") if isinstance(pr.get("head"), dict) else "")
    checks: list[dict[str, Any]] = []
    if head_sha:
        check_result = client.fetch_check_runs(repo, head_sha)
        errors.extend(_collect_errors("check_runs", check_result))
        for check in _result_data(check_result, []):
            if isinstance(check, dict):
                checks.append({**check, "metadata_source": "check_run"})
        status_result = client.fetch_statuses(repo, head_sha)
        errors.extend(_collect_errors("statuses", status_result))
        for status in _result_data(status_result, []):
            if isinstance(status, dict):
                checks.append({**status, "name": status.get("context", ""), "conclusion": status.get("state", ""), "metadata_source": "commit_status"})

    return {
        "instance_id": manifest_row["instance_id"],
        "repo": repo,
        "pr_number": int(pr_number) if str(pr_number).isdigit() else pr_number,
        "pr_url": _pr_url(manifest_row),
        "fetched_at": _now_iso(),
        "fetch_mode": "live",
        "manifest_metadata": manifest_row,
        "pr": pr if isinstance(pr, dict) else {},
        "commits": _result_data(commits_result, []),
        "files": _result_data(files_result, []),
        "reviews": _result_data(reviews_result, []),
        "review_comments": _result_data(review_comments_result, []),
        "issue_comments": issue_comments,
        "checks": checks,
        "linked_issues": _result_data(linked_result, []),
        "errors": errors,
    }


def _all_text(raw_pr: dict[str, Any]) -> str:
    parts: list[str] = []
    pr = raw_pr.get("pr", {})
    if isinstance(pr, dict):
        parts.extend(str(pr.get(key, "")) for key in ("title", "body"))
    for key in ("reviews", "review_comments", "issue_comments", "linked_issues"):
        for item in raw_pr.get(key, []) or []:
            if isinstance(item, dict):
                parts.extend(str(item.get(field, "")) for field in ("title", "body", "comment", "summary"))
    return "\n".join(part for part in parts if part)


def _grounding(artifact_type: str, reference: str, excerpt: str = "") -> list[dict[str, str]]:
    item = {"artifact_type": artifact_type, "reference": reference}
    if excerpt:
        item["excerpt"] = excerpt[:240]
    return [item]


def _evidence(present: bool, quality: int, claim: str, grounding: list[dict[str, str]], notes: str) -> dict[str, Any]:
    return {"present": present, "quality": quality, "claim": claim, "grounding": grounding, "notes": notes}


def _missing(notes: str) -> dict[str, Any]:
    return _evidence(False, 0, "", [], notes)


def _files(raw_pr: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in raw_pr.get("files", []) or [] if isinstance(item, dict)]


def _checks(raw_pr: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in raw_pr.get("checks", []) or [] if isinstance(item, dict)]


def _commits(raw_pr: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in raw_pr.get("commits", []) or [] if isinstance(item, dict)]


def _has_terms(text: str, terms: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in terms)


def _file_summary(files: list[dict[str, Any]]) -> str:
    if not files:
        return "No changed file metadata available."
    names = [str(item.get("filename", "UNKNOWN")) for item in files]
    additions = sum(int(item.get("additions", 0) or 0) for item in files)
    deletions = sum(int(item.get("deletions", 0) or 0) for item in files)
    return f"{len(files)} files changed (+{additions}/-{deletions}): " + ", ".join(names[:8])


def _touched_dirs(files: list[dict[str, Any]]) -> list[str]:
    dirs = sorted({str(item.get("filename", "")).split("/")[0] for item in files if "/" in str(item.get("filename", ""))})
    return [item for item in dirs if item]


def _extract_pr_reference(body: str) -> bool:
    return bool(re.search(r"(fixes|closes|resolves)\s+#\d+|#\d+", body, flags=re.IGNORECASE))


def _prov(
    status: str,
    source_type: str,
    extraction_rule: str,
    confidence: str,
    excerpt: str = "",
    notes: str = "",
    source_url: str | None = None,
) -> list[dict[str, Any]]:
    return [
        make_provenance_record(
            status,
            source_type,
            extraction_rule,
            confidence,
            source_url=source_url,
            excerpt=excerpt or None,
            notes=notes or None,
        )
    ]


def _missing_prov(extraction_rule: str, notes: str) -> list[dict[str, Any]]:
    return _prov("missing", "heuristic", extraction_rule, "high", notes=notes)


def _file_names(files: list[dict[str, Any]]) -> list[str]:
    return [str(item.get("filename", "")) for item in files if item.get("filename")]


def _is_dependency_file(filename: str) -> bool:
    normalized = filename.lower().replace("\\", "/").split("/")[-1]
    return normalized in DEPENDENCY_FILES


def reconstruct_dossier_from_raw(raw_pr: dict[str, Any]) -> dict[str, Any]:
    """Build a conservative MergeDossier from raw PR artifacts."""
    pr = raw_pr.get("pr", {}) if isinstance(raw_pr.get("pr"), dict) else {}
    manifest = raw_pr.get("manifest_metadata", {}) if isinstance(raw_pr.get("manifest_metadata"), dict) else {}
    body = str(pr.get("body", "") or "")
    title = str(pr.get("title", "") or "")
    all_text = _all_text(raw_pr)
    all_text_lower = all_text.lower()
    files = _files(raw_pr)
    checks = _checks(raw_pr)
    commits = _commits(raw_pr)
    linked_issues = raw_pr.get("linked_issues", []) or []

    evidence: dict[str, Any] = {}
    evidence_provenance: dict[str, list[dict[str, Any]]] = {}
    if title or body or linked_issues:
        evidence["intent"] = _evidence(
            True,
            2 if title and (body or linked_issues) else 1,
            title or "Intent inferred from linked issue metadata.",
            _grounding("pr", "title/body", f"{title}\n{body}") if title or body else _grounding("linked_issue", "linked_issues"),
            "Observed from PR title/body or linked issue.",
        )
        evidence_provenance["intent"] = _prov(
            "observed",
            "pr_title" if title else "linked_issue",
            "intent_title_body_issue_v1",
            "high",
            f"{title}\n{body}" if title or body else "",
            "Observed from PR title/body or linked issue.",
            raw_pr.get("pr_url"),
        )
    else:
        evidence["intent"] = _missing("No PR title/body or linked issue text available.")
        evidence_provenance["intent"] = _missing_prov(
            "intent_title_body_issue_v1",
            "Checked PR title, PR body, and linked issue metadata; no intent evidence was available.",
        )

    if linked_issues or _extract_pr_reference(body):
        evidence["requirement_traceability"] = _evidence(
            True,
            2 if linked_issues else 1,
            "PR references linked issue or issue-style requirement.",
            _grounding("linked_issue", "linked_issues") if linked_issues else _grounding("pr_body", "issue reference", body),
            "Observed from linked issue metadata or issue reference in PR body.",
        )
        evidence_provenance["requirement_traceability"] = _prov(
            "observed" if linked_issues else "inferred",
            "linked_issue" if linked_issues else "pr_body",
            "requirement_issue_reference_v1",
            "high" if linked_issues else "medium",
            body,
            "Observed linked issue metadata or inferred requirement traceability from issue references.",
            raw_pr.get("pr_url"),
        )
    else:
        evidence["requirement_traceability"] = _missing("No linked issue, closing keyword, or issue reference found.")
        evidence_provenance["requirement_traceability"] = _missing_prov(
            "requirement_issue_reference_v1",
            "Checked linked issues, closing keywords, and issue references; none were found.",
        )

    test_files = [item for item in files if "test" in str(item.get("filename", "")).lower()]
    test_checks = [
        item
        for item in checks
        if any(term in str(item.get("name", item.get("context", ""))).lower() for term in ("test", "pytest", "ci"))
    ]
    body_mentions_tests = "test" in body.lower() or "pytest" in body.lower()
    if test_files or test_checks or body_mentions_tests:
        test_status = "observed" if body_mentions_tests else "inferred"
        evidence["test_rationale"] = _evidence(
            True,
            2 if test_files and body_mentions_tests else 1,
            "Test evidence observed from files, checks, or PR body.",
            _grounding("changed_files", "test files", ", ".join(str(item.get("filename", "")) for item in test_files))
            if test_files
            else _grounding("checks", "test checks"),
            "Evidence is observed; metadata-only test signals are marked as thin.",
        )
        evidence_provenance["test_rationale"] = _prov(
            test_status,
            "pr_body" if body_mentions_tests else ("changed_file" if test_files else "ci_check"),
            "test_signal_scan_v1",
            "high" if body_mentions_tests else "medium",
            body if body_mentions_tests else ", ".join(_file_names(test_files)) or ", ".join(str(item.get("name", item.get("context", ""))) for item in test_checks),
            "PR-body test statements are observed; changed test files or CI check names are inferred metadata evidence.",
            raw_pr.get("pr_url"),
        )
    else:
        evidence["test_rationale"] = _missing("No changed test files, test checks, or PR body test rationale found.")
        evidence_provenance["test_rationale"] = _missing_prov(
            "test_signal_scan_v1",
            "Checked PR body, changed test files, and CI/check names; no test evidence was found.",
        )

    passing_checks = [
        item
        for item in checks
        if str(item.get("conclusion", item.get("status", item.get("state", "")))).lower() in {"success", "passed", "pass"}
    ]
    regression_mentioned = "regression" in all_text_lower
    if passing_checks or regression_mentioned:
        passing_names = ", ".join(str(item.get("name", item.get("context", ""))) for item in passing_checks)
        evidence["regression_safety"] = _evidence(
            True,
            1,
            "Regression safety evidence observed from checks or comments.",
            _grounding("checks", "passing checks", passing_names)
            if passing_checks
            else _grounding("comments", "regression mention"),
            f"Observed passing CI checks: {passing_names}. This is metadata evidence, not proof of full regression safety."
            if passing_checks
            else "Observed explicit regression mention; not treated as full proof.",
        )
        evidence_provenance["regression_safety"] = _prov(
            "inferred" if passing_checks and not regression_mentioned else "observed",
            "ci_check" if passing_checks and not regression_mentioned else "pr_body",
            "regression_signal_scan_v1",
            "medium" if passing_checks and not regression_mentioned else "high",
            passing_names if passing_checks else all_text,
            "Observed passing CI checks are metadata evidence, not proof of full regression safety.",
            raw_pr.get("pr_url"),
        )
    else:
        evidence["regression_safety"] = _missing("No passing check metadata or regression-safety discussion found.")
        evidence_provenance["regression_safety"] = _missing_prov(
            "regression_signal_scan_v1",
            "Checked CI/check metadata and regression-safety discussion; no regression evidence was found.",
        )

    if _has_terms(all_text, RISK_TERMS):
        evidence["risk_analysis"] = _evidence(
            True,
            1,
            "Risk-related language appears in PR text or comments.",
            _grounding("text", "risk terms"),
            "Observed risk language; quality remains thin unless the text provides a concrete analysis.",
        )
        evidence_provenance["risk_analysis"] = _prov(
            "observed",
            "pr_body",
            "risk_keyword_scan_v1",
            "high",
            all_text,
            "Observed risk, breaking-change, compatibility, security, migration, rollback, or regression-risk language.",
            raw_pr.get("pr_url"),
        )
    else:
        evidence["risk_analysis"] = _missing("No risk, breaking-change, compatibility, security, migration, rollback, or regression-risk discussion found.")
        evidence_provenance["risk_analysis"] = _missing_prov(
            "risk_keyword_scan_v1",
            "Checked PR body, reviews, review comments, issue comments, and linked issue text; no risk language was found.",
        )

    if files:
        dirs = _touched_dirs(files)
        explicit_scope = "scope" in body.lower() or "limited to" in body.lower()
        evidence["scope_justification"] = _evidence(
            True,
            1,
            _file_summary(files),
            _grounding("changed_files", "files"),
            "Inferred from changed file metadata; explicit scope rationale was not assumed.",
        )
        if explicit_scope:
            evidence["scope_justification"]["quality"] = 2
            evidence["scope_justification"]["notes"] = "Observed changed file metadata plus explicit PR body scope explanation."
            evidence["scope_justification"]["claim"] += f"; touched dirs: {', '.join(dirs) if dirs else 'root'}"
        evidence_provenance["scope_justification"] = _prov(
            "observed" if explicit_scope else "inferred",
            "pr_body" if explicit_scope else "changed_file",
            "scope_changed_file_scan_v1",
            "high" if explicit_scope else "medium",
            body if explicit_scope else _file_summary(files),
            "Explicit PR-body scope is observed; changed-file metadata is inferred scope evidence.",
            raw_pr.get("pr_url"),
        )
    else:
        evidence["scope_justification"] = _missing("No changed file metadata available.")
        evidence_provenance["scope_justification"] = _missing_prov(
            "scope_changed_file_scan_v1",
            "Checked changed file metadata and PR-body scope language; no scope evidence was found.",
        )

    if files or commits or body:
        commit_messages = "; ".join(str(item.get("message", "")) for item in commits[:3] if item.get("message"))
        evidence["change_summary"] = _evidence(
            True,
            2 if body and files else 1,
            _file_summary(files) if files else (commit_messages or title),
            _grounding("changed_files", "files") if files else _grounding("commits", "messages"),
            "Observed from changed file metadata, commits, or PR body.",
        )
        evidence_provenance["change_summary"] = _prov(
            "observed",
            "changed_file" if files else ("commit" if commits else "pr_body"),
            "change_summary_scan_v1",
            "high" if files or body else "medium",
            _file_summary(files) if files else commit_messages or body,
            "Observed from changed files, commits, or PR body.",
            raw_pr.get("pr_url"),
        )
    else:
        evidence["change_summary"] = _missing("No PR body, commits, or changed file metadata available.")
        evidence_provenance["change_summary"] = _missing_prov(
            "change_summary_scan_v1",
            "Checked PR body, commits, and changed files; no change summary evidence was found.",
        )

    if _has_terms(all_text, TRACE_TERMS):
        evidence["agent_trace"] = _evidence(True, 1, "Agent trace or command-log language appears in artifacts.", _grounding("text", "agent trace terms"), "Observed explicit trace language.")
        evidence_provenance["agent_trace"] = _prov(
            "observed",
            "pr_body",
            "trace_keyword_scan_v1",
            "high",
            all_text,
            "Observed agent logs, tool logs, command logs, reasoning summaries, task trace, or explicit agent execution notes.",
            raw_pr.get("pr_url"),
        )
    else:
        evidence["agent_trace"] = _missing("No agent logs, tool logs, command logs, reasoning summaries, or explicit agent trace found.")
        evidence_provenance["agent_trace"] = _missing_prov(
            "trace_keyword_scan_v1",
            "Checked PR body, comments, reviews, and linked issue text; no agent trace or command-log evidence was found.",
        )

    if _has_terms(all_text, LIMITATION_TERMS):
        evidence["limitations"] = _evidence(True, 1, "Limitations, follow-ups, TODOs, or constraints appear in artifacts.", _grounding("text", "limitation terms"), "Observed limitation language.")
        evidence_provenance["limitations"] = _prov(
            "observed",
            "pr_body",
            "limitation_keyword_scan_v1",
            "medium",
            all_text,
            "Observed limitation, known gap, follow-up, TODO, partial, or constraint language.",
            raw_pr.get("pr_url"),
        )
    else:
        evidence["limitations"] = _missing("No known limitations, follow-ups, partial implementation notes, TODOs, or constraints found.")
        evidence_provenance["limitations"] = _missing_prov(
            "limitation_keyword_scan_v1",
            "Checked PR body, comments, reviews, and linked issue text; no limitation evidence was found.",
        )

    if _has_terms(all_text, REVIEWER_TERMS):
        evidence["reviewer_actionability"] = _evidence(True, 1, "Reviewer instructions or validation steps appear in artifacts.", _grounding("text", "reviewer action terms"), "Observed reviewer-action language.")
        evidence_provenance["reviewer_actionability"] = _prov(
            "observed",
            "pr_body",
            "reviewer_action_keyword_scan_v1",
            "medium",
            all_text,
            "Observed reviewer instructions, validation steps, test commands, or inspection guidance.",
            raw_pr.get("pr_url"),
        )
    else:
        evidence["reviewer_actionability"] = _missing("No clear review instructions, validation steps, test commands, or inspection guidance found.")
        evidence_provenance["reviewer_actionability"] = _missing_prov(
            "reviewer_action_keyword_scan_v1",
            "Checked PR body, comments, reviews, and linked issue text; no reviewer-action evidence was found.",
        )

    if _has_terms(all_text, OWNERSHIP_TERMS):
        evidence["ownership_handoff"] = _evidence(True, 1, "Ownership, rollout, monitoring, manual steps, follow-up responsibility, or rollback is mentioned.", _grounding("text", "ownership terms"), "Observed handoff language.")
        evidence_provenance["ownership_handoff"] = _prov(
            "observed",
            "pr_body",
            "ownership_keyword_scan_v1",
            "high",
            all_text,
            "Observed rollout, monitoring, owner, manual steps, migration plan, follow-up responsibility, or maintainer handoff language.",
            raw_pr.get("pr_url"),
        )
    else:
        evidence["ownership_handoff"] = _missing("No owner, rollout, monitoring, manual step, follow-up responsibility, or maintainer handoff found.")
        evidence_provenance["ownership_handoff"] = _missing_prov(
            "ownership_keyword_scan_v1",
            "Checked PR body, comments, reviews, and linked issue text; no ownership handoff evidence was found.",
        )

    dependency_files = [name for name in _file_names(files) if _is_dependency_file(name)]
    if dependency_files:
        evidence_provenance["dependency_evidence"] = _prov(
            "inferred",
            "changed_file",
            "dependency_file_scan_v1",
            "medium",
            ", ".join(dependency_files),
            "Dependency evidence inferred from dependency or lockfile changes; compatibility rationale is not assumed.",
            raw_pr.get("pr_url"),
        )
    else:
        evidence_provenance["dependency_evidence"] = _prov(
            "not_applicable",
            "heuristic",
            "dependency_file_scan_v1",
            "medium",
            notes="No dependency manifest or lockfile changes were found.",
        )

    if _has_terms(all_text, RATIONALE_TERMS):
        evidence_provenance["rationale_evidence"] = _prov(
            "observed",
            "pr_body",
            "rationale_keyword_scan_v1",
            "medium",
            all_text,
            "Observed rationale, design, approach, why, implementation notes, tradeoff, or alternative language.",
            raw_pr.get("pr_url"),
        )
    else:
        evidence_provenance["rationale_evidence"] = _missing_prov(
            "rationale_keyword_scan_v1",
            "Checked PR body, comments, reviews, and linked issue text; no rationale evidence was found.",
        )

    return {
        "schema_version": "0.1.0",
        "dossier_id": f"dossier-{raw_pr.get('instance_id', 'UNKNOWN')}",
        "instance_id": raw_pr.get("instance_id", "UNKNOWN"),
        "repository": raw_pr.get("repo", ""),
        "pr_url": raw_pr.get("pr_url", ""),
        "source_agent": manifest.get("agent_name") or raw_pr.get("source_agent", "unknown"),
        "created_at": pr.get("created_at") or raw_pr.get("fetched_at", ""),
        "dossier_created_at": raw_pr.get("fetched_at", ""),
        "evidence": {key: evidence.get(key, _missing(f"No reconstruction rule populated {key}.")) for key in EVIDENCE_TYPES},
        "evidence_provenance": evidence_provenance,
        "limitations": ["Offline reconstruction is conservative and artifact-bound."],
        "metadata": {
            "seed_builder": True,
            "fetch_mode": raw_pr.get("fetch_mode", ""),
            "manifest_metadata": manifest,
            "raw_instance_id": raw_pr.get("instance_id", ""),
        },
    }


def reconstruct_dossiers_from_raw_dir(raw_dir: str | Path, out_dir: str | Path) -> list[dict[str, Any]]:
    """Reconstruct dossiers for every raw PR JSON in a directory."""
    output_path = Path(out_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    dossiers = []
    for raw_path in sorted(Path(raw_dir).glob("*.json")):
        raw = load_json(raw_path)
        dossier = reconstruct_dossier_from_raw(raw)
        (output_path / f"{raw.get('instance_id', raw_path.stem)}.json").write_text(
            json.dumps(dossier, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        dossiers.append(dossier)
    return dossiers


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_summary_md(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Seed Corpus Build Summary",
        "",
        f"- Total manifest rows: {summary['total_manifest_rows']}",
        f"- Processed rows: {summary['processed_rows']}",
        f"- Missing fixtures: {summary['missing_fixtures']}",
        f"- Reconstructed dossiers: {summary['reconstructed_dossiers']}",
        "",
        "## Counts",
    ]
    for key in ("author_type_counts", "agent_name_counts", "outcome_counts", "task_type_counts", "language_counts"):
        lines.extend(["", f"### {key}", ""])
        counts = summary.get(key, {})
        if counts:
            lines.extend(f"- {name}: {count}" for name, count in counts.items())
        else:
            lines.append("- none")
    lines.extend(["", "## Missing core artifacts", ""])
    lines.extend(f"- {name}: {count}" for name, count in summary.get("missing_core_artifact_counts", {}).items())
    lines.extend(["", "## Evidence presence", ""])
    lines.extend(f"- {name}: {count}" for name, count in summary.get("evidence_presence_counts", {}).items())
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _summary(rows: list[dict[str, str]], raw_records: list[dict[str, Any]], dossiers: list[dict[str, Any]], missing: int) -> dict[str, Any]:
    missing_core = Counter()
    for raw in raw_records:
        for key in ("commits", "files", "reviews", "review_comments", "issue_comments", "checks", "linked_issues"):
            if not raw.get(key):
                missing_core[key] += 1
    evidence_presence = Counter()
    for dossier in dossiers:
        for key, item in dossier.get("evidence", {}).items():
            if item.get("present"):
                evidence_presence[key] += 1
    return {
        "total_manifest_rows": len(rows),
        "processed_rows": len(raw_records),
        "missing_fixtures": missing,
        "reconstructed_dossiers": len(dossiers),
        "author_type_counts": dict(Counter(row.get("author_type", "") for row in rows)),
        "agent_name_counts": dict(Counter(row.get("agent_name", "") for row in rows)),
        "outcome_counts": dict(Counter(row.get("outcome", "") for row in rows)),
        "task_type_counts": dict(Counter(row.get("task_type", "") for row in rows)),
        "language_counts": dict(Counter(row.get("language", "") for row in rows)),
        "missing_core_artifact_counts": dict(missing_core),
        "evidence_presence_counts": {key: evidence_presence.get(key, 0) for key in EVIDENCE_TYPES},
    }


def write_seed_corpus(
    manifest: str | Path | list[dict[str, str]],
    out_dir: str | Path,
    fixture_dir: str | Path | None = None,
    live: bool = False,
    github_token: str | None = None,
    api_base: str = "https://api.github.com",
    sleep_seconds: float = 0.0,
    continue_on_error: bool = True,
    github_client: GitHubClient | None = None,
    limit: int | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Build a seed corpus from a manifest and offline fixtures or live GitHub."""
    rows = load_seed_manifest(manifest) if not isinstance(manifest, list) else manifest
    if limit is not None:
        rows = rows[:limit]
    errors = validate_seed_manifest(rows)
    if errors:
        raise ValueError("; ".join(errors))
    if fixture_dir and live:
        raise ValueError("Use either fixture_dir or live mode, not both.")
    if fixture_dir is None and not live:
        raise ValueError("Provide fixture_dir or set live=True; live fetching is never implicit.")

    output = Path(out_dir)
    for child in ("raw", "dossiers", "manifests", "logs"):
        (output / child).mkdir(parents=True, exist_ok=True)

    raw_records: list[dict[str, Any]] = []
    dossiers: list[dict[str, Any]] = []
    log_rows: list[dict[str, Any]] = []
    missing = 0

    client = github_client or (GitHubClient(token=github_token, api_base=api_base) if live else None)

    for row in rows:
        raw_path = output / "raw" / f"{row['instance_id']}.json"
        try:
            if raw_path.exists() and not force:
                raw = load_json(raw_path)
                raw["manifest_metadata"] = {**row, **raw.get("manifest_metadata", {})}
                log_source = "cached_raw"
            elif fixture_dir is not None:
                raw = load_fixture_raw_pr(fixture_dir, row)
                log_source = "fixture"
            else:
                assert client is not None
                raw = fetch_live_raw_pr(row, client, sleep_seconds=sleep_seconds)
                log_source = "live"
        except FileNotFoundError as exc:
            missing += 1
            log_rows.append({"instance_id": row.get("instance_id"), "status": "missing_fixture", "error": str(exc)})
            continue
        except Exception as exc:
            log_rows.append({"instance_id": row.get("instance_id"), "status": "fetch_error", "error": str(exc)})
            if continue_on_error:
                continue
            raise
        raw_errors = validate_data(raw, "github_pr_raw")
        if raw_errors:
            log_rows.append({"instance_id": row.get("instance_id"), "status": "invalid_raw", "errors": raw_errors})
            if not continue_on_error:
                raise ValueError("; ".join(raw_errors))
            continue
        dossier = reconstruct_dossier_from_raw(raw)
        dossier_errors = validate_data(dossier, "dossier")
        if dossier_errors:
            log_rows.append({"instance_id": row.get("instance_id"), "status": "invalid_dossier", "errors": dossier_errors})
            if not continue_on_error:
                raise ValueError("; ".join(dossier_errors))
            continue
        raw_records.append(raw)
        dossiers.append(dossier)
        _write_json(raw_path, raw)
        _write_json(output / "dossiers" / f"{row['instance_id']}.json", dossier)
        log_rows.append(
            {
                "instance_id": row.get("instance_id"),
                "status": "reconstructed",
                "source": log_source,
                "endpoint_errors": len(raw.get("errors", [])),
            }
        )

    with (output / "manifests" / "resolved_manifest.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    with (output / "logs" / "build_seed_corpus_log.jsonl").open("w", encoding="utf-8") as f:
        for row in log_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary = _summary(rows, raw_records, dossiers, missing)
    _write_json(output / "summary.json", summary)
    _write_summary_md(output / "summary.md", summary)
    return summary
