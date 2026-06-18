import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check_paper_readiness.py"
SPEC = importlib.util.spec_from_file_location("check_paper_readiness", SCRIPT_PATH)
assert SPEC is not None
check_paper_readiness = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(check_paper_readiness)

readiness_status = check_paper_readiness.readiness_status
run_readiness = check_paper_readiness.run_readiness


def test_readiness_status_needs_human_labels_when_machine_gates_pass():
    records = [{"status": "pass"}, {"status": "pass"}]

    assert readiness_status(records, "annotation_template_only", require_completed=False) == "needs_human_labels"
    assert readiness_status(records, "annotation_template_only", require_completed=True) == "fail"
    assert readiness_status(records, "completed_annotation_csv", require_completed=True) == "pass"


def test_readiness_status_fails_on_failed_machine_gate():
    records = [{"status": "pass"}, {"status": "fail"}]

    assert readiness_status(records, "completed_annotation_csv", require_completed=False) == "fail"


def test_run_readiness_with_fake_runner_writes_reports(tmp_path, monkeypatch):
    def fake_runner(args, env):
        return {
            "name": " ".join(args),
            "command": args,
            "returncode": 0,
            "status": "pass",
            "stdout_tail": "ok",
            "stderr_tail": "",
        }

    monkeypatch.setattr(check_paper_readiness, "annotation_validation_command", lambda require: (["validate"], "annotation_template_only", True))

    result = run_readiness(tmp_path, require_completed_annotations=False, runner=fake_runner)

    assert result["status"] == "needs_human_labels"
    assert result["annotation_state"] == "annotation_template_only"
    gates = {record["gate"] for record in result["records"]}
    assert "layout_quality" in gates
    assert "final_pdf_proofread" in gates
    assert "manuscript_claim_hygiene" in gates
    assert "double_anonymous_submission" in gates
    assert (tmp_path / "paper_readiness_check.json").exists()
    assert (tmp_path / "paper_readiness_check.md").exists()


def test_run_readiness_strict_mode_fails_without_completed_annotations(tmp_path, monkeypatch):
    def fake_runner(args, env):
        return {
            "name": " ".join(args),
            "command": args,
            "returncode": 0,
            "status": "pass",
            "stdout_tail": "ok",
            "stderr_tail": "",
        }

    monkeypatch.setattr(check_paper_readiness, "annotation_validation_command", lambda require: (["validate"], "annotation_template_only", False))

    result = run_readiness(tmp_path, require_completed_annotations=True, runner=fake_runner)

    assert result["status"] == "fail"
    assert result["records"][-1]["gate"] == "annotation_csv"
    assert result["records"][-1]["status"] == "fail"
