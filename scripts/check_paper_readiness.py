"""Run the local paper/artifact readiness gate for MergeDossier-Bench."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "outputs" / "paper_readiness_check_20260613"

CommandRunner = Callable[[list[str], dict[str, str]], dict[str, Any]]


def run_command(args: list[str], env: dict[str, str]) -> dict[str, Any]:
    completed = subprocess.run(args, cwd=ROOT, env=env, text=True, capture_output=True, check=False)
    return {
        "name": " ".join(args),
        "command": args,
        "returncode": completed.returncode,
        "status": "pass" if completed.returncode == 0 else "fail",
        "stdout_tail": completed.stdout[-3000:],
        "stderr_tail": completed.stderr[-3000:],
    }


def command_env() -> dict[str, str]:
    env = os.environ.copy()
    src = str(ROOT / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def annotation_validation_command(require_completed: bool) -> tuple[list[str], str, bool]:
    completed = ROOT / "outputs" / "real_pilot_mixed_source_annotation_sheet_completed_20260613.csv"
    template = ROOT / "outputs" / "real_pilot_mixed_source_annotation_sheet_20260613.csv"
    if completed.exists():
        return (
            [
                sys.executable,
                "-m",
                "mergedossier_bench.cli",
                "validate-annotation-csv",
                "--annotations",
                str(completed),
                "--out",
                str(ROOT / "outputs" / "real_pilot_mixed_source_annotation_sheet_completed_validation_20260613.json"),
            ],
            "completed_annotation_csv",
            True,
        )
    command = [
        sys.executable,
        "-m",
        "mergedossier_bench.cli",
        "validate-annotation-csv",
        "--annotations",
        str(template),
        "--allow-incomplete",
        "--out",
        str(ROOT / "outputs" / "real_pilot_mixed_source_annotation_sheet_validation_20260613.json"),
    ]
    return command, "annotation_template_only", not require_completed


def readiness_status(records: list[dict[str, Any]], annotation_state: str, require_completed: bool) -> str:
    if any(record["status"] == "fail" for record in records):
        return "fail"
    if annotation_state != "completed_annotation_csv":
        return "fail" if require_completed else "needs_human_labels"
    return "pass"


def run_readiness(out_dir: Path, require_completed_annotations: bool, runner: CommandRunner = run_command) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    env = command_env()
    commands: list[tuple[str, list[str], bool]] = [
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
            True,
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
            True,
        ),
        (
            "final_pdf_proofread",
            [
                sys.executable,
                "scripts/check_final_pdf_proofread.py",
                "--pdf",
                "paper/main.pdf",
                "--out",
                str(out_dir / "final_pdf_proofread"),
            ],
            True,
        ),
        (
            "manuscript_claim_hygiene",
            [
                sys.executable,
                "scripts/check_manuscript_claim_hygiene.py",
                "--tex",
                "paper/main.tex",
                "--out",
                str(out_dir / "manuscript_claim_hygiene"),
            ],
            True,
        ),
        (
            "double_anonymous_submission",
            [
                sys.executable,
                "scripts/check_double_anonymous_submission.py",
                "--pdf",
                "paper/main.pdf",
                "--tex",
                "paper/main.tex",
                "--out",
                str(out_dir / "double_anonymous_submission"),
            ],
            True,
        ),
        ("pytest", [sys.executable, "-m", "pytest", "-q"], True),
        ("artifact_smoke", [sys.executable, "scripts/reproduce_artifact_smoke.py"], True),
    ]
    annotation_command, annotation_state, annotation_can_pass = annotation_validation_command(require_completed_annotations)
    commands.append(("annotation_csv", annotation_command, annotation_can_pass))

    records: list[dict[str, Any]] = []
    for name, command, allowed in commands:
        record = runner(command, env)
        record["gate"] = name
        if not allowed and record["status"] == "pass":
            record["status"] = "fail"
            record["stderr_tail"] = (record.get("stderr_tail", "") + "\nCompleted annotation CSV is required.").strip()
        records.append(record)

    status = readiness_status(records, annotation_state, require_completed_annotations)
    result = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": status,
        "annotation_state": annotation_state,
        "require_completed_annotations": require_completed_annotations,
        "records": records,
        "next_required_human_action": None
        if annotation_state == "completed_annotation_csv"
        else (
            "Fill outputs/real_pilot_mixed_source_annotation_workbook_20260613.xlsx, "
            "then run scripts/run_completed_annotation_pipeline.py."
        ),
    }
    (out_dir / "paper_readiness_check.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_markdown(result, out_dir / "paper_readiness_check.md")
    return result


def write_markdown(result: dict[str, Any], out: Path) -> None:
    lines = [
        "# Paper Readiness Check",
        "",
        f"Overall status: **{result['status']}**",
        "",
        f"Annotation state: `{result['annotation_state']}`",
        "",
        "| Gate | Status | Return code |",
        "|---|---:|---:|",
    ]
    for record in result["records"]:
        lines.append(f"| {record['gate']} | {record['status']} | {record['returncode']} |")
    if result.get("next_required_human_action"):
        lines.extend(["", "## Next Human Action", "", str(result["next_required_human_action"])])
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run paper/artifact readiness checks")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output directory for readiness reports")
    parser.add_argument(
        "--require-completed-annotations",
        action="store_true",
        help="Fail unless the completed annotation CSV exists and validates",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_readiness(Path(args.out), require_completed_annotations=args.require_completed_annotations)
    print(f"Paper readiness check: {result['status']} -> {args.out}")
    return 0 if result["status"] in {"pass", "needs_human_labels"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
