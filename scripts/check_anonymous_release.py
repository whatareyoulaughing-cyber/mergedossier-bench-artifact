"""Scan an anonymous-review release staging tree or zip for identity/path leaks."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {
    ".cff",
    ".csv",
    ".json",
    ".jsonl",
    ".md",
    ".ps1",
    ".py",
    ".tex",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
PDF_SUFFIXES = {".pdf"}
SELF_CHECK_FILES = {
    "scripts/build_anonymous_release_zip.py",
    "scripts/check_anonymous_release.py",
    "scripts/check_double_anonymous_submission.py",
    "tests/test_anonymous_release_check.py",
    "tests/test_double_anonymous_submission_check.py",
}
LEAK_PRONE_PARTS = {".git", ".venv", ".pytest_cache", ".mypy_cache", ".ruff_cache", "__pycache__"}
LOCAL_USER = os.environ.get("USERNAME") or os.environ.get("USER") or ""

LEAK_PATTERNS = {
    "email_address": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    "windows_user_path": re.compile(r"C:\\Users\\", re.I),
    "windows_user_path_escaped": re.compile(r"C:\\\\Users\\\\", re.I),
    "forward_user_path": re.compile(r"C:/Users/", re.I),
    "onedrive_path": re.compile(r"OneDrive", re.I),
    "mojibake_workspace_path": re.compile(r"Ã¦â€“â€¡|Ã¥Â­Â¦|Ã¥Å“|Ã¥Â¤"),
    "github_token": re.compile(r"\b(?:github_pat_|ghp_)[A-Za-z0-9_]{20,}"),
    "openai_token": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
    "generic_api_key_assignment": re.compile(
        r"\b(?:api[_-]?key|token|secret)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]",
        re.I,
    ),
    "ssh_private_key": re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
    "ssh_remote_url": re.compile(r"\bgit@github\.com:", re.I),
}
if LOCAL_USER:
    LEAK_PATTERNS["local_user_id"] = re.compile(re.escape(LOCAL_USER))


def scan_anonymous_release(target_path: Path, out_dir: Path) -> dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=True)
    findings: list[dict[str, object]] = []

    for item in _iter_scan_items(target_path):
        filename = str(item["filename"])
        logical_name = str(item["logical_name"])
        size = int(item["size"])
        suffix = Path(filename).suffix.lower()
        parts = set(Path(logical_name).parts)

        leak_prone = sorted(parts & LEAK_PRONE_PARTS)
        if leak_prone:
            findings.append(
                {
                    "file": filename,
                    "patterns": [f"leak_prone_path:{part}" for part in leak_prone],
                    "bytes": size,
                }
            )
            continue

        if logical_name in SELF_CHECK_FILES:
            continue

        raw = item["bytes"]
        if not isinstance(raw, bytes):
            continue

        if suffix in PDF_SUFFIXES:
            hits = _pdf_metadata_hits(raw, filename)
            if hits:
                findings.append({"file": filename, "patterns": hits, "bytes": size})
            continue

        if suffix not in TEXT_SUFFIXES or size > 2_000_000:
            continue

        text = raw.decode("utf-8", errors="ignore")
        hits = [name for name, pattern in LEAK_PATTERNS.items() if pattern.search(text)]
        if hits:
            findings.append({"file": filename, "patterns": hits, "bytes": size})

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target_path": _display(target_path),
        "status": "fail" if findings else "pass",
        "finding_count": len(findings),
        "findings": findings[:200],
        "claim_boundary": (
            "This check scans release text/PDF metadata and leak-prone paths for local path, "
            "identity, token, or hidden-directory leaks. It does not validate empirical claims "
            "or publication metadata."
        ),
    }
    (out_dir / "anonymous_release_check.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    _write_markdown(result, out_dir / "anonymous_release_check.md")
    return result


def _iter_scan_items(target_path: Path) -> list[dict[str, Any]]:
    if target_path.is_dir():
        items: list[dict[str, Any]] = []
        for path in target_path.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(target_path).as_posix()
            try:
                data = path.read_bytes()
            except OSError:
                continue
            items.append({"filename": rel, "logical_name": rel, "bytes": data, "size": len(data)})
        return items

    items = []
    with zipfile.ZipFile(target_path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            parts = Path(info.filename).parts
            logical_name = "/".join(parts[1:]) if len(parts) > 1 else info.filename
            items.append(
                {
                    "filename": info.filename,
                    "logical_name": logical_name,
                    "bytes": archive.read(info.filename),
                    "size": info.file_size,
                }
            )
    return items


def _display(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.name


def _pdf_metadata_hits(pdf_bytes: bytes, name: str) -> list[str]:
    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = Path(tmp) / Path(name).name
        pdf_path.write_bytes(pdf_bytes)
        completed = subprocess.run(
            ["pdfinfo", str(pdf_path)],
            text=True,
            capture_output=True,
            errors="replace",
            check=False,
        )
        metadata = (completed.stdout or "") + "\n" + (completed.stderr or "")
    return [f"pdf_metadata:{key}" for key, pattern in LEAK_PATTERNS.items() if pattern.search(metadata)]


def _write_markdown(result: dict[str, object], out: Path) -> None:
    lines = [
        "# Anonymous Release Check",
        "",
        f"Overall status: **{result['status']}**",
        "",
        f"- Findings: {result['finding_count']}",
        "",
        "| File | Patterns | Bytes |",
        "|---|---|---:|",
    ]
    findings = result.get("findings") or []
    if isinstance(findings, list) and findings:
        for finding in findings:
            if isinstance(finding, dict):
                patterns = finding.get("patterns", [])
                pattern_text = ", ".join(patterns) if isinstance(patterns, list) else str(patterns)
                lines.append(f"| `{finding.get('file')}` | {pattern_text} | {finding.get('bytes')} |")
    else:
        lines.append("| None | - | 0 |")
    lines.extend(["", "## Boundary", "", str(result["claim_boundary"]), ""])
    out.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check anonymous release staging tree or zip for leaks")
    parser.add_argument("--target", default="release/anonymous_github_repo")
    parser.add_argument("--zip", default=None, help="Backward-compatible alias for --target.")
    parser.add_argument("--out", default="outputs/anonymous_release_check")
    args = parser.parse_args(argv)
    target = args.zip or args.target
    result = scan_anonymous_release(ROOT / target, ROOT / args.out)
    if args.out == "outputs/anonymous_release_check":
        top_json = ROOT / "outputs" / "anonymous_release_check.json"
        top_md = ROOT / "outputs" / "anonymous_release_check.md"
        top_json.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        _write_markdown(result, top_md)
    print(f"Anonymous release check: {result['status']} ({result['finding_count']} findings)")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
