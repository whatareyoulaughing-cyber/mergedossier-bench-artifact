import importlib.util
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "check_release_zip_smoke.py"
SPEC = importlib.util.spec_from_file_location("check_release_zip_smoke", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
check_release_zip_smoke = MODULE.check_release_zip_smoke


def _write_fake_release_zip(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("pkg/pyproject.toml", "[project]\nname='x'\n")
        archive.writestr("pkg/src/mergedossier_bench/__init__.py", "")
        archive.writestr("pkg/examples/corpus/toy.json", "{}")
        archive.writestr("pkg/tests/test_cli_smoke.py", "")


def test_release_zip_smoke_passes_with_expected_outputs(tmp_path: Path):
    release = tmp_path / "release.zip"
    _write_fake_release_zip(release)

    def fake_runner(args, cwd, env, timeout):
        assert "PYTHONPATH" in env
        if "summarize" in args:
            out = cwd / "outputs/release_zip_smoke/corpus"
            out.mkdir(parents=True, exist_ok=True)
            (out / "summary.json").write_text("{}", encoding="utf-8")
            (out / "scores.jsonl").write_text("", encoding="utf-8")
        if "audit-provenance" in args:
            out = cwd / "outputs/release_zip_smoke/provenance"
            out.mkdir(parents=True, exist_ok=True)
            (out / "provenance_summary.json").write_text("{}", encoding="utf-8")
            (out / "uncited_evidence.jsonl").write_text("", encoding="utf-8")
        return {"command": args, "returncode": 0, "stdout_tail": "", "stderr_tail": ""}

    result = check_release_zip_smoke(release, tmp_path / "out", runner=fake_runner)

    assert result["status"] == "pass"
    assert [record["name"] for record in result["commands"]] == [
        "pytest_subset",
        "corpus_summary",
        "provenance_audit",
    ]
    assert (tmp_path / "out/release_zip_smoke.md").exists()


def test_release_zip_smoke_fails_on_command_error(tmp_path: Path):
    release = tmp_path / "release.zip"
    _write_fake_release_zip(release)

    def failing_runner(args, cwd, env, timeout):
        return {"command": args, "returncode": 2, "stdout_tail": "", "stderr_tail": "failed"}

    result = check_release_zip_smoke(release, tmp_path / "out", runner=failing_runner)

    assert result["status"] == "fail"
    assert "pytest_subset" in result["error"]


def test_release_zip_smoke_fails_without_package_root(tmp_path: Path):
    release = tmp_path / "release.zip"
    with zipfile.ZipFile(release, "w") as archive:
        archive.writestr("pkg/README.md", "missing pyproject and src")

    result = check_release_zip_smoke(release, tmp_path / "out")

    assert result["status"] == "fail"
    assert "Expected one package root" in result["error"]
