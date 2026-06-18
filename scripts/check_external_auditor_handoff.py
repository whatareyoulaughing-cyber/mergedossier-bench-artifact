"""Check that the external-auditor handoff zip preserves audit independence."""

from __future__ import annotations

import argparse
import csv
import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PASS = "pass"
FAIL = "fail"

REQUIRED_BASENAMES = {
    "external_audit_sheet.xlsx",
    "external_audit_sheet.csv",
    "external_audit_manifest.json",
    "README_external_audit.md",
    "OPERATOR_QUICKSTART.md",
    "RETURN_INSTRUCTIONS_FOR_AUTHOR.md",
    "EMAIL_TEMPLATE_TO_EXTERNAL_AUDITOR.md",
    "HANDOFF_MANIFEST.json",
}

FORBIDDEN_PATH_PATTERNS = [
    "annotation_sheet_completed",
    "population_results",
    "population_estimates",
    "paper_table_",
    "external_audit_agreement",
    "external_audit_disagreements",
    "completed_external_audit",
]

VALID_LABELS = {"present", "partially_present", "missing", "not_applicable"}


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _record(name: str, status: str, evidence: str, action: str) -> dict[str, str]:
    return {"name": name, "status": status, "evidence": evidence, "action": action}


def _read_zip_text(archive: zipfile.ZipFile, suffix: str) -> str:
    matches = [name for name in archive.namelist() if name.endswith(suffix)]
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one {suffix}, found {len(matches)}")
    return archive.read(matches[0]).decode("utf-8-sig")


def _blank_label_cells_in_csv(csv_text: str) -> tuple[int, int, list[dict[str, str]]]:
    rows = list(csv.DictReader(io.StringIO(csv_text)))
    label_columns = [field for field in (rows[0].keys() if rows else []) if field.endswith("_label")]
    filled: list[dict[str, str]] = []
    total = 0
    for row in rows:
        instance_id = str(row.get("instance_id", "")).strip()
        for column in label_columns:
            total += 1
            value = str(row.get(column, "")).strip()
            if value:
                filled.append({"instance_id": instance_id, "column": column, "value": value})
    return total - len(filled), total, filled


def check_external_auditor_handoff(zip_path: Path, out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    checks: list[dict[str, str]] = []
    if not zip_path.exists():
        checks.append(_record("zip_exists", FAIL, f"Missing {_rel(zip_path)}.", "Build the external auditor handoff zip."))
        result = _result(zip_path, checks)
        _write_outputs(result, out_dir)
        return result

    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        basenames = {Path(name).name for name in names}
        missing = sorted(REQUIRED_BASENAMES - basenames)
        if missing:
            checks.append(_record("required_files", FAIL, "Missing: " + ", ".join(missing), "Rebuild the handoff zip."))
        else:
            checks.append(_record("required_files", PASS, f"All {len(REQUIRED_BASENAMES)} required handoff files are present.", "Send this zip to the external auditor."))

        forbidden_hits = [
            name for name in names for pattern in FORBIDDEN_PATH_PATTERNS if pattern.lower() in name.lower()
        ]
        if forbidden_hits:
            checks.append(_record("forbidden_result_paths", FAIL, "Forbidden entries: " + ", ".join(sorted(set(forbidden_hits))[:20]), "Remove primary labels/result tables from the handoff zip."))
        else:
            checks.append(_record("forbidden_result_paths", PASS, "No primary annotation/result-table path patterns found.", "Keep the handoff zip independent from paper results."))

        manifest = json.loads(_read_zip_text(archive, "HANDOFF_MANIFEST.json"))
        excludes = " ".join(str(item) for item in manifest.get("excludes", []))
        if all(term in excludes for term in ["primary completed annotation CSV", "paper result tables", "population estimates"]):
            checks.append(_record("manifest_exclusion_boundary", PASS, "HANDOFF_MANIFEST records excluded primary/result artifacts.", "Keep this boundary visible to auditors."))
        else:
            checks.append(_record("manifest_exclusion_boundary", FAIL, "HANDOFF_MANIFEST does not list expected exclusions.", "Regenerate the handoff manifest."))

        csv_text = _read_zip_text(archive, "external_audit_sheet.csv")
        blank, total, filled = _blank_label_cells_in_csv(csv_text)
        if total and blank == total:
            checks.append(_record("blank_audit_labels", PASS, f"All {total} external audit label cells are blank.", "The auditor can code independently."))
        else:
            preview = ", ".join(f"{row['instance_id']}:{row['column']}={row['value']}" for row in filled[:10])
            checks.append(_record("blank_audit_labels", FAIL, f"{len(filled)} of {total} label cells are pre-filled. {preview}", "Regenerate a blank external audit sheet."))

        invalid_prefill = [row for row in filled if row["value"] in VALID_LABELS]
        if not invalid_prefill:
            checks.append(_record("no_completed_codes", PASS, "No completed audit-code values found in the handoff CSV.", "Keep completed codes out of the auditor package."))
        else:
            checks.append(_record("no_completed_codes", FAIL, f"Found {len(invalid_prefill)} completed audit-code values.", "Remove pre-filled labels before sending."))

    result = _result(zip_path, checks)
    _write_outputs(result, out_dir)
    return result


def _result(zip_path: Path, checks: list[dict[str, str]]) -> dict[str, Any]:
    failures = [check for check in checks if check["status"] == FAIL]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": FAIL if failures else PASS,
        "zip_path": _rel(zip_path),
        "failure_count": len(failures),
        "checks": checks,
        "claim_boundary": (
            "Handoff independence check only. Passing this check does not complete the external audit "
            "or establish external agreement."
        ),
    }


def _write_outputs(result: dict[str, Any], out_dir: Path) -> None:
    (out_dir / "external_auditor_handoff_check.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# External Auditor Handoff Check",
        "",
        f"Status: **{result['status']}**",
        "",
        "| Check | Status | Evidence | Action |",
        "|---|---:|---|---|",
    ]
    for check in result["checks"]:
        evidence = check["evidence"].replace("|", "\\|")
        action = check["action"].replace("|", "\\|")
        lines.append(f"| {check['name']} | {check['status']} | {evidence} | {action} |")
    lines.extend(["", "## Boundary", "", str(result["claim_boundary"]), ""])
    (out_dir / "external_auditor_handoff_check.md").write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check external-auditor handoff zip independence")
    parser.add_argument("--zip", default="outputs/external_audit_handoff_20260617/MergeDossier-external-audit-handoff.zip")
    parser.add_argument("--out", default="outputs/external_audit_handoff_20260617")
    args = parser.parse_args(argv)
    result = check_external_auditor_handoff(ROOT / args.zip, ROOT / args.out)
    print(f"External auditor handoff check: {result['status']} (fail={result['failure_count']})")
    return 0 if result["status"] == PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
