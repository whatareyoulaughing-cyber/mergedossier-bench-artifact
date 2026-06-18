"""Build a single author-side packet for the remaining 80%-confidence actions."""

from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _abs(root: Path, value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else root / path


def _rel(root: Path, path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _copy_file(root: Path, src: Path | None, dst: Path, packet_path: str) -> dict[str, Any]:
    if src is None or not src.exists():
        return {"source": _rel(root, src), "packet_path": packet_path, "copied": False, "bytes": 0}
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return {
        "source": _rel(root, src),
        "packet_path": packet_path,
        "copied": True,
        "bytes": dst.stat().st_size,
    }


def _write_zip(source_dir: Path, zip_path: Path) -> dict[str, Any]:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(source_dir.rglob("*")):
            if not path.is_file() or path == zip_path:
                continue
            rel = path.relative_to(source_dir).as_posix()
            archive.write(path, rel)
            rows.append({"path": rel, "bytes": path.stat().st_size})
    return {"zip_path": _rel(ROOT, zip_path), "zip_bytes": zip_path.stat().st_size, "file_count": len(rows), "files": rows}


def build_80_percent_push_packet(root: Path, out_dir: Path) -> dict[str, Any]:
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    gap = _read_json(root / "outputs/acceptance_probability_gap_report_20260617/acceptance_probability_gap_report.json")
    send_now = _read_json(root / "outputs/external_audit_send_now_20260617/send_now_manifest.json")
    publish_now = _read_json(root / "outputs/public_release_publish_now_20260617/publish_now_manifest.json")
    p0_dashboard = _read_json(root / "outputs/p0_execution_dashboard_20260617/p0_execution_dashboard.json")

    send_files = send_now.get("files") if isinstance(send_now.get("files"), dict) else {}
    publish_files = publish_now.get("copied_files") if isinstance(publish_now.get("copied_files"), dict) else {}
    publish_outputs = publish_now.get("outputs") if isinstance(publish_now.get("outputs"), dict) else {}

    copy_plan = {
        "external_audit/SEND_NOW_EMAIL_ZH.eml": _abs(root, send_files.get("email_zh_eml")),
        "external_audit/SEND_NOW_EMAIL_EN.eml": _abs(root, send_files.get("email_en_eml")),
        "external_audit/SEND_NOW_EMAIL_ZH_WINDOWS.md": _abs(root, send_files.get("email_zh_windows")),
        "external_audit/SEND_NOW_EMAIL_EN.md": _abs(root, send_files.get("email_en")),
        "external_audit/MergeDossier-external-audit-handoff.zip": _abs(root, send_now.get("handoff_zip_for_email")),
        "external_audit/ATTACHMENT_AND_RETURN_CHECKLIST.md": _abs(root, send_files.get("attachment_checklist")),
        "public_release/PUBLISH_NOW_CHECKLIST_ZH_WINDOWS.md": _abs(root, publish_outputs.get("checklist_zh")),
        "public_release/PUBLISH_NOW_CHECKLIST_EN.md": _abs(root, publish_outputs.get("checklist_en")),
        "public_release/POST_PUBLICATION_UPDATE.ps1": _abs(root, publish_outputs.get("post_publication_runner")),
        "public_release/ZENODO_COPY_FIELDS.md": _abs(root, publish_files.get("ZENODO_COPY_FIELDS.md")),
        "public_release/GITHUB_RELEASE_COPY_FIELDS.md": _abs(root, publish_files.get("GITHUB_RELEASE_COPY_FIELDS.md")),
        "public_release/SHA256SUMS.txt": _abs(root, publish_files.get("SHA256SUMS.txt")),
        "public_release/artifact_upload_manifest.csv": _abs(root, publish_files.get("artifact_upload_manifest.csv")),
        "public_release/files_to_upload/MergeDossier-Bench-anonymous-review.zip": _abs(root, publish_now.get("archive_to_upload")),
        "dashboard/P0_EXECUTION_DASHBOARD_ZH_WINDOWS.md": root
        / "outputs/p0_execution_dashboard_20260617/P0_EXECUTION_DASHBOARD_ZH_WINDOWS.md",
        "gap_report/acceptance_probability_gap_report.md": root
        / "outputs/acceptance_probability_gap_report_20260617/acceptance_probability_gap_report.md",
    }

    copied = {
        packet_path: _copy_file(root, src, out_dir / packet_path, packet_path)
        for packet_path, src in copy_plan.items()
    }
    missing = [path for path, item in copied.items() if not item["copied"]]
    status = "ready_to_execute_external_p0_actions" if not missing else "missing_required_files"

    start_here = render_start_here(status, gap, send_now, publish_now, p0_dashboard, missing)
    (out_dir / "START_HERE_80_PERCENT_ZH.md").write_text(start_here, encoding="utf-8")
    (out_dir / "START_HERE_80_PERCENT_ZH_WINDOWS.md").write_text(start_here, encoding="utf-8-sig")
    (out_dir / "OPEN_THIS_PACKET.ps1").write_text(render_open_packet_script(), encoding="utf-8")
    (out_dir / "public_release").mkdir(parents=True, exist_ok=True)
    (out_dir / "public_release/UPLOAD_FILE_POINTER.txt").write_text(
        "\n".join(
            [
                "Upload this artifact archive to Zenodo/GitHub release:",
                "public_release/files_to_upload/MergeDossier-Bench-anonymous-review.zip",
                f"SHA256: {publish_now.get('archive_sha256') or p0_dashboard.get('release_sha256')}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "p0_open_count": gap.get("p0_open_count"),
        "local_fail_count": gap.get("fail_count"),
        "release_sha256": publish_now.get("archive_sha256") or p0_dashboard.get("release_sha256"),
        "archive_to_upload": "public_release/files_to_upload/MergeDossier-Bench-anonymous-review.zip",
        "external_audit_attachment": "external_audit/MergeDossier-external-audit-handoff.zip",
        "copied_files": copied,
        "generated_files": {
            "START_HERE_80_PERCENT_ZH.md": True,
            "START_HERE_80_PERCENT_ZH_WINDOWS.md": True,
            "OPEN_THIS_PACKET.ps1": True,
            "public_release/UPLOAD_FILE_POINTER.txt": True,
        },
        "missing_files": missing,
        "claim_boundary": (
            "This packet only helps the author execute the remaining external actions. "
            "It does not complete the external audit, mint a DOI, publish a repository, "
            "or justify new empirical claims."
        ),
    }
    (out_dir / "80_percent_push_packet_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    zip_summary = _write_zip(out_dir, out_dir / "MergeDossier-80-percent-push-packet.zip")
    manifest["zip_summary"] = zip_summary
    (out_dir / "80_percent_push_packet_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest


def render_start_here(
    status: str,
    gap: dict[str, Any],
    send_now: dict[str, Any],
    publish_now: dict[str, Any],
    p0_dashboard: dict[str, Any],
    missing: list[str],
) -> str:
    return "\n".join(
        [
            "# 80% Push Packet",
            "",
            f"Status: `{status}`",
            f"Gap status: `{gap.get('status', 'missing')}`",
            f"P0 open: `{gap.get('p0_open_count')}`",
            f"Local fail count: `{gap.get('fail_count')}`",
            f"Release SHA256: `{publish_now.get('archive_sha256') or p0_dashboard.get('release_sha256')}`",
            "",
            "## 先做 1：发外部审计",
            "",
            "1. 优先打开 `external_audit/SEND_NOW_EMAIL_ZH.eml`，填收件人后发送。",
            "2. 附件必须是 `external_audit/MergeDossier-external-audit-handoff.zip`。",
            "3. 如果 `.eml` 打不开，复制 `external_audit/SEND_NOW_EMAIL_ZH_WINDOWS.md` 的正文发送。",
            "4. 收到返回表后，按 `external_audit/ATTACHMENT_AND_RETURN_CHECKLIST.md` 检查，然后运行外部审计分析脚本。",
            "",
            "## 再做 2：发布 DOI / Public URL",
            "",
            "1. 打开 `public_release/PUBLISH_NOW_CHECKLIST_ZH_WINDOWS.md`。",
            "2. 上传 `public_release/files_to_upload/MergeDossier-Bench-anonymous-review.zip`。",
            "3. 用 `public_release/ZENODO_COPY_FIELDS.md` 和 `public_release/GITHUB_RELEASE_COPY_FIELDS.md` 填写页面。",
            "4. 拿到真实 DOI / public URL 后，先 dry-run，再运行 `public_release/POST_PUBLICATION_UPDATE.ps1` 写回元数据。",
            "",
            "## 一键打开本 packet",
            "",
            "```powershell",
            ".\\OPEN_THIS_PACKET.ps1",
            "```",
            "",
            "## 当前状态不是完成",
            "",
            "- 这个 packet 只是执行材料。",
            "- 它不代表外部审计完成。",
            "- 它不代表 DOI 或 public repository 已发布。",
            "- 它不支持新增 correctness、mergeability、reviewer utility、AI-vs-human、all-GitHub 或 inter-rater reliability claim。",
            "",
            f"Missing required files: `{missing}`",
            f"Send-now status: `{send_now.get('status', 'missing')}`",
            f"Publish-now status: `{publish_now.get('status', 'missing')}`",
            "",
        ]
    )


def render_open_packet_script() -> str:
    return "\n".join(
        [
            "$ErrorActionPreference = 'Stop'",
            "# Opens the consolidated 80% push packet. No files are modified.",
            "Start-Process -FilePath '.\\START_HERE_80_PERCENT_ZH_WINDOWS.md'",
            "Start-Process -FilePath '.\\external_audit\\SEND_NOW_EMAIL_ZH.eml'",
            "Start-Process -FilePath '.\\external_audit\\MergeDossier-external-audit-handoff.zip'",
            "Start-Process -FilePath '.\\public_release\\PUBLISH_NOW_CHECKLIST_ZH_WINDOWS.md'",
            "Start-Process -FilePath '.\\public_release\\UPLOAD_FILE_POINTER.txt'",
            "Start-Process -FilePath '.\\public_release\\files_to_upload'",
            "Write-Host 'Opened the 80% push packet. Execute the two P0 actions manually.'",
            "",
        ]
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the consolidated 80%-confidence push packet")
    parser.add_argument("--out", default="outputs/80_percent_push_packet_20260617")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = build_80_percent_push_packet(ROOT, ROOT / args.out)
    print(f"80% push packet: {result['status']} -> {args.out}")
    return 0 if result["status"] == "ready_to_execute_external_p0_actions" else 2


if __name__ == "__main__":
    raise SystemExit(main())
