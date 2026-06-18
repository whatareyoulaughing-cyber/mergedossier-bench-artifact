"""Export an AIDev pull-request table into the MergeDossier population CSV shape."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from mergedossier_bench.population import normalize_agent


DEFAULT_DATASET = "hao-li/AIDev"
DEFAULT_TABLE = "pull_request.parquet"

EXPORT_COLUMNS = [
    "repository",
    "number",
    "html_url",
    "source_agent",
    "author_type",
    "title",
    "body",
    "language",
    "outcome",
    "created_at",
    "changed_file_count",
    "commit_count",
    "comment_count",
    "review_count",
    "source",
    "notes",
    "files_changed",
    "commit_messages",
    "comments",
    "reviews",
    "ci_status",
]


def _source_from_args(args: argparse.Namespace) -> str:
    if args.input:
        return args.input
    return f"hf://datasets/{args.dataset}/{args.table}"


def _table_source(dataset: str, table: str) -> str:
    if not table:
        return ""
    if table.startswith("hf://") or table.lower().endswith(".csv") or Path(table).exists():
        return table
    return f"hf://datasets/{dataset}/{table}"


def _first(row: dict[str, Any], *keys: str) -> str:
    lower_map = {str(key).lower(): key for key in row}
    for key in keys:
        actual = lower_map.get(key.lower())
        if actual is None:
            continue
        value = row.get(actual)
        if value not in (None, ""):
            if isinstance(value, float) and str(value) == "nan":
                continue
            return str(value).strip()
    return ""


def _parse_int(value: Any) -> int:
    if value in (None, ""):
        return 0
    try:
        return int(float(str(value).strip()))
    except ValueError:
        return 0


def _truthy(value: Any) -> bool | None:
    if value in (None, ""):
        return None
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "public"}:
        return True
    if text in {"0", "false", "no", "n", "private"}:
        return False
    return None


def _parse_repo_number_from_url(url: str) -> tuple[str, str]:
    match = re.search(r"github\.com/([^/\s]+)/([^/\s]+)/pull/(\d+)", url or "")
    if not match:
        return "", ""
    return f"{match.group(1)}/{match.group(2)}", match.group(3)


def _listish_text(value: str) -> str:
    return value.replace("\r\n", "\n").strip()


def _join_preview(items: list[str], limit: int = 8, max_chars: int = 1200) -> str:
    clean = [item.replace("\r\n", "\n").strip() for item in items if str(item).strip()]
    text = " | ".join(clean[:limit])
    return text[:max_chars]


def _repo_and_number(row: dict[str, Any]) -> tuple[str, str, str]:
    url = _first(row, "html_url", "pr_url", "pull_request_url", "url")
    repo = _first(row, "repository", "repo", "repo_name", "full_name", "repository_name")
    repo_api_url = _first(row, "repo_url", "repository_url")
    if not repo and repo_api_url:
        match = re.search(r"/repos/([^/\s]+/[^/\s]+)$", repo_api_url)
        if match:
            repo = match.group(1)
    number = _first(row, "number", "pr_number", "pull_number", "pull_request_number")
    parsed_repo, parsed_number = _parse_repo_number_from_url(url)
    return repo or parsed_repo, number or parsed_number, url


def _outcome(row: dict[str, Any]) -> str:
    state = _first(row, "outcome", "state", "status")
    merged = _first(row, "merged_at", "merge_commit_sha", "merged")
    closed = _first(row, "closed_at")
    if str(merged).strip().lower() in {"true", "1", "yes"} or (merged and merged.lower() not in {"false", "0", "nan"}):
        return "merged"
    if state.lower() == "merged":
        return "merged"
    if closed or state.lower() in {"closed", "rejected", "closed_unmerged"}:
        return "closed_unmerged"
    if state.lower() == "open":
        return "open"
    return state or "unknown"


def _explicit_curated(row: dict[str, Any]) -> bool | None:
    for key in ("is_curated", "curated", "curated_subset", "in_curated_subset"):
        value = _truthy(_first(row, key))
        if value is not None:
            return value
    subset = _first(row, "subset", "split", "frame", "dataset_split").lower()
    if subset:
        if "curated" in subset:
            return True
        if subset in {"all", "full"}:
            return False
    return None


def _star_count(row: dict[str, Any]) -> tuple[int, bool]:
    for key in ("repo_stars", "stars", "stargazers_count", "repository_stars", "star_count"):
        value = _first(row, key)
        if value:
            return _parse_int(value), True
    return 0, False


def _has_artifacts(row: dict[str, Any]) -> tuple[bool, bool]:
    artifact_keys = (
        "comment_count",
        "comments_count",
        "issue_comment_count",
        "review_count",
        "reviews_count",
        "review_comment_count",
        "commit_count",
        "commits_count",
        "issue_count",
        "linked_issue_count",
        "comments",
        "reviews",
        "commit_messages",
        "commits",
    )
    found = any(_first(row, key) for key in artifact_keys)
    if not found:
        return True, False
    return any(_parse_int(_first(row, key)) > 0 or len(_first(row, key)) > 2 for key in artifact_keys), True


def _is_public(row: dict[str, Any]) -> tuple[bool, bool]:
    private = _truthy(_first(row, "private", "is_private"))
    public = _truthy(_first(row, "public", "is_public"))
    if private is not None:
        return not private, True
    if public is not None:
        return public, True
    return True, False


def normalize_aidev_row(row: dict[str, Any]) -> dict[str, str]:
    repo, number, url = _repo_and_number(row)
    title = _first(row, "title", "pr_title")
    body = _first(row, "body", "pr_body", "description")
    agent_raw = _first(row, "source_agent", "agent", "agent_name", "tool", "bot", "actor_login", "author", "user_login", "login")
    agent = normalize_agent(agent_raw, title, body, _first(row, "labels", "label_names"))
    if not url and repo and number:
        url = f"https://github.com/{repo}/pull/{_parse_int(number)}"
    return {
        "repository": repo,
        "number": str(_parse_int(number)),
        "html_url": url,
        "source_agent": agent_raw or agent,
        "author_type": "ai_authored" if agent != "unknown" else "unknown",
        "title": title,
        "body": body,
        "language": _first(row, "language", "primary_language", "ecosystem") or "unknown",
        "outcome": _outcome(row),
        "created_at": _first(row, "created_at", "opened_at"),
        "changed_file_count": str(_parse_int(_first(row, "changed_file_count", "changed_files_count", "files_count", "num_files"))),
        "commit_count": str(_parse_int(_first(row, "commit_count", "commits_count", "num_commits"))),
        "comment_count": str(_parse_int(_first(row, "comment_count", "comments_count", "issue_comment_count"))),
        "review_count": str(_parse_int(_first(row, "review_count", "reviews_count", "review_comment_count"))),
        "source": "aidev_curated_export",
        "notes": "Exported from AIDev original public dataset for MergeDossier population-frame sampling.",
        "files_changed": _listish_text(_first(row, "files_changed", "changed_files", "file_paths")),
        "commit_messages": _listish_text(_first(row, "commit_messages", "commits")),
        "comments": _listish_text(_first(row, "comments", "issue_comments", "review_comments")),
        "reviews": _listish_text(_first(row, "reviews")),
        "ci_status": _first(row, "ci_status", "check_status", "status_checks"),
    }


def include_row(row: dict[str, Any], curated_only: bool) -> tuple[bool, str]:
    repo, number, _ = _repo_and_number(row)
    if not repo or not number:
        return False, "missing_repo_or_pr_number"
    agent = normalize_agent(_first(row, "source_agent", "agent", "agent_name", "tool", "bot", "actor_login", "author", "user_login", "login"), _first(row, "title", "body"))
    if agent == "unknown":
        return False, "missing_ai_authorship_evidence"
    public_ok, public_checked = _is_public(row)
    if public_checked and not public_ok:
        return False, "private_or_unavailable"
    if curated_only:
        explicit = _explicit_curated(row)
        if explicit is False:
            return False, "not_curated_subset"
        if explicit is None:
            stars, stars_checked = _star_count(row)
            if stars_checked and stars < 100:
                return False, "repo_below_100_stars"
            artifact_ok, artifact_checked = _has_artifacts(row)
            if artifact_checked and not artifact_ok:
                return False, "missing_curated_artifacts"
    return True, "included"


def _read_csv_rows(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        return [dict(row) for row in csv.DictReader(f)]


def _read_source_rows(source: str, columns: list[str] | None = None) -> list[dict[str, Any]]:
    if Path(source).suffix.lower() == ".csv":
        rows = _read_csv_rows(source)
        if columns is None:
            return rows
        return [{key: row.get(key, "") for key in columns} for row in rows]
    try:
        import pandas as pd
    except ModuleNotFoundError as exc:
        raise SystemExit("pandas and pyarrow are required. Install with: pip install -e \".[analysis]\"") from exc
    df = pd.read_parquet(source, columns=columns)
    return df.fillna("").to_dict(orient="records")


def _enrich_with_repository(rows: list[dict[str, Any]], repository_source: str) -> dict[str, Any]:
    if not repository_source:
        return {"repository_rows": 0, "matched_rows": 0}
    repo_rows = _read_source_rows(repository_source, columns=["id", "url", "full_name", "language", "stars"])
    by_id = {str(_parse_int(row.get("id"))): row for row in repo_rows}
    by_url = {str(row.get("url", "")): row for row in repo_rows if row.get("url")}
    matched = 0
    for row in rows:
        repo = by_id.get(str(_parse_int(row.get("repo_id")))) or by_url.get(str(row.get("repo_url", "")))
        if not repo:
            continue
        matched += 1
        row.setdefault("repository", repo.get("full_name", ""))
        row.setdefault("language", repo.get("language", ""))
        row.setdefault("repo_stars", repo.get("stars", ""))
    return {"repository_rows": len(repo_rows), "matched_rows": matched}


def _enrich_counts_and_text(
    rows: list[dict[str, Any]],
    *,
    commits_source: str = "",
    commit_details_source: str = "",
    comments_source: str = "",
    reviews_source: str = "",
) -> dict[str, Any]:
    by_pr: dict[str, dict[str, Any]] = {
        str(_parse_int(row.get("id"))): row for row in rows if _parse_int(row.get("id"))
    }
    summary: dict[str, Any] = {}

    if commits_source:
        commit_rows = _read_source_rows(commits_source, columns=["pr_id", "message"])
        messages: dict[str, list[str]] = defaultdict(list)
        for row in commit_rows:
            messages[str(_parse_int(row.get("pr_id")))].append(str(row.get("message", "")))
        for pr_id, items in messages.items():
            if pr_id in by_pr:
                by_pr[pr_id]["commit_count"] = len(items)
                by_pr[pr_id]["commit_messages"] = _join_preview(items)
        summary["commit_rows"] = len(commit_rows)
        summary["commit_prs"] = len(messages)

    if commit_details_source:
        detail_rows = _read_source_rows(commit_details_source, columns=["pr_id", "filename"])
        files: dict[str, set[str]] = defaultdict(set)
        for row in detail_rows:
            filename = str(row.get("filename", "")).strip()
            if filename:
                files[str(_parse_int(row.get("pr_id")))].add(filename)
        for pr_id, items in files.items():
            if pr_id in by_pr:
                sorted_files = sorted(items)
                by_pr[pr_id]["changed_file_count"] = len(sorted_files)
                by_pr[pr_id]["files_changed"] = _join_preview(sorted_files, limit=25)
        summary["commit_detail_rows"] = len(detail_rows)
        summary["file_prs"] = len(files)

    if comments_source:
        comment_rows = _read_source_rows(comments_source, columns=["pr_id", "body"])
        comments: dict[str, list[str]] = defaultdict(list)
        for row in comment_rows:
            comments[str(_parse_int(row.get("pr_id")))].append(str(row.get("body", "")))
        for pr_id, items in comments.items():
            if pr_id in by_pr:
                by_pr[pr_id]["comment_count"] = len(items)
                by_pr[pr_id]["comments"] = _join_preview(items, limit=6)
        summary["comment_rows"] = len(comment_rows)
        summary["comment_prs"] = len(comments)

    if reviews_source:
        review_rows = _read_source_rows(reviews_source, columns=["pr_id", "body", "state"])
        reviews: dict[str, list[str]] = defaultdict(list)
        for row in review_rows:
            body = str(row.get("body", "")).strip()
            state = str(row.get("state", "")).strip()
            reviews[str(_parse_int(row.get("pr_id")))].append(f"{state}: {body}" if body else state)
        for pr_id, items in reviews.items():
            if pr_id in by_pr:
                by_pr[pr_id]["review_count"] = len(items)
                by_pr[pr_id]["reviews"] = _join_preview(items, limit=6)
        summary["review_rows"] = len(review_rows)
        summary["review_prs"] = len(reviews)

    return summary


def export_aidev_curated_csv(
    source: str,
    out: str | Path,
    report_out: str | Path,
    curated_only: bool = True,
    *,
    repository_source: str = "",
    commits_source: str = "",
    commit_details_source: str = "",
    comments_source: str = "",
    reviews_source: str = "",
) -> dict[str, Any]:
    raw_rows = _read_source_rows(source)
    enrichment = {}
    enrichment["repository"] = _enrich_with_repository(raw_rows, repository_source)
    enrichment["artifacts"] = _enrich_counts_and_text(
        raw_rows,
        commits_source=commits_source,
        commit_details_source=commit_details_source,
        comments_source=comments_source,
        reviews_source=reviews_source,
    )
    exported: list[dict[str, str]] = []
    reasons: Counter[str] = Counter()
    for raw in raw_rows:
        include, reason = include_row(raw, curated_only)
        reasons[reason] += 1
        if include:
            exported.append(normalize_aidev_row(raw))
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=EXPORT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(exported)
    report_dir = Path(report_out)
    report_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "source": source,
        "curated_only": curated_only,
        "raw_rows": len(raw_rows),
        "exported_rows": len(exported),
        "exclusion_reason_counts": dict(reasons),
        "filter_rule": (
            "Use the AIDev-pop pull_request table as the curated frame; when other inputs are used, apply "
            "public/AI-authorship checks and repo-stars/artifact-availability filters when those fields are present."
        ),
        "enrichment": enrichment,
        "output_csv": str(out_path),
    }
    (report_dir / "export_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (report_dir / "export_report.md").write_text(
        "\n".join(
            [
                "# AIDev Export Report",
                "",
                f"- Source: `{source}`",
                f"- Raw rows: {len(raw_rows)}",
                f"- Exported rows: {len(exported)}",
                f"- Curated-only filter: {curated_only}",
                "",
                "## Inclusion/Exclusion Counts",
                "",
                *[f"- {key}: {value}" for key, value in sorted(reasons.items())],
                "",
                "This export is an operational sampling-frame artifact, not an empirical result.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export AIDev pull requests to a MergeDossier-compatible CSV")
    parser.add_argument("--dataset", default=DEFAULT_DATASET, help="Hugging Face dataset id")
    parser.add_argument("--table", default=DEFAULT_TABLE, help="Dataset table/parquet file")
    parser.add_argument("--input", help="Optional local or hf:// parquet/CSV source")
    parser.add_argument("--repository-table", default="repository.parquet", help="Optional repository table for language/stars/full_name")
    parser.add_argument("--commits-table", default="pr_commits.parquet", help="Optional PR commits table for commit counts/messages")
    parser.add_argument("--commit-details-table", default="pr_commit_details.parquet", help="Optional commit detail table for changed files")
    parser.add_argument("--comments-table", default="pr_comments.parquet", help="Optional issue comments table")
    parser.add_argument("--reviews-table", default="pr_reviews.parquet", help="Optional review table")
    parser.add_argument("--no-joins", action="store_true", help="Disable repository/artifact table joins")
    parser.add_argument("--out", required=True, help="Output CSV")
    parser.add_argument("--report-out", required=True, help="Output directory for export report")
    parser.add_argument("--all-rows", action="store_true", help="Disable curated-frame filtering")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source = _source_from_args(args)
    report = export_aidev_curated_csv(
        source,
        args.out,
        args.report_out,
        curated_only=not args.all_rows,
        repository_source="" if args.no_joins else _table_source(args.dataset, args.repository_table),
        commits_source="" if args.no_joins else _table_source(args.dataset, args.commits_table),
        commit_details_source="" if args.no_joins else _table_source(args.dataset, args.commit_details_table),
        comments_source="" if args.no_joins else _table_source(args.dataset, args.comments_table),
        reviews_source="" if args.no_joins else _table_source(args.dataset, args.reviews_table),
    )
    print(f"AIDev export written: {report['exported_rows']} of {report['raw_rows']} rows -> {args.out}")
    if report["exported_rows"] == 0:
        print("WARNING: export produced zero rows; inspect export_report.json and source schema.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
