import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "check_final_pdf_proofread.py"
SPEC = importlib.util.spec_from_file_location("check_final_pdf_proofread", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
check_text_quality = MODULE.check_text_quality
summarize = MODULE.summarize


def test_final_pdf_text_quality_passes_on_required_identity_phrases():
    text = """
    MergeDossier-Bench: Measuring the Handoff-Evidence Gap.
    A diff is not a dossier. A dossier must cite its evidence.
    The AIDev-pop sample uses a single-operator audit.
    """
    result = summarize(check_text_quality(text))
    assert result["status"] == "pass"


def test_final_pdf_text_quality_fails_on_placeholder_tokens():
    text = """
    MergeDossier-Bench Handoff-Evidence Gap AIDev-pop single-operator.
    A diff is not a dossier. A dossier must cite its evidence.
    TODO replace this citation [??].
    """
    checks = check_text_quality(text)
    placeholder = next(check for check in checks if check["name"] == "placeholder_tokens")
    assert placeholder["status"] == "fail"
    assert "todo" in placeholder["detail"]
    assert "unresolved_reference" in placeholder["detail"]
