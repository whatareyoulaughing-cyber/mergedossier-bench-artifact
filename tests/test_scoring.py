from mergedossier_bench.scoring import readiness_band, score_dossier
from mergedossier_bench.validators import load_json


def test_readiness_band():
    assert readiness_band(10) == "insufficient"
    assert readiness_band(45) == "thin"
    assert readiness_band(65) == "adequate"
    assert readiness_band(90) == "strong"


def test_toy_score_has_expected_shape():
    dossier = load_json("examples/toy_merge_dossier.json")
    report = score_dossier(dossier)
    assert report["dossier_id"] == "dossier-toy-owner-repo-42"
    assert 0 <= report["evidence_sufficiency_score"] <= 100
    assert "risk_analysis" in report["missing_evidence"]
    assert "ownership_handoff" in report["missing_evidence"]
