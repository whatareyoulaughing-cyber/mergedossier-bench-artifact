"""Data collection utilities for GitHub/AIDev-style PR data.

This module intentionally avoids doing network work at import time. Use a token
from the environment for real collection, and never commit private data.
"""

from __future__ import annotations

import csv
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable, Iterable

KNOWN_AGENT_HINTS = {
    "codex": "Codex",
    "openai": "Codex",
    "devin": "Devin",
    "claude": "Claude Code",
    "copilot": "GitHub Copilot",
    "cursor": "Cursor",
    "aider": "Aider",
    "github-copilot[bot]": "GitHub Copilot",
}


def infer_source_agent(*texts: str) -> str:
    """Infer source agent from author/title/body/labels using simple heuristics."""
    blob = " ".join(t or "" for t in texts).lower()
    for hint, agent in KNOWN_AGENT_HINTS.items():
        if hint in blob:
            return agent
    return "unknown"


def load_aidev_like_csv(path: str | Path) -> list[dict[str, Any]]:
    """Load a CSV exported from AIDev-like PR metadata.

    This is a loose adapter. Codex should specialize it once the actual CSV
    column names are available.
    """
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            repo = row.get("repository") or row.get("repo") or row.get("full_name") or "unknown/unknown"
            pr_number_raw = row.get("pr_number") or row.get("number") or "0"
            try:
                pr_number = int(pr_number_raw)
            except ValueError:
                pr_number = 0
            title = row.get("title", "")
            body = row.get("body", "")
            author = row.get("author") or row.get("user_login") or row.get("creator") or "unknown"
            source_agent = row.get("source_agent") or infer_source_agent(author, title, body, row.get("labels", ""))
            rows.append(
                {
                    "schema_version": "0.1.0",
                    "instance_id": row.get("instance_id") or f"{repo.replace('/', '-')}-{pr_number}",
                    "repository": repo,
                    "pr_number": pr_number,
                    "pr_url": row.get("pr_url") or row.get("html_url") or "",
                    "title": title,
                    "body": body,
                    "author": author,
                    "source_agent": source_agent,
                    "created_at": row.get("created_at", ""),
                    "closed_at": row.get("closed_at") or None,
                    "merged_at": row.get("merged_at") or None,
                    "base_sha": row.get("base_sha", ""),
                    "head_sha": row.get("head_sha", ""),
                    "issue_links": [],
                    "files_changed": [],
                    "commits": [],
                    "tests": [],
                    "ci_runs": [],
                    "review_events": [],
                    "agent_trace": None,
                    "labels": [x.strip() for x in row.get("labels", "").split(",") if x.strip()],
                    "metadata": {"source_csv": str(path)},
                }
            )
    return rows


def require_github_token(env_var: str = "GITHUB_TOKEN") -> str:
    """Return a GitHub token from the environment or raise a helpful error."""
    token = os.environ.get(env_var)
    if not token:
        raise RuntimeError(f"Set {env_var} before using GitHub collection functions.")
    return token


class GitHubClient:
    """Small GitHub REST client with injectable transport for offline tests."""

    def __init__(
        self,
        token: str | None = None,
        api_base: str = "https://api.github.com",
        timeout: int = 30,
        transport: Callable[..., tuple[int, dict[str, str], Any]] | None = None,
    ) -> None:
        self.token = token
        self.api_base = api_base.rstrip("/")
        self.timeout = timeout
        self.transport = transport

    def _url(self, path_or_url: str, params: dict[str, Any] | None = None) -> str:
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            base = path_or_url
        else:
            base = f"{self.api_base}/{path_or_url.lstrip('/')}"
        if not params:
            return base
        separator = "&" if "?" in base else "?"
        return base + separator + urllib.parse.urlencode(params)

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "MergeDossier-Bench",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _default_transport(self, url: str, headers: dict[str, str], timeout: int) -> tuple[int, dict[str, str], Any]:
        request = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8")
                data = json.loads(body) if body else None
                return response.status, dict(response.headers.items()), data
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            try:
                data = json.loads(body) if body else {}
            except json.JSONDecodeError:
                data = {"message": body}
            return exc.code, dict(exc.headers.items()), data
        except urllib.error.URLError as exc:
            return 0, {}, {"message": str(exc.reason)}

    def _request(self, url: str) -> tuple[int, dict[str, str], Any]:
        headers = self._headers()
        if self.transport is not None:
            return self.transport(url=url, headers=headers, timeout=self.timeout)
        return self._default_transport(url, headers, self.timeout)

    def get_json(self, path_or_url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Fetch one JSON resource and return a structured result."""
        url = self._url(path_or_url, params)
        status, headers, data = self._request(url)
        ok = 200 <= int(status) < 300
        error = None
        if not ok:
            message = data.get("message") if isinstance(data, dict) else str(data)
            error = {
                "endpoint": path_or_url,
                "status": status,
                "message": message or "GitHub API request failed",
                "rate_limit_remaining": headers.get("x-ratelimit-remaining") or headers.get("X-RateLimit-Remaining"),
                "rate_limit_reset": headers.get("x-ratelimit-reset") or headers.get("X-RateLimit-Reset"),
            }
        return {"ok": ok, "status": status, "headers": headers, "data": data, "error": error}

    def get_paginated(self, path_or_url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Fetch a paginated GitHub list endpoint."""
        first_params = {"per_page": 100}
        if params:
            first_params.update(params)
        url = self._url(path_or_url, first_params)
        items: list[Any] = []
        errors: list[dict[str, Any]] = []
        while url:
            result = self.get_json(url)
            if not result["ok"]:
                errors.append(result["error"])
                break
            data = result["data"]
            if isinstance(data, list):
                items.extend(data)
            elif data is not None:
                items.append(data)
            url = _next_link(result["headers"].get("Link") or result["headers"].get("link", ""))
        return {"ok": not errors, "data": items, "errors": errors}

    def fetch_pull_request(self, repo: str, pr_number: int | str) -> dict[str, Any]:
        return self.get_json(f"/repos/{repo}/pulls/{pr_number}")

    def fetch_pull_commits(self, repo: str, pr_number: int | str) -> dict[str, Any]:
        return self.get_paginated(f"/repos/{repo}/pulls/{pr_number}/commits")

    def fetch_pull_files(self, repo: str, pr_number: int | str) -> dict[str, Any]:
        return self.get_paginated(f"/repos/{repo}/pulls/{pr_number}/files")

    def fetch_pull_reviews(self, repo: str, pr_number: int | str) -> dict[str, Any]:
        return self.get_paginated(f"/repos/{repo}/pulls/{pr_number}/reviews")

    def fetch_pull_review_comments(self, repo: str, pr_number: int | str) -> dict[str, Any]:
        return self.get_paginated(f"/repos/{repo}/pulls/{pr_number}/comments")

    def fetch_issue_comments(self, repo: str, issue_number: int | str) -> dict[str, Any]:
        return self.get_paginated(f"/repos/{repo}/issues/{issue_number}/comments")

    def fetch_linked_issues_best_effort(
        self, repo: str, pr_body: str, issue_comments: list[dict[str, Any]] | None = None
    ) -> dict[str, Any]:
        """Extract issue references and hydrate issue metadata when available."""
        references = extract_issue_references(pr_body, issue_comments or [])
        linked: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        for number, method in references.items():
            result = self.get_json(f"/repos/{repo}/issues/{number}")
            if result["ok"] and isinstance(result["data"], dict):
                issue = dict(result["data"])
                issue["extraction_method"] = method
                linked.append(issue)
            else:
                linked.append({"number": number, "extraction_method": method})
                if result["error"]:
                    errors.append(result["error"])
        return {"ok": not errors, "data": linked, "errors": errors}

    def fetch_check_runs(self, repo: str, ref_sha: str) -> dict[str, Any]:
        result = self.get_json(f"/repos/{repo}/commits/{ref_sha}/check-runs")
        if result["ok"] and isinstance(result["data"], dict):
            return {"ok": True, "data": result["data"].get("check_runs", []), "errors": []}
        return {"ok": False, "data": [], "errors": [result["error"]]}

    def fetch_statuses(self, repo: str, ref_sha: str) -> dict[str, Any]:
        return self.get_paginated(f"/repos/{repo}/commits/{ref_sha}/statuses")


def _next_link(link_header: str) -> str | None:
    for part in link_header.split(","):
        section = part.strip()
        if 'rel="next"' not in section:
            continue
        start = section.find("<")
        end = section.find(">")
        if start >= 0 and end > start:
            return section[start + 1 : end]
    return None


def extract_issue_references(pr_body: str, issue_comments: list[dict[str, Any]] | None = None) -> dict[int, str]:
    """Extract best-effort linked issue references from PR text and comments."""
    references: dict[int, str] = {}
    texts = [pr_body or ""]
    texts.extend(str(item.get("body", "")) for item in (issue_comments or []) if isinstance(item, dict))
    closing = re_compile_closing()
    generic = re_compile_generic_issue()
    for text in texts:
        for match in closing.finditer(text):
            references[int(match.group("number"))] = "closing_keyword"
        for match in generic.finditer(text):
            references.setdefault(int(match.group("number")), "issue_reference")
    return references


def re_compile_closing():
    import re

    return re.compile(r"\b(?:fixes|closes|resolves)\s+#(?P<number>\d+)", flags=re.IGNORECASE)


def re_compile_generic_issue():
    import re

    return re.compile(r"(?<![\w/])#(?P<number>\d+)")


def iter_jsonl(rows: Iterable[dict[str, Any]]) -> Iterable[str]:
    """Yield JSONL strings without importing json at call sites."""
    import json

    for row in rows:
        yield json.dumps(row, ensure_ascii=False)
