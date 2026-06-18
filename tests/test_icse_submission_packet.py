import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "build_icse_submission_packet.py"
SPEC = importlib.util.spec_from_file_location("build_icse_submission_packet", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
build_icse_submission_packet = MODULE.build_icse_submission_packet
extract_paper_metadata = MODULE.extract_paper_metadata


def _write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_extract_paper_metadata_expands_tool_macro(tmp_path: Path):
    tex = tmp_path / "main.tex"
    tex.write_text(
        r"""
\newcommand{\tool}{MergeDossier-Bench}
\title{\tool: Measuring the Handoff-Evidence Gap}
\begin{abstract}
\tool{} measures review-evidence availability, not correctness.
\end{abstract}
\begin{IEEEkeywords}
AI-assisted software engineering, provenance
\end{IEEEkeywords}
""",
        encoding="utf-8",
    )

    metadata = extract_paper_metadata(tex)

    assert metadata["title"] == "MergeDossier-Bench: Measuring the Handoff-Evidence Gap"
    assert "MergeDossier-Bench measures" in metadata["abstract"]
    assert metadata["abstract_word_count"] > 3
    assert metadata["keywords"] == "AI-assisted software engineering, provenance"


def test_build_icse_submission_packet_writes_manifest_and_checklist(tmp_path: Path):
    root = tmp_path
    paper = root / "paper"
    paper.mkdir()
    (paper / "main.tex").write_text(
        r"""
\title{MergeDossier-Bench: Test Title}
\begin{abstract}A bounded abstract for the submission packet.\end{abstract}
\begin{IEEEkeywords}benchmark, evidence\end{IEEEkeywords}
""",
        encoding="utf-8",
    )
    (paper / "main.pdf").write_bytes(b"%PDF")
    release = root / "outputs/release"
    release.mkdir(parents=True)
    (release / "MergeDossier-Bench-anonymous-review.zip").write_bytes(b"zip")
    _write_json(
        release / "release_zip_summary.json",
        {"file_count": 3, "zip_bytes": 3},
    )
    deposit = root / "outputs/zenodo_deposit_packet_20260617"
    deposit.mkdir(parents=True)
    (deposit / "SHA256SUMS.txt").write_text("abc  files_to_upload/release.zip\n", encoding="utf-8")
    _write_json(
        root / "outputs/submission_blocker_dashboard_20260617/submission_blocker_dashboard.json",
        {"status": "blocked_on_external_actions", "p0_open_count": 2},
    )
    _write_json(
        root / "outputs/paper_readiness_check_20260617_handoff_gap/paper_readiness_check.json",
        {"status": "pass"},
    )
    _write_json(
        root / "outputs/submission_action_packet_20260617/action_status.json",
        {"status": "action_required"},
    )

    result = build_icse_submission_packet(root, root / "out")

    assert result["status"] == "ready_except_external_actions"
    assert result["paper_metadata"]["title"] == "MergeDossier-Bench: Test Title"
    assert (root / "out/files_for_submission/main.pdf").exists()
    assert (root / "out/files_for_submission/MergeDossier-Bench-anonymous-review.zip").exists()
    assert (root / "out/PORTAL_FIELDS.md").exists()
    assert (root / "out/ICSE_SUBMISSION_CHECKLIST_ZH.md").exists()
    assert (root / "out/submission_file_manifest.csv").exists()
    checklist = (root / "out/ICSE_SUBMISSION_CHECKLIST_ZH.md").read_text(encoding="utf-8")
    assert "P0 open count" in checklist
    assert "Do not claim patch correctness" in checklist
