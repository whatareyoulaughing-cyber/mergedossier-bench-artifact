import importlib.util
import json
from email import policy
from email.parser import BytesParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "build_external_audit_send_now_packet.py"
SPEC = importlib.util.spec_from_file_location("build_external_audit_send_now_packet", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
build_external_audit_send_now_packet = MODULE.build_external_audit_send_now_packet


def test_external_audit_send_now_packet_copies_zip_and_writes_templates(tmp_path: Path):
    zip_path = tmp_path / "outputs/external_audit_handoff_20260617/MergeDossier-external-audit-handoff.zip"
    zip_path.parent.mkdir(parents=True)
    zip_path.write_bytes(b"zip")

    result = build_external_audit_send_now_packet(tmp_path, tmp_path / "out")

    assert result["status"] == "ready_to_send"
    assert result["handoff_zip_copied"] is True
    assert (tmp_path / "out/MergeDossier-external-audit-handoff.zip").exists()
    zh = (tmp_path / "out/SEND_NOW_EMAIL_ZH.md").read_text(encoding="utf-8")
    en = (tmp_path / "out/SEND_NOW_EMAIL_EN.md").read_text(encoding="utf-8")
    checklist = (tmp_path / "out/ATTACHMENT_AND_RETURN_CHECKLIST.md").read_text(encoding="utf-8")
    manifest = json.loads((tmp_path / "out/send_now_manifest.json").read_text(encoding="utf-8"))
    assert "60-90" in zh
    assert "external_audit_sheet.xlsx" in zh
    assert "Please do not judge code correctness" in en
    assert "check_external_audit_return.py" in checklist
    assert manifest["status"] == "ready_to_send"
    assert manifest["eml_files_available"] is True
    assert (tmp_path / "out/SEND_NOW_EMAIL_ZH_WINDOWS.md").exists()
    eml_path = tmp_path / "out/SEND_NOW_EMAIL_EN.eml"
    assert eml_path.exists()
    message = BytesParser(policy=policy.default).parsebytes(eml_path.read_bytes())
    attachments = list(message.iter_attachments())
    assert message["To"] == "external-auditor-email"
    assert "external audit slice" in message["Subject"]
    assert len(attachments) == 1
    assert attachments[0].get_filename() == "MergeDossier-external-audit-handoff.zip"


def test_external_audit_send_now_packet_reports_missing_zip(tmp_path: Path):
    result = build_external_audit_send_now_packet(tmp_path, tmp_path / "out")

    assert result["status"] == "missing_handoff_zip"
    assert result["handoff_zip_copied"] is False
    assert result["eml_files_available"] is False
    assert "must not be cited" in result["send_boundary"]
