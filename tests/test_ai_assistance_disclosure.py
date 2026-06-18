import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

BUILD_SPEC = importlib.util.spec_from_file_location(
    "build_ai_assistance_disclosure_packet",
    ROOT / "scripts" / "build_ai_assistance_disclosure_packet.py",
)
assert BUILD_SPEC and BUILD_SPEC.loader
BUILD_MODULE = importlib.util.module_from_spec(BUILD_SPEC)
BUILD_SPEC.loader.exec_module(BUILD_MODULE)
build_ai_disclosure_packet = BUILD_MODULE.build_ai_disclosure_packet

CHECK_SPEC = importlib.util.spec_from_file_location(
    "check_ai_assistance_disclosure",
    ROOT / "scripts" / "check_ai_assistance_disclosure.py",
)
assert CHECK_SPEC and CHECK_SPEC.loader
CHECK_MODULE = importlib.util.module_from_spec(CHECK_SPEC)
CHECK_SPEC.loader.exec_module(CHECK_MODULE)
check_ai_disclosure = CHECK_MODULE.check_ai_disclosure


GOOD_DISCLOSURE = """# AI Assistance Disclosure Draft

The authors used AI coding and writing assistants during artifact development,
debugging, manuscript editing, and internal review. AI assistance was used to
generate draft code changes and suggest wording. The authors remained
responsible for all research decisions, corpus inclusion choices, annotation
labels, statistical outputs, citations, claims, and final manuscript text.

AI-generated suggestions were checked against repository artifacts before being
kept. AI tools were not treated as operators for the reported audit codes. The
reported AIDev-pop audit pass is a single-operator audit with delayed repeats,
and the manuscript does not claim inter-rater reliability, all-GitHub
population rates, reviewer utility, or authorship-group effects.
"""


def test_build_ai_disclosure_packet_and_check_pass(tmp_path: Path):
    source = tmp_path / "disclosure.md"
    source.write_text(GOOD_DISCLOSURE, encoding="utf-8")

    build_result = build_ai_disclosure_packet(source, tmp_path / "packet")
    check_result = check_ai_disclosure(source, tmp_path / "packet", out_dir=tmp_path / "check")

    assert build_result["status"] == "ready_for_portal_adaptation"
    assert check_result["status"] == "pass"
    assert (tmp_path / "packet/PORTAL_AI_DISCLOSURE.md").exists()
    assert (tmp_path / "check/ai_assistance_disclosure_check.md").exists()


def test_ai_disclosure_check_fails_old_or_dangerous_wording(tmp_path: Path):
    source = tmp_path / "disclosure.md"
    source.write_text(
        GOOD_DISCLOSURE
        + "\nAI annotator labels were validated by AI. The manuscript does not claim population-level rates.\n",
        encoding="utf-8",
    )
    build_ai_disclosure_packet(source, tmp_path / "packet")

    result = check_ai_disclosure(source, tmp_path / "packet")

    assert result["status"] == "fail"
    names = {failure["name"] for failure in result["failures"]}
    assert "forbidden:ai_annotator" in names
    assert "forbidden:validated_by_ai" in names
    assert "forbidden:old_population_rate_boundary" in names
