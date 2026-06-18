"""Build a single author-side dashboard for executing the remaining P0 actions."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
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


def _abs(root: Path, value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else root / path


def build_p0_execution_dashboard(root: Path, out_dir: Path) -> dict[str, Any]:
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    gap = _read_json(root / "outputs/acceptance_probability_gap_report_20260617/acceptance_probability_gap_report.json")
    send_now = _read_json(root / "outputs/external_audit_send_now_20260617/send_now_manifest.json")
    publish_now = _read_json(root / "outputs/public_release_publish_now_20260617/publish_now_manifest.json")

    send_files = send_now.get("files") if isinstance(send_now.get("files"), dict) else {}
    publish_outputs = publish_now.get("outputs") if isinstance(publish_now.get("outputs"), dict) else {}
    paths = {
        "audit_email_eml": _abs(root, send_files.get("email_zh_eml")),
        "audit_email_text": _abs(root, send_files.get("email_zh_windows")),
        "audit_attachment": _abs(root, send_now.get("handoff_zip_for_email")),
        "audit_checklist": _abs(root, send_files.get("attachment_checklist")),
        "publish_checklist": _abs(root, publish_outputs.get("checklist_zh")),
        "publish_upload_pointer": _abs(root, publish_outputs.get("upload_pointer")),
        "publish_upload_archive": _abs(root, publish_now.get("archive_to_upload")),
        "post_publication_runner": _abs(root, publish_outputs.get("post_publication_runner")),
    }
    path_status = {
        key: {
            "path": _rel(path) if path else None,
            "exists": bool(path and path.exists()),
        }
        for key, path in paths.items()
    }
    missing = [key for key, item in path_status.items() if not item["exists"]]
    status = "ready_to_execute_p0_actions" if not missing else "missing_p0_execution_files"

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "gap_status": gap.get("status", "missing"),
        "p0_open_count": gap.get("p0_open_count"),
        "fail_count": gap.get("fail_count"),
        "audit_send_status": send_now.get("status", "missing"),
        "publish_status": publish_now.get("status", "missing"),
        "release_sha256": publish_now.get("archive_sha256"),
        "paths": path_status,
        "missing_paths": missing,
        "claim_boundary": (
            "Execution dashboard only. Opening these files does not complete the external audit, "
            "mint a DOI, publish a repository, or justify new empirical claims."
        ),
    }

    (out_dir / "p0_execution_dashboard.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    dashboard = render_dashboard(result)
    (out_dir / "P0_EXECUTION_DASHBOARD_ZH.md").write_text(dashboard, encoding="utf-8")
    (out_dir / "P0_EXECUTION_DASHBOARD_ZH_WINDOWS.md").write_text(dashboard, encoding="utf-8-sig")
    (out_dir / "OPEN_P0_ACTIONS.ps1").write_text(render_open_script(paths), encoding="utf-8")
    return result


def render_dashboard(result: dict[str, Any]) -> str:
    paths = result["paths"]
    return "\n".join(
        [
            "# P0 Execution Dashboard",
            "",
            f"Status: `{result['status']}`",
            f"Gap status: `{result['gap_status']}`",
            f"P0 open: `{result['p0_open_count']}`",
            f"Local fail count: `{result['fail_count']}`",
            "",
            "## 1. 外部审计，立刻发送",
            "",
            f"- 首选：打开 `{paths['audit_email_eml']['path']}`，填收件人后发送。",
            f"- 如果 `.eml` 打不开：复制 `{paths['audit_email_text']['path']}`，附件用 `{paths['audit_attachment']['path']}`。",
            f"- 回收说明：`{paths['audit_checklist']['path']}`。",
            "",
            "## 2. DOI / Public URL，立刻发布",
            "",
            f"- 发布清单：`{paths['publish_checklist']['path']}`。",
            f"- 上传文件指针：`{paths['publish_upload_pointer']['path']}`。",
            f"- 上传 archive：`{paths['publish_upload_archive']['path']}`。",
            f"- 当前 SHA256：`{result['release_sha256']}`。",
            f"- DOI/public URL 出来后运行：`{paths['post_publication_runner']['path']}`。",
            "",
            "## 一键打开",
            "",
            "```powershell",
            ".\\outputs\\p0_execution_dashboard_20260617\\OPEN_P0_ACTIONS.ps1",
            "```",
            "",
            "## Boundary",
            "",
            result["claim_boundary"],
            "",
        ]
    )


def render_open_script(paths: dict[str, Path | None]) -> str:
    def line(path: Path | None) -> str:
        if path is None:
            return ""
        return f"if (Test-Path -LiteralPath '{path}') {{ Start-Process -FilePath '{path}' }}"

    upload_archive = paths.get("publish_upload_archive")
    upload_dir = upload_archive.parent if upload_archive else None
    lines = [
        "$ErrorActionPreference = 'Stop'",
        "# Opens the two remaining P0 action surfaces. No files are modified.",
        line(paths.get("audit_email_eml")),
        line(paths.get("audit_email_text")),
        line(paths.get("audit_attachment")),
        line(paths.get("publish_checklist")),
        line(paths.get("publish_upload_pointer")),
        line(upload_dir),
        "",
        "Write-Host 'Opened P0 action files. Send the external-audit email and publish the archive manually.'",
        "",
    ]
    return "\n".join(value for value in lines if value is not None)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the P0 execution dashboard")
    parser.add_argument("--out", default="outputs/p0_execution_dashboard_20260617")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = build_p0_execution_dashboard(ROOT, ROOT / args.out)
    print(f"P0 execution dashboard: {result['status']} -> {args.out}")
    return 0 if result["status"] == "ready_to_execute_p0_actions" else 2


if __name__ == "__main__":
    raise SystemExit(main())
