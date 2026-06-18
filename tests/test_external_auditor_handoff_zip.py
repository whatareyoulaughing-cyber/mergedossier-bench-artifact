import importlib.util
import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "build_external_auditor_handoff_zip", ROOT / "scripts" / "build_external_auditor_handoff_zip.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
build_external_auditor_handoff_zip = MODULE.build_external_auditor_handoff_zip


def test_external_auditor_handoff_zip_contains_only_handoff_files(tmp_path: Path):
    slice_dir = tmp_path / "slice"
    slice_dir.mkdir()
    required = {
        "external_audit_sheet.xlsx": "xlsx-bytes",
        "external_audit_sheet.csv": "csv-bytes",
        "external_audit_manifest.json": json.dumps({"selected_tasks": 50}),
        "README_external_audit.md": "# README",
    }
    for name, text in required.items():
        (slice_dir / name).write_text(text, encoding="utf-8")
    out = tmp_path / "handoff.zip"

    summary = build_external_auditor_handoff_zip(slice_dir, out, staging_dir=tmp_path / "staging")

    assert summary["file_count"] == 8
    with zipfile.ZipFile(out) as zf:
        names = [Path(name).name for name in zf.namelist()]
    assert "external_audit_sheet.xlsx" in names
    assert "OPERATOR_QUICKSTART.md" in names
    assert "RETURN_INSTRUCTIONS_FOR_AUTHOR.md" in names
    assert "EMAIL_TEMPLATE_TO_EXTERNAL_AUDITOR.md" in names
    assert "HANDOFF_MANIFEST.json" in names
    assert "annotation_sheet_completed.csv" not in names
    assert "population_estimates.json" not in names
    with zipfile.ZipFile(out) as zf:
        return_note_name = next(name for name in zf.namelist() if name.endswith("RETURN_INSTRUCTIONS_FOR_AUTHOR.md"))
        return_note = zf.read(return_note_name).decode("utf-8")
    assert "check_external_audit_progress.py" in return_note
