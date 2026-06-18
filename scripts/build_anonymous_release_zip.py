"""Build an anonymous-review release zip for MergeDossier-Bench.

The package is intentionally curated instead of zipping the whole worktree:
it includes the software, schemas, tests, examples, paper-facing outputs, and
release documentation needed by artifact reviewers while excluding caches,
large external downloads, local virtual environments, and private scratch data.
"""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

INCLUDE_PATHS = [
    "AGENTS.md",
    "CITATION.cff",
    "LICENSE",
    "README.md",
    "TODO.md",
    "pyproject.toml",
    "schemas",
    "src",
    "tests",
    "examples",
    "scripts",
    "docs",
    ".paper/ai_assistance_disclosure.md",
    ".paper/claim_evidence_ledger.md",
    ".paper/journal_format.md",
    ".paper/material_passport.md",
    "paper/main.tex",
    "paper/references.bib",
    "paper/main.pdf",
    "paper/figures",
    "data/manifests/seed_prs.csv",
    "data/manifests/real_pilot_full_provisional_verified_manifest_20260613.csv",
    "data/manifests/population_ai_pr_frame_sanitized_20260616.csv",
    "data/manifests/population_ai_pr_sample_500_20260616.csv",
    "data/real_pilot_mixed_source_raw_20260613",
    "outputs/artifact_smoke",
    "outputs/aidev_export_report_20260616",
    "outputs/population_sampling_report_20260616",
    "outputs/population_ai_pr_500_20260616/reports/annotation_sheet_completed.csv",
    "outputs/population_results_20260616",
    "outputs/dependency_sensitive_audit_20260616/results",
    "outputs/external_audit_slice_20260617",
    "outputs/external_audit_analysis_20260617",
    "outputs/external_audit_handoff_20260617",
    "outputs/final_pdf_proofread_20260617",
    "outputs/icse_format_check_20260617_handoff_gap.md",
    "outputs/icse_format_check_20260617_handoff_gap.json",
    "outputs/layout_quality_20260617.md",
    "outputs/layout_quality_20260617.json",
    "outputs/visual_check_layout_quality_20260617/visual_layout_review.md",
    "outputs/visual_check_layout_quality_20260617/contact.png",
    "outputs/visual_check_layout_quality_20260617/packet/preview.jpg",
    "outputs/visual_check_layout_quality_20260617/packet/visual_packet.md",
    "outputs/paper_readiness_check_20260617_handoff_gap",
    "outputs/paper_layout_build_check_20260617",
    "outputs/public_release_metadata_20260617",
    "outputs/raw_frame_release_risk_20260617",
    "outputs/manuscript_claim_hygiene_20260617",
    "outputs/submission_blocker_dashboard_20260617",
    "outputs/submission_readiness_20260617",
]

EXCLUDE_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
}

EXCLUDE_SUFFIXES = {
    ".aux",
    ".bbl",
    ".blg",
    ".log",
    ".out",
    ".pyc",
    ".tmp",
}

SECRET_PATTERNS = [
    re.compile(r"github_pat_[A-Za-z0-9_]+"),
    re.compile(r"ghp_[A-Za-z0-9_]{20,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
]

TEXT_SUFFIXES = {".csv", ".json", ".jsonl", ".md", ".py", ".tex", ".toml", ".cff", ".txt"}

LOCAL_PATH_PATTERNS = [
    re.compile(r"C:\\\\Users\\\\[^\\\\]+\\\\AppData\\\\Local\\\\Programs\\\\Python\\\\Python\d+\\\\python\.exe"),
    re.compile(r"C:\\Users\\[^\\]+\\AppData\\Local\\Programs\\Python\\Python\d+\\python\.exe"),
    re.compile(r"C:/Users/[^/]+/AppData/Local/Programs/Python/Python\d+/python\.exe"),
    re.compile(r"C:\\\\Users\\\\[^\\\\]+\\\\.*?MergeDossier-Bench-starter\\\\"),
    re.compile(r"C:\\\\Users\\\\[^\\\\]+\\\\.*?MergeDossier-Bench-starter"),
    re.compile(r"C:\\Users\\[^\\]+\\.*?MergeDossier-Bench-starter\\"),
    re.compile(r"C:\\Users\\[^\\]+\\.*?MergeDossier-Bench-starter"),
    re.compile(r"C:/Users/[^/]+/.*?MergeDossier-Bench-starter/"),
    re.compile(r"C:/Users/[^/]+/.*?MergeDossier-Bench-starter"),
]


def should_include(path: Path) -> bool:
    rel_parts = path.relative_to(ROOT).parts
    if any(part in EXCLUDE_PARTS for part in rel_parts):
        return False
    if path.suffix.lower() in EXCLUDE_SUFFIXES:
        return False
    return True


def iter_files() -> list[Path]:
    files: list[Path] = []
    for raw in INCLUDE_PATHS:
        path = ROOT / raw
        if not path.exists():
            continue
        if path.is_file():
            if should_include(path):
                files.append(path)
            continue
        for child in path.rglob("*"):
            if child.is_file() and should_include(child):
                files.append(child)
    return sorted(set(files), key=lambda item: item.as_posix().lower())


def scan_text_file(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    findings = []
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            findings.append(pattern.pattern)
    return findings


def redact_local_paths(text: str) -> str:
    redacted = text
    for pattern in LOCAL_PATH_PATTERNS[:3]:
        redacted = pattern.sub("python", redacted)
    for pattern in LOCAL_PATH_PATTERNS[3:]:
        redacted = pattern.sub("<REPO_ROOT>/", redacted)
    return redacted


def _read_for_zip(path: Path) -> bytes | None:
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    return redact_local_paths(text).encode("utf-8")


def build_zip(out_path: Path) -> dict[str, object]:
    files = iter_files()
    package_root = f"MergeDossier-Bench-anonymous-{datetime.now(timezone.utc).strftime('%Y%m%d')}"
    secret_findings = []
    for path in files:
        if path.suffix.lower() in TEXT_SUFFIXES:
            matches = scan_text_file(path)
            if matches:
                secret_findings.append({"path": str(path.relative_to(ROOT)), "patterns": matches})
    if secret_findings:
        raise RuntimeError("Potential secret patterns found: " + json.dumps(secret_findings[:20], indent=2))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_rows = []
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in files:
            rel = path.relative_to(ROOT)
            arcname = f"{package_root}/{rel.as_posix()}"
            redacted_bytes = _read_for_zip(path)
            if redacted_bytes is None:
                zf.write(path, arcname)
            else:
                zf.writestr(arcname, redacted_bytes)
            manifest_rows.append({"path": rel.as_posix(), "bytes": path.stat().st_size})
        release_manifest = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "package_root": package_root,
            "file_count": len(manifest_rows),
            "total_uncompressed_bytes": sum(row["bytes"] for row in manifest_rows),
            "claim_boundary": (
                "Anonymous-review artifact for handoff-evidence gap measurement within AIDev-pop; "
                "not a correctness, mergeability, reviewer-utility, AI-vs-human, all-GitHub, or inter-rater-reliability claim."
            ),
            "files": manifest_rows,
        }
        zf.writestr(f"{package_root}/RELEASE_MANIFEST.json", json.dumps(release_manifest, indent=2) + "\n")

    return {
        "zip_path": str(out_path),
        "package_root": package_root,
        "file_count": len(manifest_rows),
        "zip_bytes": out_path.stat().st_size,
        "total_uncompressed_bytes": sum(row["bytes"] for row in manifest_rows),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build anonymous-review release zip")
    parser.add_argument("--out", default="outputs/release/MergeDossier-Bench-anonymous-review.zip")
    parser.add_argument("--summary-out", default="outputs/release/release_zip_summary.json")
    args = parser.parse_args(argv)
    summary = build_zip(ROOT / args.out)
    summary_path = ROOT / args.summary_out
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    display_path = Path(summary["zip_path"])
    try:
        display = display_path.relative_to(ROOT).as_posix()
    except ValueError:
        display = display_path.name
    print(f"Release zip written: {display} ({summary['file_count']} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
