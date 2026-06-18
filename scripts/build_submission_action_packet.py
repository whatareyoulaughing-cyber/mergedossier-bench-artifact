"""Build a user-facing action packet for the remaining submission blockers."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
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


def _copy_if_exists(src: Path, dst: Path) -> bool:
    if not src.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def build_submission_action_packet(root: Path, out_dir: Path) -> dict[str, Any]:
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    external_zip = root / "outputs/external_audit_handoff_20260617/MergeDossier-external-audit-handoff.zip"
    external_summary = _read_json(root / "outputs/external_audit_analysis_20260617/external_audit_summary.json")
    deposit_summary = _read_json(root / "outputs/zenodo_deposit_packet_20260617/deposit_packet_summary.json")
    dashboard = _read_json(root / "outputs/submission_blocker_dashboard_20260617/submission_blocker_dashboard.json")

    copied_external_zip = _copy_if_exists(
        external_zip,
        out_dir / "send_to_external_auditor" / external_zip.name,
    )
    handoff_dir = root / "outputs/external_audit_handoff_20260617/handoff_files"
    for name in ["EMAIL_TEMPLATE_TO_EXTERNAL_AUDITOR.md", "OPERATOR_QUICKSTART.md", "RETURN_INSTRUCTIONS_FOR_AUTHOR.md"]:
        _copy_if_exists(handoff_dir / name, out_dir / "send_to_external_auditor" / name)
    recruitment_dir = root / "outputs/external_audit_recruitment_20260617"
    for name in [
        "RECRUITMENT_MESSAGE_EN.md",
        "RECRUITMENT_MESSAGE_ZH.md",
        "RECRUITMENT_MESSAGE_ZH_WINDOWS.md",
        "AUTHOR_SEND_CHECKLIST.md",
        "AUDITOR_BOUNDARY_CARD.md",
    ]:
        _copy_if_exists(recruitment_dir / name, out_dir / "send_to_external_auditor" / "recruitment" / name)

    for name in [
        "zenodo_deposit_instructions.md",
        "SHA256SUMS.txt",
        "artifact_upload_manifest.csv",
        "zenodo_metadata_template.json",
        "public_release_checklist.md",
    ]:
        _copy_if_exists(root / "outputs/zenodo_deposit_packet_20260617" / name, out_dir / "archive_deposit" / name)

    status = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "action_required",
        "p0_actions": [
            {
                "name": "external_audit",
                "status": external_summary.get("status", "missing"),
                "blank_label_cells": len(external_summary.get("blank_label_cells", []))
                if isinstance(external_summary.get("blank_label_cells"), list)
                else None,
                "packet": _rel(out_dir / "send_to_external_auditor" / external_zip.name)
                if copied_external_zip
                else None,
                "done_when": "outputs/external_audit_analysis_20260617/external_audit_summary.json reports status=complete.",
            },
            {
                "name": "doi_and_public_url",
                "status": deposit_summary.get("status", "missing"),
                "doi_minted": bool(deposit_summary.get("doi_minted")),
                "public_repository_url_recorded": bool(deposit_summary.get("public_repository_url_recorded")),
                "archive_sha256": deposit_summary.get("archive_sha256"),
                "upload_archive": deposit_summary.get("archive_copy"),
                "done_when": "A real DOI and public repository URL are recorded with scripts/update_public_release_metadata.py.",
            },
        ],
        "dashboard_status": dashboard.get("status", "missing"),
        "dashboard_p0_open_count": dashboard.get("p0_open_count"),
    }

    (out_dir / "action_status.json").write_text(
        json.dumps(status, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    write_next_actions_zh(status, out_dir / "NEXT_ACTIONS_ZH.md")
    write_next_actions_zh(status, out_dir / "NEXT_ACTIONS_ZH_WINDOWS.md", encoding="utf-8-sig")
    write_after_commands(out_dir / "AFTER_COMPLETION_COMMANDS.ps1")
    return status


def write_next_actions_zh(status: dict[str, Any], out: Path, encoding: str = "utf-8") -> None:
    external = status["p0_actions"][0]
    deposit = status["p0_actions"][1]
    lines = [
        "# MergeDossier-Bench 投稿前剩余动作包",
        "",
        "当前判断：本地论文、代码、格式、匿名包和 claim 边界检查已经通过；距离更高投稿把握主要差两个外部动作。",
        "",
        "## 1. 先完成第二人/外部审计",
        "",
        f"- 要发送的压缩包：`{external.get('packet') or 'missing'}`",
        "- 可直接复制的中英招募话术在：`send_to_external_auditor/recruitment/`。",
        "- 发送对象：任何能独立阅读英文 PR/dossier 片段的人，不需要懂本项目代码。",
        "- 任务量：50 个 audit tasks。",
        "- 对方只需要填 workbook 里的下拉标签：`present`、`partially_present`、`missing`、`not_applicable`。",
        "- 对方不要看你的主标注 CSV、论文结果表、population results，避免被当前结果影响。",
        "",
        "收回 completed workbook 后运行：",
        "",
        "```powershell",
        "python scripts/check_external_audit_progress.py --audit <completed_external_audit_sheet.xlsx> --out outputs/external_audit_progress_20260617",
        "python scripts/check_external_audit_return.py --completed <completed_external_audit_sheet.xlsx> --out outputs/external_audit_analysis_20260617",
        "python scripts/check_submission_blockers.py --out outputs/submission_blocker_dashboard_20260617",
        "```",
        "",
        "只有当 `external_audit_summary.json` 显示 `status=complete` 时，才可以在论文或附录里引用外部审计结果。",
        "",
        "## 2. 发布 artifact DOI / public URL",
        "",
        f"- 上传包：`{deposit.get('upload_archive')}`",
        f"- SHA256：`{deposit.get('archive_sha256')}`",
        "- Zenodo 指令和 metadata 模板在：`archive_deposit/`",
        "- DOI 没 mint 之前，不要把 README/CITATION 里的 placeholder 当成完成状态。",
        "",
        "真实 DOI 和 public repo URL 出来后运行：",
        "",
        "```powershell",
        "python scripts/update_public_release_metadata.py --dry-run --doi <artifact-doi> --repo-url <public-repo-url> --paper-url <paper-url-or-doi> --author-name \"<public-author-name>\" --affiliation \"<public-affiliation>\"",
        "python scripts/update_public_release_metadata.py --doi <artifact-doi> --repo-url <public-repo-url> --paper-url <paper-url-or-doi> --author-name \"<public-author-name>\" --affiliation \"<public-affiliation>\"",
        "python scripts/check_paper_readiness.py --out outputs/paper_readiness_check_20260617_handoff_gap",
        "python scripts/build_anonymous_release_zip.py",
        "python scripts/check_anonymous_release.py --zip outputs/release/MergeDossier-Bench-anonymous-review.zip --out outputs/anonymous_release_check_20260617",
        "python scripts/build_zenodo_deposit_packet.py",
        "python scripts/check_submission_blockers.py --out outputs/submission_blocker_dashboard_20260617",
        "```",
        "",
        "## 3. 当前不能 claim 的内容",
        "",
        "- 不 claim patch correctness。",
        "- 不 claim mergeability。",
        "- 不 claim reviewer utility。",
        "- 不 claim AI-vs-human causal effects。",
        "- 不 claim all-GitHub population rates。",
        "- 外部审计完成前，不 claim inter-rater reliability 或 external agreement。",
        "",
        "## 4. 做完后的目标状态",
        "",
        "- Dashboard 中 P0 open count 应该降到 0。",
        "- Public metadata placeholders 应该消失。",
        "- Release checksum 和 Zenodo checksum 应该匹配。",
        "- Paper readiness、claim hygiene、anonymous release scan 都保持 pass。",
        "",
    ]
    out.write_text("\n".join(lines), encoding=encoding)


def write_after_commands(out: Path) -> None:
    lines = [
        "# Fill the placeholders before running.",
        "python scripts/check_external_audit_progress.py --audit <completed_external_audit_sheet.xlsx> --out outputs/external_audit_progress_20260617",
        "python scripts/check_external_audit_return.py --completed <completed_external_audit_sheet.xlsx> --out outputs/external_audit_analysis_20260617",
        "python scripts/update_public_release_metadata.py --dry-run --doi <artifact-doi> --repo-url <public-repo-url> --paper-url <paper-url-or-doi> --author-name \"<public-author-name>\" --affiliation \"<public-affiliation>\"",
        "python scripts/update_public_release_metadata.py --doi <artifact-doi> --repo-url <public-repo-url> --paper-url <paper-url-or-doi> --author-name \"<public-author-name>\" --affiliation \"<public-affiliation>\"",
        "python scripts/check_paper_readiness.py --out outputs/paper_readiness_check_20260617_handoff_gap",
        "python scripts/build_anonymous_release_zip.py",
        "python scripts/check_anonymous_release.py --zip outputs/release/MergeDossier-Bench-anonymous-review.zip --out outputs/anonymous_release_check_20260617",
        "python scripts/build_zenodo_deposit_packet.py",
        "python scripts/check_submission_blockers.py --out outputs/submission_blocker_dashboard_20260617",
        "",
    ]
    out.write_text("\n".join(lines), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a user-facing final submission action packet")
    parser.add_argument("--out", default="outputs/submission_action_packet_20260617")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = build_submission_action_packet(ROOT, ROOT / args.out)
    print(
        "Submission action packet written: "
        f"{args.out} (dashboard={result['dashboard_status']}, P0 open={result['dashboard_p0_open_count']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
