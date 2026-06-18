import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_and_check_paper_layout.py"
SPEC = importlib.util.spec_from_file_location("build_and_check_paper_layout", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

build_and_check = MODULE.build_and_check


def test_build_and_check_runs_steps_and_writes_reports(tmp_path):
    seen = []

    def fake_runner(command, cwd, log_path):
        seen.append(command)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("ok\n", encoding="utf-8")
        return {
            "command": command,
            "cwd": str(cwd),
            "log": str(log_path),
            "returncode": 0,
            "status": "pass",
            "stdout_tail": "ok",
            "stderr_tail": "",
        }

    result = build_and_check(tmp_path, runner=fake_runner)

    assert result["status"] == "pass"
    assert [record["step"] for record in result["records"]] == [
        "generate_figures",
        "pdflatex_pass1",
        "bibtex",
        "pdflatex_pass2",
        "pdflatex_final",
        "icse_format",
        "layout_quality",
    ]
    assert any("generate_paper_figures.py" in part for part in seen[0])
    assert (tmp_path / "paper_layout_build_check.json").exists()
    assert (tmp_path / "paper_layout_build_check.md").exists()


def test_build_and_check_stops_after_failed_step(tmp_path):
    calls = 0

    def fake_runner(command, cwd, log_path):
        nonlocal calls
        calls += 1
        return {
            "command": command,
            "cwd": str(cwd),
            "log": str(log_path),
            "returncode": 1,
            "status": "fail",
            "stdout_tail": "",
            "stderr_tail": "boom",
        }

    result = build_and_check(tmp_path, runner=fake_runner)

    assert result["status"] == "fail"
    assert calls == 1
    assert result["records"][0]["step"] == "generate_figures"
