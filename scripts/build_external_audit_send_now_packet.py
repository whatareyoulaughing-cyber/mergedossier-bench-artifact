"""Build a minimal send-now packet for the external audit P0 action."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
from email.message import EmailMessage
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _copy(src: Path, dst: Path) -> bool:
    if not src.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def build_external_audit_send_now_packet(root: Path, out_dir: Path) -> dict[str, Any]:
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    handoff_zip = root / "outputs/external_audit_handoff_20260617/MergeDossier-external-audit-handoff.zip"
    copied_zip = out_dir / handoff_zip.name
    copied = _copy(handoff_zip, copied_zip)

    files = {
        "email_zh": out_dir / "SEND_NOW_EMAIL_ZH.md",
        "email_zh_windows": out_dir / "SEND_NOW_EMAIL_ZH_WINDOWS.md",
        "email_en": out_dir / "SEND_NOW_EMAIL_EN.md",
        "email_zh_eml": out_dir / "SEND_NOW_EMAIL_ZH.eml",
        "email_en_eml": out_dir / "SEND_NOW_EMAIL_EN.eml",
        "follow_up_24h_zh": out_dir / "FOLLOW_UP_24H_ZH.md",
        "follow_up_48h_zh": out_dir / "FOLLOW_UP_48H_ZH.md",
        "attachment_checklist": out_dir / "ATTACHMENT_AND_RETURN_CHECKLIST.md",
    }
    email_zh = render_email_zh(copied_zip if copied else handoff_zip)
    files["email_zh"].write_text(email_zh, encoding="utf-8")
    files["email_zh_windows"].write_text(email_zh, encoding="utf-8-sig")
    email_en = render_email_en(copied_zip if copied else handoff_zip)
    files["email_en"].write_text(email_en, encoding="utf-8")
    if copied:
        write_eml(
            files["email_zh_eml"],
            subject="能否帮我做一个 50-task ICSE artifact 外部审计？",
            body=strip_markdown_header(email_zh),
            attachment=copied_zip,
        )
        write_eml(
            files["email_en_eml"],
            subject="50-task external audit slice for an ICSE artifact paper",
            body=strip_markdown_header(email_en),
            attachment=copied_zip,
        )
    files["follow_up_24h_zh"].write_text(render_follow_up_zh(hours=24), encoding="utf-8")
    files["follow_up_48h_zh"].write_text(render_follow_up_zh(hours=48), encoding="utf-8")
    files["attachment_checklist"].write_text(render_checklist(copied_zip if copied else handoff_zip), encoding="utf-8")

    status = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "ready_to_send" if copied else "missing_handoff_zip",
        "handoff_zip_source": _rel(handoff_zip),
        "handoff_zip_copied": copied,
        "handoff_zip_for_email": _rel(copied_zip if copied else handoff_zip),
        "files": {key: _rel(path) for key, path in files.items()},
        "eml_files_available": copied,
        "send_boundary": (
            "Send-now packet only. It does not complete the external audit and must not be cited "
            "until a completed return passes check_external_audit_return.py."
        ),
    }
    (out_dir / "send_now_manifest.json").write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return status


def render_email_zh(attachment: Path) -> str:
    return "\n".join(
        [
            "# 直接发送邮件 ZH",
            "",
            "主题：能否帮我做一个 50-task ICSE artifact 外部审计？",
            "",
            "你好 <name>，",
            "",
            "我想请你帮我做一个独立外部审计，用来降低一篇 ICSE paper 里 single-operator audit 的风险。",
            "任务很具体：打开附件 zip 里的 `external_audit_sheet.xlsx`，给 50 条 PR/dossier 记录选择下拉标签。",
            "",
            "你只需要判断可见 review evidence 是否存在：",
            "",
            "- `present`",
            "- `partially_present`",
            "- `missing`",
            "- `not_applicable`",
            "",
            "不需要运行代码，不需要判断代码是否正确、能否 merge，也不需要比较 AI 和 human。",
            "请不要看我的主标注 CSV、论文结果表或 population results，避免被当前结果影响。",
            "",
            "预计时间：60-90 分钟。",
            "返回方式：把填好的 `external_audit_sheet.xlsx` 发回给我即可。",
            "",
            f"附件：`{_rel(attachment)}`",
            "",
            "非常感谢！",
            "",
        ]
    )


def strip_markdown_header(text: str) -> str:
    lines = text.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    while lines and not lines[0].strip():
        lines = lines[1:]
    return "\n".join(lines).strip() + "\n"


def write_eml(out: Path, *, subject: str, body: str, attachment: Path) -> None:
    message = EmailMessage()
    message["To"] = "<external-auditor-email>"
    message["Subject"] = subject
    message.set_content(body)
    message.add_attachment(
        attachment.read_bytes(),
        maintype="application",
        subtype="zip",
        filename=attachment.name,
    )
    out.write_bytes(message.as_bytes(policy=message.policy.clone(max_line_length=78)))


def render_email_en(attachment: Path) -> str:
    return "\n".join(
        [
            "# Send-Now Email EN",
            "",
            "Subject: 50-task external audit slice for an ICSE artifact paper",
            "",
            "Hi <name>,",
            "",
            "Could you help independently code a 50-task external audit slice for my ICSE artifact paper?",
            "The task is to open `external_audit_sheet.xlsx` inside the attached zip and choose dropdown labels for visible review evidence.",
            "",
            "Use only these audit codes: `present`, `partially_present`, `missing`, or `not_applicable`.",
            "Please do not judge code correctness, mergeability, reviewer utility, or AI-vs-human differences.",
            "Also, please do not look at my primary annotation CSV, paper result tables, or population-results folder.",
            "",
            "Estimated time: 60-90 minutes.",
            "Return: send back the completed `external_audit_sheet.xlsx`.",
            "",
            f"Attachment: `{_rel(attachment)}`",
            "",
            "Thank you!",
            "",
        ]
    )


def render_follow_up_zh(*, hours: int) -> str:
    return "\n".join(
        [
            f"# {hours} 小时提醒 ZH",
            "",
            "主题：小提醒：ICSE artifact 外部审计 workbook",
            "",
            "你好 <name>，",
            "",
            "打扰一下，提醒一下之前发你的 50-task external audit workbook。",
            "如果你没时间做完整 50 条，也请直接告诉我；我会另找人，没关系。",
            "",
            "如果已经完成，请把填好的 `external_audit_sheet.xlsx` 发回即可。",
            "",
            "谢谢！",
            "",
        ]
    )


def render_checklist(attachment: Path) -> str:
    return "\n".join(
        [
            "# External Audit Send Checklist",
            "",
            "Before sending:",
            "",
            f"- Attach `{_rel(attachment)}`.",
            "- Send either `SEND_NOW_EMAIL_ZH.md` or `SEND_NOW_EMAIL_EN.md`.",
            "- Do not attach primary annotation CSVs or paper result tables.",
            "- Ask the operator to return only the completed `external_audit_sheet.xlsx`.",
            "",
            "After return:",
            "",
            "```powershell",
            "python scripts/check_external_audit_progress.py --audit <completed_external_audit_sheet.xlsx> --out outputs/external_audit_progress_20260617",
            "python scripts/check_external_audit_return.py --completed <completed_external_audit_sheet.xlsx> --out outputs/external_audit_analysis_20260617",
            "python scripts/check_submission_blockers.py --out outputs/submission_blocker_dashboard_20260617",
            "python scripts/build_acceptance_probability_gap_report.py --out outputs/acceptance_probability_gap_report_20260617",
            "```",
            "",
            "Claim boundary: do not claim external agreement until `external_audit_summary.json` reports `status=complete`.",
            "",
        ]
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a send-now packet for the external audit")
    parser.add_argument("--out", default="outputs/external_audit_send_now_20260617")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = build_external_audit_send_now_packet(ROOT, ROOT / args.out)
    print(f"External audit send-now packet: {result['status']} -> {args.out}")
    return 0 if result["status"] == "ready_to_send" else 2


if __name__ == "__main__":
    raise SystemExit(main())
