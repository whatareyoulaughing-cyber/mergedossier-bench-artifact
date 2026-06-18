import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "check_manuscript_claim_hygiene.py"
SPEC = importlib.util.spec_from_file_location("check_manuscript_claim_hygiene", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
check_manuscript_claim_hygiene = MODULE.check_manuscript_claim_hygiene


SAFE_TEX = r"""
\title{MergeDossier-Bench: Measuring the Handoff-Evidence Gap in AI-Authored Pull Requests}
\newcommand{\slogan}{A diff is not a dossier.}
\newcommand{\provslogan}{A dossier must cite its evidence.}
This paper studies the handoff-evidence gap and review-evidence availability
within AIDev-pop. It uses a single-operator audit and a legacy triage score.
It is not a patch correctness benchmark and not a mergeability benchmark.
It is not reviewer utility evidence, not an AI-vs-human causal comparison, and
not all-GitHub population rates. These checks do not replace inter-rater
agreement.
\label{tab:claims-nonclaims}
\label{tab:handoff-gap}
\label{tab:tipping-point}
\label{tab:availability-intervals}
\label{tab:population-sample}
"""


def test_claim_hygiene_passes_safe_claim_boundary_text(tmp_path: Path):
    tex = tmp_path / "main.tex"
    tex.write_text(SAFE_TEX, encoding="utf-8")

    result = check_manuscript_claim_hygiene(tex, tmp_path / "out")

    assert result["status"] == "pass"
    assert result["finding_count"] == 0
    assert (tmp_path / "out/manuscript_claim_hygiene.md").exists()


def test_claim_hygiene_fails_on_forbidden_overclaim(tmp_path: Path):
    tex = tmp_path / "main.tex"
    tex.write_text(
        SAFE_TEX
        + "\nThis benchmark proves reviewer utility improvement and validated labels.\n"
        + "It shows AI-authored PRs are worse.\n",
        encoding="utf-8",
    )

    result = check_manuscript_claim_hygiene(tex, tmp_path / "out")

    assert result["status"] == "fail"
    names = {finding["name"] for finding in result["findings"]}
    assert "affirming_prove" in names
    assert "validated_labels" in names
    assert "ai_prs_worse" in names


def test_claim_hygiene_fails_when_required_anchor_missing(tmp_path: Path):
    tex = tmp_path / "main.tex"
    tex.write_text(SAFE_TEX.replace(r"\label{tab:handoff-gap}", ""), encoding="utf-8")

    result = check_manuscript_claim_hygiene(tex)

    assert result["status"] == "fail"
    assert any(finding["name"] == "handoff_gap_table" for finding in result["findings"])
