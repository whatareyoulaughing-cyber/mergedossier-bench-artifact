import importlib.util
import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "check_external_auditor_handoff.py"
SPEC = importlib.util.spec_from_file_location("check_external_auditor_handoff", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
check_external_auditor_handoff = MODULE.check_external_auditor_handoff


def _blank_csv(prefilled: bool = False) -> str:
    value = "present" if prefilled else ""
    return (
        "instance_id,is_reliability_repeat,intent_label,intent_comment\n"
        f"task-a,False,{value},\n"
    )


def _write_handoff_zip(path: Path, *, forbidden: bool = False, prefilled: bool = False) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        root = "pkg"
        archive.writestr(f"{root}/external_audit_sheet.xlsx", "xlsx")
        archive.writestr(f"{root}/external_audit_sheet.csv", _blank_csv(prefilled))
        archive.writestr(f"{root}/external_audit_manifest.json", "{}")
        archive.writestr(f"{root}/README_external_audit.md", "# readme")
        archive.writestr(f"{root}/OPERATOR_QUICKSTART.md", "# quickstart")
        archive.writestr(f"{root}/RETURN_INSTRUCTIONS_FOR_AUTHOR.md", "# return")
        archive.writestr(f"{root}/EMAIL_TEMPLATE_TO_EXTERNAL_AUDITOR.md", "# email")
        archive.writestr(
            f"{root}/HANDOFF_MANIFEST.json",
            json.dumps(
                {
                    "excludes": [
                        "primary completed annotation CSV",
                        "paper result tables",
                        "population estimates",
                    ]
                }
            ),
        )
        if forbidden:
            archive.writestr(f"{root}/population_results/paper_table_handoff_gap.csv", "leak")


def test_external_auditor_handoff_check_passes_clean_zip(tmp_path: Path):
    archive = tmp_path / "handoff.zip"
    _write_handoff_zip(archive)

    result = check_external_auditor_handoff(archive, tmp_path / "out")

    assert result["status"] == "pass"
    assert result["failure_count"] == 0
    assert any(check["name"] == "blank_audit_labels" and check["status"] == "pass" for check in result["checks"])
    assert (tmp_path / "out/external_auditor_handoff_check.md").exists()


def test_external_auditor_handoff_check_fails_for_leak_and_prefill(tmp_path: Path):
    archive = tmp_path / "handoff.zip"
    _write_handoff_zip(archive, forbidden=True, prefilled=True)

    result = check_external_auditor_handoff(archive, tmp_path / "out")

    assert result["status"] == "fail"
    assert any(check["name"] == "forbidden_result_paths" and check["status"] == "fail" for check in result["checks"])
    assert any(check["name"] == "blank_audit_labels" and check["status"] == "fail" for check in result["checks"])
