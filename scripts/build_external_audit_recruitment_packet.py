"""Build send-ready recruitment materials for the external audit slice."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "outputs" / "external_audit_recruitment_20260617"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _write(path: Path, lines: list[str], encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding=encoding)


def build_external_audit_recruitment_packet(root: Path, out_dir: Path) -> dict[str, Any]:
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    handoff_zip = root / "outputs/external_audit_handoff_20260617/MergeDossier-external-audit-handoff.zip"
    audit_summary = _read_json(root / "outputs/external_audit_analysis_20260617/external_audit_summary.json")
    handoff_summary = _read_json(root / "outputs/external_audit_handoff_20260617/external_auditor_handoff_summary.json")
    blank_cells = audit_summary.get("blank_label_cells", [])
    blank_count = len(blank_cells) if isinstance(blank_cells, list) else None

    status = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "ready_to_send" if handoff_zip.exists() else "missing_handoff_zip",
        "handoff_zip": _rel(handoff_zip, root) if handoff_zip.exists() else None,
        "handoff_zip_bytes": handoff_zip.stat().st_size if handoff_zip.exists() else None,
        "handoff_file_count": handoff_summary.get("file_count"),
        "external_audit_status": audit_summary.get("status", "missing"),
        "blank_label_cells": blank_count,
        "claim_boundary": (
            "Recruitment materials only. They do not establish external agreement until a completed "
            "external audit sheet is returned and analyzed as complete."
        ),
    }

    attachment = status["handoff_zip"] or "outputs/external_audit_handoff_20260617/MergeDossier-external-audit-handoff.zip"
    _write(
        out_dir / "RECRUITMENT_MESSAGE_EN.md",
        [
            "# Recruitment Message EN",
            "",
            "Subject: Quick independent audit request for an ICSE paper artifact",
            "",
            "Hi <name>,",
            "",
            "Could you help with a small independent audit for my ICSE paper artifact?",
            "The task is to open the attached workbook and code 50 short PR/dossier records using dropdown labels.",
            "It does not require running code or understanding this project internals.",
            "",
            "What I need:",
            "",
            "- Open `external_audit_sheet.xlsx` from the attached zip.",
            "- Fill every `_label` column with one of: `present`, `partially_present`, `missing`, or `not_applicable`.",
            "- Add a short comment only when a case is ambiguous.",
            "- Do not judge whether the patch is correct, mergeable, useful to reviewers, or better/worse than human PRs.",
            "- Do not look at my completed primary audit sheet or paper result tables.",
            "",
            "Estimated time: about 60-90 minutes, depending on how much detail you read.",
            "Return format: send back the completed `external_audit_sheet.xlsx`.",
            "",
            f"Attachment to send: `{attachment}`",
            "",
            "Thank you!",
            "",
        ],
    )
    _write(
        out_dir / "RECRUITMENT_MESSAGE_ZH.md",
        [
            "# 招募消息 ZH",
            "",
            "主题：能否帮我做一个 ICSE 论文 artifact 的小型独立 audit？",
            "",
            "你好 <name>，",
            "",
            "我想请你帮我做一个很小的独立外部审计，用来降低论文里 single-operator audit 的风险。",
            "任务是打开附件里的 workbook，给 50 条 PR/dossier 记录打下拉标签。",
            "不需要运行代码，也不需要懂这个项目内部实现。",
            "",
            "具体需要你做：",
            "",
            "- 打开附件 zip 里的 `external_audit_sheet.xlsx`。",
            "- 在 `Annotation` sheet 里，把所有 `_label` 列填成：`present`、`partially_present`、`missing`、或 `not_applicable`。",
            "- 如果某条很模糊，可以简单写一句 comment。",
            "- 不需要判断代码是否正确、能否 merge、reviewer 是否会喜欢，也不比较 AI PR 和 human PR。",
            "- 请不要看我的主标注 CSV、论文结果表或 population results，避免被结果影响。",
            "",
            "预计时间：大约 60-90 分钟。",
            "返回方式：把填好的 `external_audit_sheet.xlsx` 发回给我即可。",
            "",
            f"要发送的附件：`{attachment}`",
            "",
            "谢谢！",
            "",
        ],
    )
    _write(
        out_dir / "RECRUITMENT_MESSAGE_ZH_WINDOWS.md",
        (out_dir / "RECRUITMENT_MESSAGE_ZH.md").read_text(encoding="utf-8").splitlines(),
        encoding="utf-8-sig",
    )
    _write(
        out_dir / "AUTHOR_SEND_CHECKLIST.md",
        [
            "# Author Send Checklist",
            "",
            "Before sending:",
            "",
            f"- Confirm the attachment exists: `{attachment}`.",
            "- Send only the external-auditor handoff zip, not the primary completed annotation CSV.",
            "- Do not send `outputs/population_results_20260616/` or paper result tables to the auditor.",
            "- Ask the auditor to return the completed workbook, preferably `external_audit_sheet.xlsx`.",
            "- Give a concrete deadline, for example 48 hours or one weekend.",
            "",
            "After receiving the completed workbook:",
            "",
            "```powershell",
            "python scripts/check_external_audit_return.py --completed <completed_external_audit_sheet.xlsx> --out outputs/external_audit_analysis_20260617",
            "python scripts/check_submission_blockers.py --out outputs/submission_blocker_dashboard_20260617",
            "```",
            "",
            "Only cite the external-audit result if `external_audit_summary.json` reports `status=complete`.",
            "",
        ],
    )
    _write(
        out_dir / "AUDITOR_BOUNDARY_CARD.md",
        [
            "# Auditor Boundary Card",
            "",
            "The external audit codes visible review-evidence availability only.",
            "",
            "The auditor is not asked to judge:",
            "",
            "- patch correctness,",
            "- mergeability,",
            "- reviewer utility,",
            "- AI-vs-human effects,",
            "- all-GitHub population rates,",
            "- paper acceptance likelihood.",
            "",
            "The result remains uncitable until the completed sheet passes the external-audit return checker.",
            "",
        ],
    )
    (out_dir / "recruitment_status.json").write_text(
        json.dumps(status, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build external-audit recruitment materials")
    parser.add_argument("--out", default=str(DEFAULT_OUT.relative_to(ROOT)))
    args = parser.parse_args(argv)
    status = build_external_audit_recruitment_packet(ROOT, ROOT / args.out)
    print(f"External audit recruitment packet: {status['status']} -> {args.out}")
    return 0 if status["status"] == "ready_to_send" else 1


if __name__ == "__main__":
    raise SystemExit(main())
