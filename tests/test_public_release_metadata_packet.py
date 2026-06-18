import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "build_public_release_metadata_packet", ROOT / "scripts" / "build_public_release_metadata_packet.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
build_public_release_metadata_packet = MODULE.build_public_release_metadata_packet


def test_public_release_metadata_packet_uses_placeholders_not_fake_doi(tmp_path: Path):
    summary = build_public_release_metadata_packet(tmp_path)

    assert summary["status"] == "template_only"
    zenodo = json.loads((tmp_path / "zenodo_metadata_template.json").read_text(encoding="utf-8"))
    assert zenodo["creators"][0]["name"] == "TO_BE_FILLED_AFTER_ANONYMOUS_REVIEW"
    assert zenodo["related_identifiers"][0]["identifier"] == "TO_BE_FILLED_PUBLIC_REPOSITORY_URL"
    assert "doi.org" not in json.dumps(zenodo).lower()

    checklist = (tmp_path / "public_release_checklist.md").read_text(encoding="utf-8")
    assert "| Archival DOI | missing |" in checklist
    assert "Do not mark the artifact as archived" in checklist

    release_notes = (tmp_path / "github_release_notes_template.md").read_text(encoding="utf-8")
    assert "not a correctness benchmark" in release_notes

    zenodo_copy = (tmp_path / "ZENODO_COPY_FIELDS.md").read_text(encoding="utf-8")
    assert "TO_BE_FILLED_PUBLIC_REPOSITORY_URL" in zenodo_copy
    assert "Notes / Claim Boundary" in zenodo_copy
    assert "does not mint a DOI" in zenodo_copy

    github_copy = (tmp_path / "GITHUB_RELEASE_COPY_FIELDS.md").read_text(encoding="utf-8")
    assert "Tag: `v0.1.0`" in github_copy
    assert "not a correctness benchmark" in github_copy
    assert "do not by themselves create an archival DOI" in github_copy
