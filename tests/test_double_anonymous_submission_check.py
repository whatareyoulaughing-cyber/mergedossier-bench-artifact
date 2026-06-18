import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "check_double_anonymous_submission.py"
SPEC = importlib.util.spec_from_file_location("check_double_anonymous_submission", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
check_double_anonymous_text = MODULE.check_double_anonymous_text
summarize = MODULE.summarize


def test_double_anonymous_text_passes_anonymous_front_matter():
    pdf_text = (
        "MergeDossier-Bench: Measuring the Handoff-Evidence Gap\n"
        "Anonymous Author(s)\n\n"
        "Abstract\n"
        "This paper studies review-evidence availability.\n"
        "References\n"
        "A paper from Delft University appears here, outside front matter.\n"
    )
    tex_text = r"\author{\IEEEauthorblockN{Anonymous Author(s)}}"

    result = summarize(check_double_anonymous_text(pdf_text, "Title: x", tex_text))

    assert result["status"] == "pass"


def test_double_anonymous_text_fails_email_affiliation_and_acknowledgment():
    pdf_text = (
        "MergeDossier-Bench\n"
        "Anonymous Author(s)\n"
        "Department of Computer Science\n"
        "author@example.edu\n\n"
        "Abstract\n"
        "Acknowledgments. This was funded by a grant.\n"
    )
    tex_text = r"\author{\IEEEauthorblockN{Alice Smith}\IEEEauthorblockA{University X}}"

    result = summarize(check_double_anonymous_text(pdf_text, "C:\\Users\\alice\\paper.pdf", tex_text))

    assert result["status"] == "fail"
    names = {check["name"] for check in result["checks"] if check["status"] == "fail"}
    assert "front_matter_identity" in names
    assert "full_pdf_identity_leaks" in names
    assert "tex_author_block" in names
