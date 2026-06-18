"""Update public-release metadata after a real DOI and public URL exist.

This is a post-anonymous-review helper. It should be run only after the archive
has actually been published and the public repository URL is known.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

START = "<!-- public-release-metadata:start -->"
END = "<!-- public-release-metadata:end -->"


def normalize_doi(value: str) -> tuple[str, str]:
    raw = value.strip()
    raw = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", raw, flags=re.I)
    if not raw.startswith("10."):
        raise ValueError("DOI must start with '10.' or be a https://doi.org/ URL")
    return raw, f"https://doi.org/{raw}"


def replace_marked_section(text: str, section: str) -> str:
    block = f"{START}\n{section.rstrip()}\n{END}"
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), flags=re.S)
    if pattern.search(text):
        return pattern.sub(block, text)
    if "\n## License" in text:
        return text.replace("\n## License", f"\n{block}\n\n## License", 1)
    return text.rstrip() + "\n\n" + block + "\n"


def update_citation(path: Path, author_name: str, repo_url: str, doi: str, doi_url: str) -> None:
    text = path.read_text(encoding="utf-8")
    text = re.sub(r'- name: "Anonymous Author\(s\)"', f'- name: "{author_name}"', text)
    text = re.sub(r'repository-code: ".*"', f'repository-code: "{repo_url}"', text)
    text = re.sub(r'url: ".*"', f'url: "{doi_url}"', text)
    if re.search(r"^doi:", text, flags=re.M):
        text = re.sub(r'^doi: ".*"', f'doi: "{doi}"', text, flags=re.M)
    else:
        text = text.replace("version: 0.1.0\n", f"version: 0.1.0\ndoi: \"{doi}\"\n", 1)
    path.write_text(text, encoding="utf-8")


def update_zenodo_metadata(
    path: Path,
    author_name: str,
    affiliation: str,
    repo_url: str,
    paper_url: str,
    publication_date: str,
) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    data["publication_date"] = publication_date
    data["creators"] = [{"name": author_name, "affiliation": affiliation}]
    for item in data.get("related_identifiers", []):
        if item.get("resource_type") == "software":
            item["identifier"] = repo_url
        elif item.get("resource_type") == "publication-article":
            item["identifier"] = paper_url
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def update_markdown_metadata(path: Path, doi: str, doi_url: str, repo_url: str, paper_url: str, publication_date: str) -> None:
    text = path.read_text(encoding="utf-8")
    section = "\n".join(
        [
            "## Public Archival Metadata",
            "",
            f"- Artifact DOI: [{doi}]({doi_url})",
            f"- Public repository: [{repo_url}]({repo_url})",
            f"- Paper URL/DOI: [{paper_url}]({paper_url})",
            f"- Release date: {publication_date}",
        ]
    )
    path.write_text(replace_marked_section(text, section), encoding="utf-8")


def update_deposit_summary(path: Path, doi: str, doi_url: str, repo_url: str, publication_date: str) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    data["doi_minted"] = True
    data["public_repository_url_recorded"] = True
    data["artifact_doi"] = doi
    data["artifact_doi_url"] = doi_url
    data["public_repository_url"] = repo_url
    data["publication_date"] = publication_date
    data["claim_boundary"] = (
        "This packet records a published archival DOI and public repository URL. "
        "It does not establish external audit completion or empirical claims beyond the paper scope."
    )
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def write_links_summary(out_path: Path, doi: str, doi_url: str, repo_url: str, paper_url: str, publication_date: str) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "artifact_doi": doi,
        "artifact_doi_url": doi_url,
        "public_repository_url": repo_url,
        "paper_url_or_doi": paper_url,
        "publication_date": publication_date,
        "status": "public_release_links_recorded",
    }
    out_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def preview_public_release_metadata_update(
    *,
    doi_value: str,
    repo_url: str,
    paper_url: str,
    author_name: str,
    affiliation: str,
    publication_date: str,
    citation_path: Path,
    readme_path: Path,
    dataset_card_path: Path,
    zenodo_metadata_path: Path,
    deposit_summary_path: Path,
    links_summary_path: Path,
) -> dict[str, Any]:
    doi, doi_url = normalize_doi(doi_value)
    required_paths = [
        citation_path,
        readme_path,
        dataset_card_path,
        zenodo_metadata_path,
        deposit_summary_path,
    ]
    missing = [str(path) for path in required_paths if not path.exists()]
    placeholders = {
        "doi": doi,
        "doi_url": doi_url,
        "repo_url": repo_url,
        "paper_url": paper_url,
        "author_name": author_name,
        "affiliation": affiliation,
        "publication_date": publication_date,
    }
    return {
        "status": "ready_to_update" if not missing else "missing_inputs",
        "missing_inputs": missing,
        "would_update": [str(path) for path in required_paths],
        "would_write": str(links_summary_path),
        "normalized_values": placeholders,
        "claim_boundary": (
            "Dry-run only. No public-release metadata files were modified, and no DOI/public URL "
            "is claimed unless the update command is run after real publication."
        ),
    }


def update_public_release_metadata(
    *,
    doi_value: str,
    repo_url: str,
    paper_url: str,
    author_name: str,
    affiliation: str,
    publication_date: str,
    citation_path: Path,
    readme_path: Path,
    dataset_card_path: Path,
    zenodo_metadata_path: Path,
    deposit_summary_path: Path,
    links_summary_path: Path,
) -> dict[str, str]:
    doi, doi_url = normalize_doi(doi_value)
    update_citation(citation_path, author_name, repo_url, doi, doi_url)
    update_zenodo_metadata(zenodo_metadata_path, author_name, affiliation, repo_url, paper_url, publication_date)
    update_markdown_metadata(readme_path, doi, doi_url, repo_url, paper_url, publication_date)
    update_markdown_metadata(dataset_card_path, doi, doi_url, repo_url, paper_url, publication_date)
    update_deposit_summary(deposit_summary_path, doi, doi_url, repo_url, publication_date)
    write_links_summary(links_summary_path, doi, doi_url, repo_url, paper_url, publication_date)
    return {
        "artifact_doi": doi,
        "artifact_doi_url": doi_url,
        "public_repository_url": repo_url,
        "paper_url_or_doi": paper_url,
        "publication_date": publication_date,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Update public-release metadata after DOI minting")
    parser.add_argument("--doi", required=True, help="Artifact DOI, e.g. 10.5281/zenodo.x")
    parser.add_argument("--repo-url", required=True, help="Public repository URL")
    parser.add_argument("--paper-url", required=True, help="Paper URL or DOI URL")
    parser.add_argument("--author-name", required=True, help="Public author name for metadata")
    parser.add_argument("--affiliation", required=True, help="Public author affiliation")
    parser.add_argument("--publication-date", default=date.today().isoformat())
    parser.add_argument("--citation", default="CITATION.cff")
    parser.add_argument("--readme", default="README.md")
    parser.add_argument("--dataset-card", default="docs/13_dataset_card.md")
    parser.add_argument("--zenodo-metadata", default="outputs/public_release_metadata_20260617/zenodo_metadata_template.json")
    parser.add_argument("--deposit-summary", default="outputs/zenodo_deposit_packet_20260617/deposit_packet_summary.json")
    parser.add_argument("--links-summary", default="outputs/public_release_metadata_20260617/public_release_links.json")
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs and write a preview without modifying metadata files.")
    parser.add_argument("--preview-out", default="outputs/public_release_update_preview_20260617/public_release_update_preview.json")
    args = parser.parse_args(argv)
    common = {
        "doi_value": args.doi,
        "repo_url": args.repo_url,
        "paper_url": args.paper_url,
        "author_name": args.author_name,
        "affiliation": args.affiliation,
        "publication_date": args.publication_date,
        "citation_path": ROOT / args.citation,
        "readme_path": ROOT / args.readme,
        "dataset_card_path": ROOT / args.dataset_card,
        "zenodo_metadata_path": ROOT / args.zenodo_metadata,
        "deposit_summary_path": ROOT / args.deposit_summary,
        "links_summary_path": ROOT / args.links_summary,
    }
    if args.dry_run:
        preview = preview_public_release_metadata_update(**common)
        preview_path = ROOT / args.preview_out
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        preview_path.write_text(json.dumps(preview, indent=2) + "\n", encoding="utf-8")
        print(f"Public release metadata dry-run: {preview['status']} -> {args.preview_out}")
        return 0 if preview["status"] == "ready_to_update" else 1
    result = update_public_release_metadata(
        **common,
    )
    print(f"Public release metadata updated: {result['artifact_doi_url']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
