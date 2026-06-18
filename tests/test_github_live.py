import csv
import json
from pathlib import Path

from mergedossier_bench.cli import main
from mergedossier_bench.github_miner import GitHubClient
from mergedossier_bench.seed_builder import fetch_live_raw_pr, load_seed_manifest, write_seed_corpus
from mergedossier_bench.validators import validate_data, validate_file


def _transport_from(routes):
    calls = []

    def transport(url, headers, timeout):
        calls.append(url)
        for needle, response in routes.items():
            if needle in url:
                return response
        return 404, {}, {"message": f"missing route for {url}"}

    transport.calls = calls
    return transport


def _routes():
    return {
        "/pulls/5/commits?per_page=100": (
            200,
            {},
            [
                {"sha": "c1", "message": "first"},
            ],
        ),
        "page=2": (
            200,
            {},
            [
                {"sha": "c2", "message": "second"},
            ],
        ),
        "/pulls/5/files?per_page=100": (200, {}, []),
        "/pulls/5/reviews?per_page=100": (200, {}, []),
        "/pulls/5/comments?per_page=100": (200, {}, []),
        "/issues/5/comments?per_page=100": (200, {}, []),
        "/pulls/5": (
            200,
            {},
            {
                "title": "Fix parser",
                "body": "Fixes #9. Tests: pytest passed.",
                "created_at": "2026-06-01T00:00:00Z",
                "head": {"sha": "head5"},
            },
        ),
        "/issues/9": (200, {}, {"number": 9, "title": "Parser issue", "body": "Parser should handle empty values."}),
        "/commits/head5/check-runs": (200, {}, {"check_runs": [{"name": "pytest", "conclusion": "success"}]}),
        "/commits/head5/statuses?per_page=100": (200, {}, [{"context": "lint", "state": "success"}]),
    }


def test_github_client_pagination_with_fake_transport():
    routes = {
        "/things?per_page=100": (
            200,
            {"Link": '<https://api.github.test/things?page=2>; rel="next"'},
            [{"id": 1}],
        ),
        "page=2": (200, {}, [{"id": 2}]),
    }
    client = GitHubClient(api_base="https://api.github.test", transport=_transport_from(routes))

    result = client.get_paginated("/things")

    assert result["ok"] is True
    assert result["data"] == [{"id": 1}, {"id": 2}]


def test_github_client_partial_endpoint_failure():
    client = GitHubClient(api_base="https://api.github.test", transport=_transport_from({"/missing": (404, {}, {"message": "Not Found"})}))

    result = client.get_json("/missing")

    assert result["ok"] is False
    assert result["error"]["status"] == 404
    assert result["error"]["message"] == "Not Found"


def test_live_raw_artifact_construction_with_mocked_responses():
    client = GitHubClient(api_base="https://api.github.test", transport=_transport_from(_routes()))
    row = {
        "instance_id": "live_1",
        "repo": "owner/repo",
        "pr_number": "5",
        "pr_url": "",
        "source": "live",
        "author_type": "unknown",
        "agent_name": "unknown",
        "task_type": "bug_fix",
        "language": "python",
        "outcome": "open",
        "sample_split": "pilot",
        "notes": "mocked",
    }

    raw = fetch_live_raw_pr(row, client)

    assert validate_data(raw, "github_pr_raw") == []
    assert raw["fetch_mode"] == "live"
    assert raw["pr_url"] == "https://github.com/owner/repo/pull/5"
    assert raw["linked_issues"][0]["number"] == 9
    assert {check["name"] for check in raw["checks"]} == {"pytest", "lint"}


def test_live_raw_artifact_records_partial_endpoint_failure():
    routes = _routes()
    routes["/pulls/5/files?per_page=100"] = (500, {}, {"message": "files endpoint failed"})
    client = GitHubClient(api_base="https://api.github.test", transport=_transport_from(routes))
    row = {
        "instance_id": "live_partial",
        "repo": "owner/repo",
        "pr_number": "5",
        "pr_url": "",
        "source": "live",
        "author_type": "unknown",
        "agent_name": "unknown",
        "task_type": "bug_fix",
        "language": "python",
        "outcome": "open",
        "sample_split": "pilot",
        "notes": "mocked partial failure",
    }

    raw = fetch_live_raw_pr(row, client)

    assert validate_data(raw, "github_pr_raw") == []
    assert raw["files"] == []
    assert any(error["status"] == 500 for error in raw["errors"])


class FakeLiveClient:
    calls = 0

    def __init__(self, token=None, api_base="https://api.github.com"):
        self.inner = GitHubClient(api_base="https://api.github.test", transport=_transport_from(_routes()))

    def fetch_pull_request(self, repo, pr_number):
        FakeLiveClient.calls += 1
        return self.inner.fetch_pull_request(repo, pr_number)

    def fetch_pull_commits(self, repo, pr_number):
        return self.inner.fetch_pull_commits(repo, pr_number)

    def fetch_pull_files(self, repo, pr_number):
        return self.inner.fetch_pull_files(repo, pr_number)

    def fetch_pull_reviews(self, repo, pr_number):
        return self.inner.fetch_pull_reviews(repo, pr_number)

    def fetch_pull_review_comments(self, repo, pr_number):
        return self.inner.fetch_pull_review_comments(repo, pr_number)

    def fetch_issue_comments(self, repo, issue_number):
        return self.inner.fetch_issue_comments(repo, issue_number)

    def fetch_linked_issues_best_effort(self, repo, pr_body, issue_comments=None):
        return self.inner.fetch_linked_issues_best_effort(repo, pr_body, issue_comments)

    def fetch_check_runs(self, repo, ref_sha):
        return self.inner.fetch_check_runs(repo, ref_sha)

    def fetch_statuses(self, repo, ref_sha):
        return self.inner.fetch_statuses(repo, ref_sha)


def _write_live_manifest(path: Path) -> None:
    fieldnames = [
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
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(
            {
                "instance_id": "live_1",
                "repo": "owner/repo",
                "pr_number": "5",
                "pr_url": "",
                "source": "live",
                "author_type": "unknown",
                "agent_name": "unknown",
                "task_type": "bug_fix",
                "language": "python",
                "outcome": "open",
                "sample_split": "pilot",
                "notes": "mocked live row",
            }
        )


def test_build_seed_corpus_live_with_mocked_client(monkeypatch, tmp_path):
    import mergedossier_bench.seed_builder as seed_builder

    FakeLiveClient.calls = 0
    monkeypatch.setattr(seed_builder, "GitHubClient", FakeLiveClient)
    manifest = tmp_path / "live_manifest.csv"
    _write_live_manifest(manifest)
    out = tmp_path / "seed_live"

    code = main(["build-seed-corpus", "--manifest", str(manifest), "--out", str(out), "--live"])

    assert code == 0
    assert FakeLiveClient.calls == 1
    assert validate_file(out / "raw" / "live_1.json", "github_pr_raw") == []
    assert validate_file(out / "dossiers" / "live_1.json", "dossier") == []


def test_live_caching_reuses_existing_raw_unless_force(monkeypatch, tmp_path):
    import mergedossier_bench.seed_builder as seed_builder

    FakeLiveClient.calls = 0
    monkeypatch.setattr(seed_builder, "GitHubClient", FakeLiveClient)
    manifest = tmp_path / "live_manifest.csv"
    _write_live_manifest(manifest)
    out = tmp_path / "seed_live"

    write_seed_corpus(str(manifest), out, live=True)
    first_calls = FakeLiveClient.calls
    write_seed_corpus(str(manifest), out, live=True)
    assert FakeLiveClient.calls == first_calls
    write_seed_corpus(str(manifest), out, live=True, force=True)
    assert FakeLiveClient.calls == first_calls + 1


def test_lint_seed_manifest_success_and_warnings_and_errors(tmp_path):
    assert main(["lint-seed-manifest", "--manifest", "data/manifests/seed_prs.csv"]) == 0
    assert main(["lint-seed-manifest", "--manifest", "data/manifests/real_pilot_template.csv"]) == 0

    bad = tmp_path / "bad.csv"
    bad.write_text(
        "instance_id,repo,pr_number,pr_url,source,author_type,agent_name,task_type,language,outcome,sample_split,notes\n"
        "bad,badrepo,nope,not-a-url,live,robot,unknown,bug_fix,python,open,pilot,\n",
        encoding="utf-8",
    )
    assert main(["lint-seed-manifest", "--manifest", str(bad)]) == 1


def test_live_generated_dossiers_work_with_summarize_and_annotation_export(tmp_path):
    manifest = tmp_path / "live_manifest.csv"
    _write_live_manifest(manifest)
    out = tmp_path / "seed_live"
    write_seed_corpus(str(manifest), out, live=True, github_client=FakeLiveClient())
    summary_out = tmp_path / "summary"
    tasks_out = tmp_path / "tasks.json"

    assert main(["summarize", "--dossiers", str(out / "dossiers"), "--out", str(summary_out)]) == 0
    assert main(["export-annotation-tasks", "--dossiers", str(out / "dossiers"), "--out", str(tasks_out)]) == 0
    assert json.loads((summary_out / "summary.json").read_text(encoding="utf-8"))["valid_dossiers"] == 1
    assert len(json.loads(tasks_out.read_text(encoding="utf-8"))) == 1
