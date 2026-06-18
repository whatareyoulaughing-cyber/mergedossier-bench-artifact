"""Smoke-test the generated anonymous-review release zip.

This checker verifies the artifact that reviewers actually receive: it extracts
the release archive into a temporary directory, locates the package root, and
runs a bounded offline smoke workflow from inside the extracted tree. The output
is intentionally kept outside the release zip to avoid checksum self-reference.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
PASS = "pass"
FAIL = "fail"

CommandRunner = Callable[[list[str], Path, dict[str, str], int], dict[str, Any]]


def _display(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _safe_extract(zip_path: Path, out_dir: Path) -> None:
    with zipfile.ZipFile(zip_path) as archive:
        target_root = out_dir.resolve()
        for member in archive.infolist():
            target = (out_dir / member.filename).resolve()
            if target != target_root and target_root not in target.parents:
                raise RuntimeError(f"Unsafe archive member path: {member.filename}")
        archive.extractall(out_dir)


def _find_package_root(extract_dir: Path) -> Path:
    candidates = [
        path
        for path in extract_dir.iterdir()
        if path.is_dir()
        and (path / "pyproject.toml").exists()
        and (path / "src" / "mergedossier_bench").is_dir()
    ]
    if len(candidates) != 1:
        raise RuntimeError(f"Expected one package root, found {len(candidates)}")
    return candidates[0]


def _default_runner(args: list[str], cwd: Path, env: dict[str, str], timeout: int) -> dict[str, Any]:
    completed = subprocess.run(
        args,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )
    return {
        "command": args,
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout[-2000:],
        "stderr_tail": completed.stderr[-2000:],
    }


def _write_markdown(result: dict[str, Any], out: Path) -> None:
    lines = [
        "# Release Zip Smoke Check",
        "",
        f"Status: **{result['status']}**",
        "",
        f"Archive: `{result.get('zip_path', '')}`",
        f"Package root: `{result.get('package_root', '')}`",
        "",
        "## Commands",
        "",
        "| Name | Return code |",
        "|---|---:|",
    ]
    for record in result.get("commands", []):
        lines.append(f"| {record['name']} | {record.get('returncode', 'n/a')} |")
    lines.extend(["", "## Expected Outputs", "", "| Output | Present |", "|---|---:|"])
    for record in result.get("expected_outputs", []):
        lines.append(f"| `{record['path']}` | {record['present']} |")
    if result.get("error"):
        lines.extend(["", "## Error", "", f"```text\n{result['error']}\n```"])
    lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")


def check_release_zip_smoke(
    zip_path: Path,
    out_dir: Path,
    *,
    runner: CommandRunner = _default_runner,
    timeout: int = 180,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": FAIL,
        "zip_path": _display(zip_path),
        "commands": [],
        "expected_outputs": [],
    }
    try:
        if not zip_path.exists():
            raise RuntimeError(f"Release zip does not exist: {_display(zip_path)}")
        with tempfile.TemporaryDirectory(prefix="mergedossier_release_zip_smoke_") as raw_tmp:
            extract_dir = Path(raw_tmp) / "extracted"
            extract_dir.mkdir()
            _safe_extract(zip_path, extract_dir)
            package_root = _find_package_root(extract_dir)
            result["package_root"] = package_root.name

            env = os.environ.copy()
            env["PYTHONPATH"] = str(package_root / "src") + os.pathsep + env.get("PYTHONPATH", "")
            env["PYTHONIOENCODING"] = "utf-8"

            release_smoke_outputs = package_root / "outputs" / "release_zip_smoke"
            if release_smoke_outputs.exists():
                shutil.rmtree(release_smoke_outputs)

            commands = [
                (
                    "pytest_subset",
                    [
                        sys.executable,
                        "-m",
                        "pytest",
                        "tests/test_cli_smoke.py",
                        "tests/test_schemas.py",
                        "tests/test_scoring.py",
                        "tests/test_corpus.py",
                        "tests/test_provenance.py",
                        "-q",
                    ],
                ),
                (
                    "corpus_summary",
                    [
                        sys.executable,
                        "-m",
                        "mergedossier_bench.cli",
                        "summarize",
                        "--dossiers",
                        "examples/corpus",
                        "--out",
                        "outputs/release_zip_smoke/corpus",
                    ],
                ),
                (
                    "provenance_audit",
                    [
                        sys.executable,
                        "-m",
                        "mergedossier_bench.cli",
                        "audit-provenance",
                        "--dossiers",
                        "examples/corpus",
                        "--out",
                        "outputs/release_zip_smoke/provenance",
                    ],
                ),
            ]
            for name, command in commands:
                record = runner(command, package_root, env, timeout)
                record["name"] = name
                result["commands"].append(record)
                if record.get("returncode") != 0:
                    raise RuntimeError(f"Release zip smoke command failed: {name}")

            expected = [
                "outputs/release_zip_smoke/corpus/summary.json",
                "outputs/release_zip_smoke/corpus/scores.jsonl",
                "outputs/release_zip_smoke/provenance/provenance_summary.json",
                "outputs/release_zip_smoke/provenance/uncited_evidence.jsonl",
            ]
            missing = []
            for rel in expected:
                present = (package_root / rel).exists()
                result["expected_outputs"].append({"path": rel, "present": present})
                if not present:
                    missing.append(rel)
            if missing:
                raise RuntimeError("Missing expected release-smoke outputs: " + ", ".join(missing))
            result["status"] = PASS
    except Exception as exc:  # noqa: BLE001 - report diagnostic instead of crashing silently.
        result["error"] = str(exc)

    (out_dir / "release_zip_smoke.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    _write_markdown(result, out_dir / "release_zip_smoke.md")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke-test the anonymous-review release zip")
    parser.add_argument("--zip", default="outputs/release/MergeDossier-Bench-anonymous-review.zip")
    parser.add_argument("--out", default="outputs/release_zip_smoke_20260617")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args(argv)

    result = check_release_zip_smoke(ROOT / args.zip, ROOT / args.out, timeout=args.timeout)
    print(f"Release zip smoke check: {result['status']}")
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
