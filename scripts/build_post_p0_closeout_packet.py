"""Build a parameterized closeout packet for the two remaining P0 actions."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def build_post_p0_closeout_packet(root: Path, out_dir: Path) -> dict[str, Any]:
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    dashboard = _read_json(root / "outputs/submission_blocker_dashboard_20260617/submission_blocker_dashboard.json")
    gap_report = _read_json(root / "outputs/acceptance_probability_gap_report_20260617/acceptance_probability_gap_report.json")
    deposit_summary = _read_json(root / "outputs/zenodo_deposit_packet_20260617/deposit_packet_summary.json")
    external_progress = _read_json(root / "outputs/external_audit_progress_20260617/external_audit_progress.json")

    status = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "waiting_for_external_inputs",
        "dashboard_status": dashboard.get("status", "missing"),
        "dashboard_p0_open_count": dashboard.get("p0_open_count"),
        "gap_report_status": gap_report.get("status", "missing"),
        "external_audit_status": external_progress.get("status", "missing"),
        "external_audit_blank_label_cells": len(external_progress.get("blank_label_cells", []))
        if isinstance(external_progress.get("blank_label_cells"), list)
        else external_progress.get("blank_label_cells"),
        "doi_minted": bool(deposit_summary.get("doi_minted")),
        "public_repository_url_recorded": bool(deposit_summary.get("public_repository_url_recorded")),
        "release_zip_sha256": deposit_summary.get("archive_sha256"),
        "outputs": {
            "runner": _rel(out_dir / "POST_P0_FINALIZE.ps1"),
            "checklist": _rel(out_dir / "POST_P0_CLOSEOUT_CHECKLIST_ZH.md"),
        },
    }

    (out_dir / "post_p0_closeout_status.json").write_text(
        json.dumps(status, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (out_dir / "POST_P0_FINALIZE.ps1").write_text(render_powershell_runner(), encoding="utf-8")
    checklist = render_checklist(status)
    (out_dir / "POST_P0_CLOSEOUT_CHECKLIST_ZH.md").write_text(checklist, encoding="utf-8")
    (out_dir / "POST_P0_CLOSEOUT_CHECKLIST_ZH_WINDOWS.md").write_text(checklist, encoding="utf-8-sig")
    return status


def render_powershell_runner() -> str:
    return "\n".join(
        [
            "param(",
            "  [Parameter(Mandatory=$true)][string]$CompletedAudit,",
            "  [Parameter(Mandatory=$true)][string]$Doi,",
            "  [Parameter(Mandatory=$true)][string]$RepoUrl,",
            "  [Parameter(Mandatory=$true)][string]$PaperUrl,",
            "  [Parameter(Mandatory=$true)][string]$AuthorName,",
            "  [Parameter(Mandatory=$true)][string]$Affiliation,",
            "  [switch]$ApplyMetadata",
            ")",
            "",
            "$ErrorActionPreference = 'Stop'",
            "",
            "python scripts/check_external_audit_progress.py --audit $CompletedAudit --out outputs/external_audit_progress_20260617",
            "python scripts/check_external_audit_return.py --completed $CompletedAudit --out outputs/external_audit_analysis_20260617",
            "",
            "$metadataArgs = @(",
            "  '--doi', $Doi,",
            "  '--repo-url', $RepoUrl,",
            "  '--paper-url', $PaperUrl,",
            "  '--author-name', $AuthorName,",
            "  '--affiliation', $Affiliation",
            ")",
            "",
            "python scripts/update_public_release_metadata.py --dry-run @metadataArgs --preview-out outputs/public_release_metadata_dry_run_20260617",
            "if ($ApplyMetadata) {",
            "  python scripts/update_public_release_metadata.py @metadataArgs",
            "} else {",
            "  Write-Host 'Dry-run complete. Re-run with -ApplyMetadata after checking outputs/public_release_metadata_dry_run_20260617.'",
            "  exit 0",
            "}",
            "",
            "python scripts/check_paper_readiness.py --out outputs/paper_readiness_check_20260617_handoff_gap",
            "python scripts/build_anonymous_release_zip.py",
            "python scripts/check_anonymous_release.py --zip outputs/release/MergeDossier-Bench-anonymous-review.zip --out outputs/anonymous_release_check_20260617",
            "python scripts/check_release_zip_smoke.py",
            "python scripts/build_zenodo_deposit_packet.py",
            "python scripts/check_public_release_preflight.py",
            "python scripts/check_submission_blockers.py --out outputs/submission_blocker_dashboard_20260617",
            "python scripts/build_icse_submission_packet.py",
            "python scripts/check_icse_submission_packet.py",
            "python scripts/build_acceptance_probability_gap_report.py --out outputs/acceptance_probability_gap_report_20260617",
            "",
            "Write-Host 'Post-P0 closeout complete. Check outputs/submission_blocker_dashboard_20260617 and outputs/acceptance_probability_gap_report_20260617.'",
            "",
        ]
    )


def render_checklist(status: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Post-P0 Closeout Checklist",
            "",
            "用途：当外部审计表已经返回、Zenodo/GitHub 已经有真实 DOI/public URL 后，用这个 packet 做最后收口。",
            "",
            "## 当前状态",
            "",
            f"- Dashboard: `{status['dashboard_status']}`",
            f"- P0 open count: `{status['dashboard_p0_open_count']}`",
            f"- Gap report: `{status['gap_report_status']}`",
            f"- External audit status: `{status['external_audit_status']}`",
            f"- Blank audit cells: `{status['external_audit_blank_label_cells']}`",
            f"- DOI minted: `{status['doi_minted']}`",
            f"- Public repository URL recorded: `{status['public_repository_url_recorded']}`",
            f"- Current release SHA256: `{status['release_zip_sha256']}`",
            "",
            "## 第一步：只做 dry-run",
            "",
            "```powershell",
            ".\\outputs\\post_p0_closeout_20260617\\POST_P0_FINALIZE.ps1 \\",
            "  -CompletedAudit \"C:\\path\\to\\completed_external_audit_sheet.xlsx\" \\",
            "  -Doi \"10.5281/zenodo.xxxxx\" \\",
            "  -RepoUrl \"https://github.com/<org>/<repo>\" \\",
            "  -PaperUrl \"https://doi.org/<paper-doi-or-placeholder>\" \\",
            "  -AuthorName \"<public author name>\" \\",
            "  -Affiliation \"<public affiliation>\"",
            "```",
            "",
            "检查 `outputs/public_release_metadata_dry_run_20260617/`，确认 DOI、repo URL、作者和单位都是真的。",
            "",
            "## 第二步：确认无误后写回元数据",
            "",
            "```powershell",
            ".\\outputs\\post_p0_closeout_20260617\\POST_P0_FINALIZE.ps1 \\",
            "  -CompletedAudit \"C:\\path\\to\\completed_external_audit_sheet.xlsx\" \\",
            "  -Doi \"10.5281/zenodo.xxxxx\" \\",
            "  -RepoUrl \"https://github.com/<org>/<repo>\" \\",
            "  -PaperUrl \"https://doi.org/<paper-doi-or-placeholder>\" \\",
            "  -AuthorName \"<public author name>\" \\",
            "  -Affiliation \"<public affiliation>\" \\",
            "  -ApplyMetadata",
            "```",
            "",
            "## 完成标准",
            "",
            "- `outputs/external_audit_analysis_20260617/external_audit_summary.json` reports `status=complete`.",
            "- `outputs/zenodo_deposit_packet_20260617/deposit_packet_summary.json` records `doi_minted=true` and `public_repository_url_recorded=true`.",
            "- `outputs/submission_blocker_dashboard_20260617/submission_blocker_dashboard.json` has `p0_open_count=0`.",
            "- `outputs/acceptance_probability_gap_report_20260617/acceptance_probability_gap_report.json` no longer reports `local_ready_external_blocked`.",
            "- Paper readiness, anonymous release scan, release-zip smoke, and ICSE submission packet check remain pass.",
            "",
            "边界：即使 closeout 通过，也不要新增 correctness、mergeability、reviewer utility、AI-vs-human、all-GitHub 或未经分析的 inter-rater reliability claim。",
            "",
        ]
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a post-P0 closeout packet")
    parser.add_argument("--out", default="outputs/post_p0_closeout_20260617")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = build_post_p0_closeout_packet(ROOT, ROOT / args.out)
    print(
        "Post-P0 closeout packet written: "
        f"{args.out} (dashboard={result['dashboard_status']}, P0 open={result['dashboard_p0_open_count']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
