"""Regenerate paper figures, compile the paper, and run layout checks."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
PAPER_DIR = ROOT / "paper"
DEFAULT_OUT_DIR = ROOT / "outputs" / "paper_layout_build_check_20260617"

CommandRunner = Callable[[list[str], Path, Path], dict[str, Any]]


def run_command(command: list[str], cwd: Path, log_path: Path) -> dict[str, Any]:
    completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(completed.stdout + completed.stderr, encoding="utf-8", errors="replace")
    return {
        "command": command,
        "cwd": str(cwd),
        "log": str(log_path.relative_to(ROOT)),
        "returncode": completed.returncode,
        "status": "pass" if completed.returncode == 0 else "fail",
        "stdout_tail": completed.stdout[-1200:],
        "stderr_tail": completed.stderr[-1200:],
    }


def build_and_check(out_dir: Path, runner: CommandRunner = run_command) -> dict[str, Any]:
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []

    steps: list[tuple[str, list[str], Path, Path]] = [
        ("generate_figures", [sys.executable, "scripts/generate_paper_figures.py"], ROOT, out_dir / "generate_figures.log"),
        ("pdflatex_pass1", ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"], PAPER_DIR, PAPER_DIR / "build_pass1.log"),
        ("bibtex", ["bibtex", "main"], PAPER_DIR, PAPER_DIR / "build_bibtex.log"),
        ("pdflatex_pass2", ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"], PAPER_DIR, PAPER_DIR / "build_pass2.log"),
        ("pdflatex_final", ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"], PAPER_DIR, PAPER_DIR / "build.log"),
        (
            "icse_format",
            [
                sys.executable,
                "scripts/check_icse_format.py",
                "--tex",
                "paper/main.tex",
                "--pdf",
                "paper/main.pdf",
                "--log",
                "paper/build.log",
                "--out",
                str(out_dir / "icse_format_check.json"),
                "--markdown",
                str(out_dir / "icse_format_check.md"),
            ],
            ROOT,
            out_dir / "icse_format_check.log",
        ),
        (
            "layout_quality",
            [
                sys.executable,
                "scripts/check_layout_quality.py",
                "--tex",
                "paper/main.tex",
                "--pdf",
                "paper/main.pdf",
                "--log",
                "paper/build.log",
                "--figures-dir",
                "paper/figures",
                "--out-json",
                str(out_dir / "layout_quality.json"),
                "--out-md",
                str(out_dir / "layout_quality.md"),
            ],
            ROOT,
            out_dir / "layout_quality.log",
        ),
    ]

    for name, command, cwd, log_path in steps:
        record = runner(command, cwd, log_path)
        record["step"] = name
        records.append(record)
        if record["status"] != "pass":
            break

    status = "fail" if any(record["status"] == "fail" for record in records) else "pass"
    result = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": status,
        "pdf": "paper/main.pdf",
        "records": records,
    }
    (out_dir / "paper_layout_build_check.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    write_markdown(result, out_dir / "paper_layout_build_check.md")
    return result


def write_markdown(result: dict[str, Any], out_path: Path) -> None:
    lines = [
        "# Paper Layout Build Check",
        "",
        f"Overall status: **{result['status']}**",
        "",
        f"PDF: `{result['pdf']}`",
        "",
        "| Step | Status | Return code | Log |",
        "|---|---:|---:|---|",
    ]
    for record in result["records"]:
        lines.append(
            f"| {record['step']} | {record['status']} | {record['returncode']} | `{record['log']}` |"
        )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build paper PDF and run layout quality checks")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Output directory for build/check reports")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = build_and_check(Path(args.out_dir))
    print(f"Paper layout build check: {result['status']} -> {args.out_dir}")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
