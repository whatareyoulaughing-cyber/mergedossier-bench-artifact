import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "update_public_release_metadata", ROOT / "scripts" / "update_public_release_metadata.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
normalize_doi = MODULE.normalize_doi
update_public_release_metadata = MODULE.update_public_release_metadata
preview_public_release_metadata_update = MODULE.preview_public_release_metadata_update


def test_normalize_doi_accepts_url_and_plain_doi():
    assert normalize_doi("10.5281/zenodo.123") == (
        "10.5281/zenodo.123",
        "https://doi.org/10.5281/zenodo.123",
    )
    assert normalize_doi("https://doi.org/10.5281/zenodo.456") == (
        "10.5281/zenodo.456",
        "https://doi.org/10.5281/zenodo.456",
    )


def test_update_public_release_metadata_replaces_placeholders(tmp_path: Path):
    citation = tmp_path / "CITATION.cff"
    citation.write_text(
        'title: "X"\nauthors:\n  - name: "Anonymous Author(s)"\nversion: 0.1.0\nrepository-code: "To be added after anonymous review."\nurl: "To be added after anonymous review."\n',
        encoding="utf-8",
    )
    readme = tmp_path / "README.md"
    readme.write_text("# Project\n\n## License\n\nMIT\n", encoding="utf-8")
    dataset = tmp_path / "dataset.md"
    dataset.write_text("# Dataset\n", encoding="utf-8")
    zenodo = tmp_path / "zenodo.json"
    zenodo.write_text(
        json.dumps(
            {
                "publication_date": "TO_BE_FILLED",
                "creators": [{"name": "TO_BE_FILLED_AFTER_ANONYMOUS_REVIEW", "affiliation": "X"}],
                "related_identifiers": [
                    {"identifier": "TO_BE_FILLED_PUBLIC_REPOSITORY_URL", "resource_type": "software"},
                    {"identifier": "TO_BE_FILLED_PAPER_URL_OR_DOI", "resource_type": "publication-article"},
                ],
            }
        ),
        encoding="utf-8",
    )
    deposit = tmp_path / "deposit.json"
    deposit.write_text(json.dumps({"doi_minted": False, "public_repository_url_recorded": False}), encoding="utf-8")
    links = tmp_path / "links.json"

    update_public_release_metadata(
        doi_value="10.5281/zenodo.123",
        repo_url="https://github.com/example/repo",
        paper_url="https://doi.org/10.1145/example",
        author_name="Doe, Jane",
        affiliation="Example University",
        publication_date="2026-06-17",
        citation_path=citation,
        readme_path=readme,
        dataset_card_path=dataset,
        zenodo_metadata_path=zenodo,
        deposit_summary_path=deposit,
        links_summary_path=links,
    )

    assert "Anonymous" not in citation.read_text(encoding="utf-8")
    assert 'doi: "10.5281/zenodo.123"' in citation.read_text(encoding="utf-8")
    assert "Public Archival Metadata" in readme.read_text(encoding="utf-8")
    assert json.loads(zenodo.read_text(encoding="utf-8"))["publication_date"] == "2026-06-17"
    assert json.loads(deposit.read_text(encoding="utf-8"))["doi_minted"] is True
    assert json.loads(links.read_text(encoding="utf-8"))["artifact_doi"] == "10.5281/zenodo.123"


def test_preview_public_release_metadata_update_does_not_modify_files(tmp_path: Path):
    citation = tmp_path / "CITATION.cff"
    citation.write_text('authors:\n  - name: "Anonymous Author(s)"\n', encoding="utf-8")
    readme = tmp_path / "README.md"
    readme.write_text("# Project\n", encoding="utf-8")
    dataset = tmp_path / "dataset.md"
    dataset.write_text("# Dataset\n", encoding="utf-8")
    zenodo = tmp_path / "zenodo.json"
    zenodo.write_text("{}", encoding="utf-8")
    deposit = tmp_path / "deposit.json"
    deposit.write_text("{}", encoding="utf-8")
    links = tmp_path / "links.json"

    preview = preview_public_release_metadata_update(
        doi_value="https://doi.org/10.5281/zenodo.999",
        repo_url="https://github.com/example/repo",
        paper_url="https://doi.org/10.1145/example",
        author_name="Doe, Jane",
        affiliation="Example University",
        publication_date="2026-06-17",
        citation_path=citation,
        readme_path=readme,
        dataset_card_path=dataset,
        zenodo_metadata_path=zenodo,
        deposit_summary_path=deposit,
        links_summary_path=links,
    )

    assert preview["status"] == "ready_to_update"
    assert preview["normalized_values"]["doi"] == "10.5281/zenodo.999"
    assert str(links) == preview["would_write"]
    assert "Anonymous Author(s)" in citation.read_text(encoding="utf-8")
    assert not links.exists()
