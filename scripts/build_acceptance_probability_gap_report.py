"""Build an evidence-backed gap report for high-confidence ICSE readiness.

The report answers the project-management question "what still separates the
current package from an 80%-style submission confidence posture?" It deliberately
does not estimate a calibrated acceptance probability.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


DEFAULT_DASHBOARD = ROOT / "outputs/submission_blocker_dashboard_20260617/submission_blocker_dashboard.json"
DEFAULT_READINESS = ROOT / "outputs/paper_readiness_check_20260617_handoff_gap/paper_readiness_check.json"
DEFAULT_EXTERNAL_AUDIT = ROOT / "outputs/external_audit_progress_20260617/external_audit_progress.json"
DEFAULT_EXTERNAL_AUDIT_INTAKE = ROOT / "outputs/external_audit_intake_20260617/external_audit_intake_report.json"
DEFAULT_EXTERNAL_AUDIT_SEND_NOW = ROOT / "outputs/external_audit_send_now_20260617/send_now_manifest.json"
DEFAULT_PUBLIC_RELEASE_PUBLISH_NOW = ROOT / "outputs/public_release_publish_now_20260617/publish_now_manifest.json"
DEFAULT_P0_EXECUTION_DASHBOARD = ROOT / "outputs/p0_execution_dashboard_20260617/p0_execution_dashboard.json"
DEFAULT_PREFLIGHT = ROOT / "outputs/public_release_preflight_20260617/public_release_preflight.json"
DEFAULT_RELEASE_SUMMARY = ROOT / "outputs/release/release_zip_summary.json"
DEFAULT_CHECKSUM = ROOT / "outputs/zenodo_deposit_packet_20260617/SHA256SUMS.txt"
DEFAULT_PAPER = ROOT / "paper/main.tex"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _display(path: Path, root: Path = ROOT) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _count_checks(checks: list[dict[str, Any]], *, severity: str, status: str | None = None) -> int:
    selected = [check for check in checks if check.get("severity") == severity]
    if status is not None:
        selected = [check for check in selected if check.get("status") == status]
    return len(selected)


def _p0_blockers(checks: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "name": str(check.get("name", "")),
            "status": str(check.get("status", "")),
            "evidence": str(check.get("evidence", "")),
            "action": str(check.get("action", "")),
        }
        for check in checks
        if check.get("severity") == "P0" and check.get("status") != "pass"
    ]


def _read_test_count(paper_path: Path) -> str:
    text = _read_text(paper_path)
    match = re.search(r"Tests\s*&\s*([0-9]+)\s+offline tests pass", text)
    if match:
        return f"{match.group(1)} offline tests pass"
    return "pytest gate pass recorded"


def _external_audit_summary(data: dict[str, Any]) -> dict[str, Any]:
    total = int(data.get("total_required_cells") or 0)
    valid = int(data.get("valid_label_cells") or 0)
    blank = data.get("blank_label_cells", [])
    blank_count = len(blank) if isinstance(blank, list) else int(data.get("blank_label_cell_count") or 0)
    completion_rate = round(valid / total, 4) if total else 0.0
    return {
        "status": data.get("status", "missing"),
        "selected_tasks": data.get("selected_tasks"),
        "rows_found": data.get("rows_found"),
        "complete_rows": data.get("complete_rows"),
        "total_required_cells": total,
        "valid_label_cells": valid,
        "blank_label_cells": blank_count,
        "completion_rate": completion_rate,
    }


def _status_from_counts(p0_open_count: int, fail_count: int) -> str:
    if fail_count:
        return "local_failures_present"
    if p0_open_count:
        return "local_ready_external_blocked"
    return "high_confidence_ready_after_external_actions"


def build_acceptance_probability_gap_report(
    *,
    root: Path = ROOT,
    dashboard_path: Path = DEFAULT_DASHBOARD,
    readiness_path: Path = DEFAULT_READINESS,
    external_audit_path: Path = DEFAULT_EXTERNAL_AUDIT,
    external_audit_intake_path: Path = DEFAULT_EXTERNAL_AUDIT_INTAKE,
    external_audit_send_now_path: Path = DEFAULT_EXTERNAL_AUDIT_SEND_NOW,
    public_release_publish_now_path: Path = DEFAULT_PUBLIC_RELEASE_PUBLISH_NOW,
    p0_execution_dashboard_path: Path = DEFAULT_P0_EXECUTION_DASHBOARD,
    preflight_path: Path = DEFAULT_PREFLIGHT,
    release_summary_path: Path = DEFAULT_RELEASE_SUMMARY,
    checksum_path: Path = DEFAULT_CHECKSUM,
    paper_path: Path = DEFAULT_PAPER,
    out_dir: Path,
) -> dict[str, Any]:
    dashboard = _read_json(dashboard_path)
    checks = dashboard.get("checks", [])
    if not isinstance(checks, list):
        checks = []

    fail_count = int(dashboard.get("fail_count") or _count_checks(checks, severity="P0", status="fail"))
    p0_open_count = int(dashboard.get("p0_open_count") or len(_p0_blockers(checks)))
    status = _status_from_counts(p0_open_count, fail_count)

    readiness = _read_json(readiness_path)
    audit = _external_audit_summary(_read_json(external_audit_path))
    intake = _read_json(external_audit_intake_path)
    send_now = _read_json(external_audit_send_now_path)
    publish_now = _read_json(public_release_publish_now_path)
    p0_dashboard = _read_json(p0_execution_dashboard_path)
    preflight = _read_json(preflight_path)
    release_summary = _read_json(release_summary_path)
    checksum_text = _read_text(checksum_path).strip()
    checksum = checksum_text.split()[0] if checksum_text.split() else None

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "interpretation": (
            "This is a readiness-risk gap report, not a calibrated acceptance probability. "
            "The package is locally strong but remains externally blocked until P0 actions are complete."
        ),
        "p0_open_count": p0_open_count,
        "fail_count": fail_count,
        "p1_pass_count": _count_checks(checks, severity="P1", status="pass"),
        "p1_open_count": _count_checks(checks, severity="P1", status="open"),
        "p0_blockers": _p0_blockers(checks),
        "local_evidence": {
            "paper_readiness_status": readiness.get("status", "missing"),
            "readiness_gate_count": len(readiness.get("records", [])) if isinstance(readiness.get("records"), list) else 0,
            "test_evidence": _read_test_count(paper_path),
            "release_zip_file_count": release_summary.get("file_count"),
            "release_zip_bytes": release_summary.get("zip_bytes"),
            "release_zip_sha256": checksum,
            "public_release_preflight_status": preflight.get("status", "missing"),
            "public_release_preflight_warnings": preflight.get("warning_count"),
            "dashboard_status": dashboard.get("status", "missing"),
        },
        "external_audit_progress": audit,
        "external_audit_intake": {
            "status": intake.get("status", "missing"),
            "candidate_count": intake.get("candidate_count"),
            "complete_candidate_count": intake.get("complete_candidate_count"),
            "ready_external_return_count": intake.get("ready_external_return_count"),
            "best_candidate": intake.get("best_candidate"),
            "next_action": intake.get("next_action"),
        },
        "external_audit_send_now": {
            "status": send_now.get("status", "missing"),
            "handoff_zip_for_email": send_now.get("handoff_zip_for_email"),
            "email_zh_windows": (send_now.get("files") or {}).get("email_zh_windows")
            if isinstance(send_now.get("files"), dict)
            else None,
            "email_en": (send_now.get("files") or {}).get("email_en")
            if isinstance(send_now.get("files"), dict)
            else None,
            "email_zh_eml": (send_now.get("files") or {}).get("email_zh_eml")
            if isinstance(send_now.get("files"), dict)
            else None,
            "email_en_eml": (send_now.get("files") or {}).get("email_en_eml")
            if isinstance(send_now.get("files"), dict)
            else None,
            "attachment_checklist": (send_now.get("files") or {}).get("attachment_checklist")
            if isinstance(send_now.get("files"), dict)
            else None,
        },
        "public_release_publish_now": {
            "status": publish_now.get("status", "missing"),
            "archive_to_upload": publish_now.get("archive_to_upload"),
            "archive_sha256": publish_now.get("archive_sha256"),
            "checklist_zh": (publish_now.get("outputs") or {}).get("checklist_zh")
            if isinstance(publish_now.get("outputs"), dict)
            else None,
            "post_publication_runner": (publish_now.get("outputs") or {}).get("post_publication_runner")
            if isinstance(publish_now.get("outputs"), dict)
            else None,
            "upload_pointer": (publish_now.get("outputs") or {}).get("upload_pointer")
            if isinstance(publish_now.get("outputs"), dict)
            else None,
        },
        "p0_execution_dashboard": {
            "status": p0_dashboard.get("status", "missing"),
            "dashboard_zh": "outputs/p0_execution_dashboard_20260617/P0_EXECUTION_DASHBOARD_ZH_WINDOWS.md",
            "open_script": "outputs/p0_execution_dashboard_20260617/OPEN_P0_ACTIONS.ps1",
            "missing_paths": p0_dashboard.get("missing_paths"),
        },
        "next_two_actions_zh": [
            "把 outputs/external_audit_send_now_20260617/SEND_NOW_EMAIL_ZH.eml 发给外部审计者，或使用同目录的 handoff zip + SEND_NOW_EMAIL_ZH_WINDOWS.md；收到完成表后运行外部 audit 分析脚本。",
            "按 outputs/public_release_publish_now_20260617/PUBLISH_NOW_CHECKLIST_ZH_WINDOWS.md 发布 artifact；拿到真实 DOI/public URL 后先 dry-run，再用 POST_PUBLICATION_UPDATE.ps1 写回元数据。",
        ],
        "non_claim_boundary": [
            "Do not claim patch correctness.",
            "Do not claim mergeability.",
            "Do not claim reviewer utility.",
            "Do not claim AI-vs-human effects.",
            "Do not claim all-GitHub population rates.",
            "Do not claim inter-rater reliability before the external audit is complete and analyzed.",
        ],
        "source_paths": {
            "dashboard": _display(dashboard_path, root),
            "readiness": _display(readiness_path, root),
            "external_audit_progress": _display(external_audit_path, root),
            "external_audit_intake": _display(external_audit_intake_path, root),
            "external_audit_send_now": _display(external_audit_send_now_path, root),
            "public_release_publish_now": _display(public_release_publish_now_path, root),
            "p0_execution_dashboard": _display(p0_execution_dashboard_path, root),
            "public_release_preflight": _display(preflight_path, root),
            "release_summary": _display(release_summary_path, root),
            "checksum": _display(checksum_path, root),
        },
    }

    result["next_two_actions_zh"] = [
        "把 outputs/external_audit_send_now_20260617/SEND_NOW_EMAIL_ZH.eml 发给外部审计者，或使用同目录的 handoff zip + SEND_NOW_EMAIL_ZH_WINDOWS.md；收到完成表后运行外部 audit 分析脚本。",
        "按 outputs/public_release_publish_now_20260617/PUBLISH_NOW_CHECKLIST_ZH_WINDOWS.md 发布 artifact；拿到真实 DOI/public URL 后先 dry-run，再用 POST_PUBLICATION_UPDATE.ps1 写回元数据。",
    ]

    result["next_two_actions_zh"] = [
        "\u628a outputs/external_audit_send_now_20260617/SEND_NOW_EMAIL_ZH.eml \u53d1\u7ed9\u5916\u90e8\u5ba1\u8ba1\u8005\uff0c\u6216\u4f7f\u7528\u540c\u76ee\u5f55\u7684 handoff zip + SEND_NOW_EMAIL_ZH_WINDOWS.md\uff1b\u6536\u5230\u5b8c\u6210\u8868\u540e\u8fd0\u884c\u5916\u90e8 audit \u5206\u6790\u811a\u672c\u3002",
        "\u6309 outputs/public_release_publish_now_20260617/PUBLISH_NOW_CHECKLIST_ZH_WINDOWS.md \u53d1\u5e03 artifact\uff1b\u62ff\u5230\u771f\u5b9e DOI/public URL \u540e\u5148 dry-run\uff0c\u518d\u7528 POST_PUBLICATION_UPDATE.ps1 \u5199\u56de\u5143\u6570\u636e\u3002",
    ]

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "acceptance_probability_gap_report.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (out_dir / "acceptance_probability_gap_report.md").write_text(
        _render_markdown(result),
        encoding="utf-8-sig",
    )
    next_actions = "\n".join(
        [
            "# Next Two Actions",
            "",
            "1. " + result["next_two_actions_zh"][0],
            "2. " + result["next_two_actions_zh"][1],
            "",
        ]
    )
    (out_dir / "NEXT_TWO_ACTIONS_ZH.md").write_text(next_actions, encoding="utf-8")
    (out_dir / "NEXT_TWO_ACTIONS_ZH_WINDOWS.md").write_text(next_actions, encoding="utf-8-sig")
    return result


def _render_markdown(result: dict[str, Any]) -> str:
    local = result["local_evidence"]
    audit = result["external_audit_progress"]
    intake = result["external_audit_intake"]
    send_now = result["external_audit_send_now"]
    publish_now = result["public_release_publish_now"]
    p0_dashboard = result["p0_execution_dashboard"]
    lines = [
        "# Acceptance-Confidence Gap Report",
        "",
        f"Overall status: **{result['status']}**",
        "",
        "This report answers what still separates the current package from an 80%-style high-confidence submission posture. It is **not a calibrated acceptance probability**.",
        "",
        "## Current Bottom Line",
        "",
        f"- P0 external blockers open: {result['p0_open_count']}",
        f"- Local fail count: {result['fail_count']}",
        f"- P1 local checks passing: {result['p1_pass_count']}",
        f"- Paper readiness: {local['paper_readiness_status']} ({local['readiness_gate_count']} gates)",
        f"- Test evidence: {local['test_evidence']}",
        f"- Release zip: {local['release_zip_file_count']} files, SHA256 `{local['release_zip_sha256']}`",
            f"- Public release preflight: {local['public_release_preflight_status']} ({local['public_release_preflight_warnings']} warnings)",
            "",
            "## P0 Execution Dashboard",
            "",
            f"- Status: {p0_dashboard['status']}",
            f"- Dashboard: `{p0_dashboard['dashboard_zh']}`",
            f"- Open script: `{p0_dashboard['open_script']}`",
            f"- Missing paths: `{p0_dashboard['missing_paths']}`",
            "",
            "## P0 Blockers",
        "",
        "| Blocker | Status | Evidence | Required Action |",
        "|---|---:|---|---|",
    ]
    for blocker in result["p0_blockers"]:
        lines.append(
            f"| {blocker['name']} | {blocker['status']} | {blocker['evidence']} | {blocker['action']} |"
        )
    lines.extend(
        [
            "",
            "## External Audit Progress",
            "",
            f"- Status: {audit['status']}",
            f"- Selected tasks: {audit['selected_tasks']}",
            f"- Complete rows: {audit['complete_rows']}",
            f"- Valid required cells: {audit['valid_label_cells']} / {audit['total_required_cells']}",
            f"- Blank required cells: {audit['blank_label_cells']}",
            f"- Completion rate: {audit['completion_rate']:.1%}",
            "",
            "## External Audit Intake Scan",
            "",
            f"- Status: {intake['status']}",
            f"- Candidate files scanned: {intake['candidate_count']}",
            f"- Complete-looking candidates: {intake['complete_candidate_count']}",
            f"- Ready external-return candidates: {intake['ready_external_return_count']}",
            f"- Next action: {intake['next_action']}",
            "",
            "## Send-Now Packet",
            "",
            f"- Status: {send_now['status']}",
            f"- Attachment: `{send_now['handoff_zip_for_email']}`",
            f"- Chinese .eml draft: `{send_now['email_zh_eml']}`",
            f"- English .eml draft: `{send_now['email_en_eml']}`",
            f"- Chinese email: `{send_now['email_zh_windows']}`",
            f"- English email: `{send_now['email_en']}`",
            f"- Checklist: `{send_now['attachment_checklist']}`",
            "",
            "## Publish-Now Packet",
            "",
            f"- Status: {publish_now['status']}",
            f"- Upload archive: `{publish_now['archive_to_upload']}`",
            f"- SHA256: `{publish_now['archive_sha256']}`",
            f"- Checklist: `{publish_now['checklist_zh']}`",
            f"- Post-publication runner: `{publish_now['post_publication_runner']}`",
            "",
            "## Next Two Actions",
            "",
        ]
    )
    for idx, action in enumerate(result["next_two_actions_zh"], start=1):
        lines.append(f"{idx}. {action}")
    lines.extend(
        [
            "",
            "## Non-Claim Boundary",
            "",
        ]
    )
    for item in result["non_claim_boundary"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Source Artifacts",
            "",
        ]
    )
    for key, value in result["source_paths"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="outputs/acceptance_probability_gap_report_20260617")
    parser.add_argument("--dashboard", default=str(DEFAULT_DASHBOARD))
    parser.add_argument("--readiness", default=str(DEFAULT_READINESS))
    parser.add_argument("--external-audit-progress", default=str(DEFAULT_EXTERNAL_AUDIT))
    parser.add_argument("--external-audit-intake", default=str(DEFAULT_EXTERNAL_AUDIT_INTAKE))
    parser.add_argument("--external-audit-send-now", default=str(DEFAULT_EXTERNAL_AUDIT_SEND_NOW))
    parser.add_argument("--public-release-publish-now", default=str(DEFAULT_PUBLIC_RELEASE_PUBLISH_NOW))
    parser.add_argument("--p0-execution-dashboard", default=str(DEFAULT_P0_EXECUTION_DASHBOARD))
    parser.add_argument("--public-release-preflight", default=str(DEFAULT_PREFLIGHT))
    parser.add_argument("--release-summary", default=str(DEFAULT_RELEASE_SUMMARY))
    parser.add_argument("--checksum", default=str(DEFAULT_CHECKSUM))
    parser.add_argument("--paper", default=str(DEFAULT_PAPER))
    args = parser.parse_args()

    result = build_acceptance_probability_gap_report(
        dashboard_path=Path(args.dashboard),
        readiness_path=Path(args.readiness),
        external_audit_path=Path(args.external_audit_progress),
        external_audit_intake_path=Path(args.external_audit_intake),
        external_audit_send_now_path=Path(args.external_audit_send_now),
        public_release_publish_now_path=Path(args.public_release_publish_now),
        p0_execution_dashboard_path=Path(args.p0_execution_dashboard),
        preflight_path=Path(args.public_release_preflight),
        release_summary_path=Path(args.release_summary),
        checksum_path=Path(args.checksum),
        paper_path=Path(args.paper),
        out_dir=Path(args.out),
    )
    print(f"Acceptance-confidence gap report: {result['status']} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
