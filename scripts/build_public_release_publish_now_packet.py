"""Build a publish-now packet for the DOI/public-URL P0 action."""

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


def build_public_release_publish_now_packet(root: Path, out_dir: Path) -> dict[str, Any]:
    if not out_dir.is_absolute():
        out_dir = root / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    deposit_dir = root / "outputs/zenodo_deposit_packet_20260617"
    summary_path = deposit_dir / "deposit_packet_summary.json"
    summary = _read_json(summary_path)
    archive_path = root / str(summary.get("archive_copy", ""))
    archive_exists = archive_path.exists()

    copied_files: dict[str, str] = {}
    for name in [
        "ZENODO_COPY_FIELDS.md",
        "GITHUB_RELEASE_COPY_FIELDS.md",
        "SHA256SUMS.txt",
        "artifact_upload_manifest.csv",
        "zenodo_deposit_instructions.md",
        "public_release_checklist.md",
        "zenodo_metadata_template.json",
    ]:
        src = deposit_dir / name
        dst = out_dir / name
        if _copy_if_exists(src, dst):
            copied_files[name] = _rel(dst)

    checklist = render_checklist(summary, archive_path)
    (out_dir / "PUBLISH_NOW_CHECKLIST_ZH.md").write_text(checklist, encoding="utf-8")
    (out_dir / "PUBLISH_NOW_CHECKLIST_ZH_WINDOWS.md").write_text(checklist, encoding="utf-8-sig")
    (out_dir / "PUBLISH_NOW_CHECKLIST_EN.md").write_text(render_checklist_en(summary, archive_path), encoding="utf-8")
    (out_dir / "POST_PUBLICATION_UPDATE.ps1").write_text(render_post_publication_runner(), encoding="utf-8")
    (out_dir / "UPLOAD_FILE_POINTER.txt").write_text(
        "\n".join(
            [
                f"Upload archive: {_rel(archive_path)}",
                f"Absolute path: {archive_path.resolve() if archive_exists else archive_path}",
                f"SHA256: {summary.get('archive_sha256')}",
                "",
            ]
        ),
        encoding="utf-8",
    )

    status = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "ready_for_manual_publication" if archive_exists else "missing_upload_archive",
        "archive_to_upload": _rel(archive_path),
        "archive_exists": archive_exists,
        "archive_sha256": summary.get("archive_sha256"),
        "doi_minted": bool(summary.get("doi_minted")),
        "public_repository_url_recorded": bool(summary.get("public_repository_url_recorded")),
        "copied_files": copied_files,
        "outputs": {
            "checklist_zh": _rel(out_dir / "PUBLISH_NOW_CHECKLIST_ZH_WINDOWS.md"),
            "checklist_en": _rel(out_dir / "PUBLISH_NOW_CHECKLIST_EN.md"),
            "post_publication_runner": _rel(out_dir / "POST_PUBLICATION_UPDATE.ps1"),
            "upload_pointer": _rel(out_dir / "UPLOAD_FILE_POINTER.txt"),
        },
        "claim_boundary": (
            "Publish-now packet only. It does not mint a DOI, publish a repository, "
            "or establish external validation."
        ),
    }
    (out_dir / "publish_now_manifest.json").write_text(
        json.dumps(status, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return status


def render_checklist(summary: dict[str, Any], archive_path: Path) -> str:
    return "\n".join(
        [
            "# Public Release Publish-Now Checklist",
            "",
            "用途：手动发布 artifact DOI / public URL 时，只看这个文件夹即可。",
            "",
            "## 1. Zenodo 上传",
            "",
            f"- 上传文件：`{_rel(archive_path)}`",
            f"- SHA256：`{summary.get('archive_sha256')}`",
            "- Zenodo 表单内容：复制 `ZENODO_COPY_FIELDS.md`。",
            "- 上传前确认 `SHA256SUMS.txt` 与上传文件一致。",
            "- DOI 没有 mint 前，不要把 README/CITATION 里的 placeholder 当成完成状态。",
            "",
            "## 2. GitHub public release",
            "",
            "- GitHub release 内容：复制 `GITHUB_RELEASE_COPY_FIELDS.md`。",
            "- 附件可以用同一个 archive，或等 DOI 元数据写回后重新打 public archive。",
            "- 发布后记录 public repository URL。",
            "",
            "## 3. 拿到真实 DOI / URL 后",
            "",
            "先 dry-run：",
            "",
            "```powershell",
            ".\\outputs\\public_release_publish_now_20260617\\POST_PUBLICATION_UPDATE.ps1 \\",
            "  -Doi \"10.5281/zenodo.xxxxx\" \\",
            "  -RepoUrl \"https://github.com/<org>/<repo>\" \\",
            "  -PaperUrl \"https://doi.org/<paper-doi-or-placeholder>\" \\",
            "  -AuthorName \"<public author name>\" \\",
            "  -Affiliation \"<public affiliation>\"",
            "```",
            "",
            "确认 dry-run 后正式写回：",
            "",
            "```powershell",
            ".\\outputs\\public_release_publish_now_20260617\\POST_PUBLICATION_UPDATE.ps1 \\",
            "  -Doi \"10.5281/zenodo.xxxxx\" \\",
            "  -RepoUrl \"https://github.com/<org>/<repo>\" \\",
            "  -PaperUrl \"https://doi.org/<paper-doi-or-placeholder>\" \\",
            "  -AuthorName \"<public author name>\" \\",
            "  -Affiliation \"<public affiliation>\" \\",
            "  -ApplyMetadata",
            "```",
            "",
            "完成标准：dashboard P0 open count 应降到 0；public-release preflight 仍应 pass；不要新增 correctness/mergeability/reviewer utility 等 claim。",
            "",
        ]
    )


def render_checklist_en(summary: dict[str, Any], archive_path: Path) -> str:
    return "\n".join(
        [
            "# Public Release Publish-Now Checklist",
            "",
            f"Upload archive: `{_rel(archive_path)}`",
            f"SHA256: `{summary.get('archive_sha256')}`",
            "",
            "Use `ZENODO_COPY_FIELDS.md` for the Zenodo form and `GITHUB_RELEASE_COPY_FIELDS.md` for the public GitHub release.",
            "After real DOI/public URL creation, run `POST_PUBLICATION_UPDATE.ps1` first without `-ApplyMetadata`, then with `-ApplyMetadata` after checking the dry-run output.",
            "",
            "Boundary: this packet does not mint a DOI or establish external validation by itself.",
            "",
        ]
    )


def render_post_publication_runner() -> str:
    return "\n".join(
        [
            "param(",
            "  [Parameter(Mandatory=$true)][string]$Doi,",
            "  [Parameter(Mandatory=$true)][string]$RepoUrl,",
            "  [Parameter(Mandatory=$true)][string]$PaperUrl,",
            "  [Parameter(Mandatory=$true)][string]$AuthorName,",
            "  [Parameter(Mandatory=$true)][string]$Affiliation,",
            "  [switch]$ApplyMetadata",
            ")",
            "",
            "$ErrorActionPreference = 'Stop'",
            "$metadataArgs = @(",
            "  '--doi', $Doi,",
            "  '--repo-url', $RepoUrl,",
            "  '--paper-url', $PaperUrl,",
            "  '--author-name', $AuthorName,",
            "  '--affiliation', $Affiliation",
            ")",
            "",
            "python scripts/update_public_release_metadata.py --dry-run @metadataArgs --preview-out outputs/public_release_metadata_dry_run_20260617",
            "if (-not $ApplyMetadata) {",
            "  Write-Host 'Dry-run complete. Check outputs/public_release_metadata_dry_run_20260617, then rerun with -ApplyMetadata.'",
            "  exit 0",
            "}",
            "",
            "python scripts/update_public_release_metadata.py @metadataArgs",
            "python scripts/check_paper_readiness.py --out outputs/paper_readiness_check_20260617_handoff_gap",
            "python scripts/build_anonymous_release_zip.py",
            "python scripts/check_anonymous_release.py --zip outputs/release/MergeDossier-Bench-anonymous-review.zip --out outputs/anonymous_release_check_20260617",
            "python scripts/check_release_zip_smoke.py",
            "python scripts/build_zenodo_deposit_packet.py",
            "python scripts/check_public_release_preflight.py",
            "python scripts/check_submission_blockers.py --out outputs/submission_blocker_dashboard_20260617",
            "python scripts/build_acceptance_probability_gap_report.py --out outputs/acceptance_probability_gap_report_20260617",
            "",
        ]
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a public-release publish-now packet")
    parser.add_argument("--out", default="outputs/public_release_publish_now_20260617")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = build_public_release_publish_now_packet(ROOT, ROOT / args.out)
    print(f"Public release publish-now packet: {result['status']} -> {args.out}")
    return 0 if result["status"] == "ready_for_manual_publication" else 2


if __name__ == "__main__":
    raise SystemExit(main())
