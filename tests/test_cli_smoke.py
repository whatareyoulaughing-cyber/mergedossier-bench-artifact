import json
from pathlib import Path

from mergedossier_bench.cli import main


def test_cli_score(tmp_path):
    out = tmp_path / "score.json"
    code = main(["score", "--dossier", "examples/toy_merge_dossier.json", "--out", str(out)])
    assert code == 0
    report = json.loads(out.read_text())
    assert report["readiness_band"] in {"insufficient", "thin", "adequate", "strong"}


def test_cli_build_dossier(tmp_path):
    out = tmp_path / "dossier.json"
    code = main(["build-dossier", "--instance", "examples/toy_pr_instance.json", "--out", str(out)])
    assert code == 0
    dossier = json.loads(out.read_text())
    assert dossier["instance_id"] == "toy-owner-repo-42"
    assert "evidence" in dossier
