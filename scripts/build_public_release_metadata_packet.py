"""Build public archival-release metadata templates.

The script does not mint a DOI or claim public archival status. It prepares the
metadata files that must be edited after anonymous review before depositing the
artifact on Zenodo or a similar archive.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TITLE = "MergeDossier-Bench: Measuring the Handoff-Evidence Gap in AI-Authored Pull Requests"
VERSION = "0.1.0"


def _zenodo_metadata() -> dict[str, object]:
    return {
        "title": TITLE,
        "upload_type": "software",
        "publication_date": "TO_BE_FILLED",
        "creators": [
            {
                "name": "TO_BE_FILLED_AFTER_ANONYMOUS_REVIEW",
                "affiliation": "TO_BE_FILLED_AFTER_ANONYMOUS_REVIEW",
            }
        ],
        "description": (
            "MergeDossier-Bench is a provenance-aware benchmark and measurement framework "
            "for measuring review-evidence availability and the handoff-evidence gap in "
            "AI-authored pull requests. The release includes software, schemas, fixtures, "
            "a sanitized AIDev-pop sampling-frame manifest, a deterministic 500-PR sample, "
            "paper-facing result tables, external-audit handoff materials, and offline "
            "reproducibility checks."
        ),
        "version": VERSION,
        "license": "MIT",
        "keywords": [
            "software engineering",
            "AI-authored pull requests",
            "handoff-evidence gap",
            "review-evidence availability",
            "provenance",
            "benchmark",
        ],
        "related_identifiers": [
            {
                "identifier": "TO_BE_FILLED_PUBLIC_REPOSITORY_URL",
                "relation": "isSupplementTo",
                "resource_type": "software",
            },
            {
                "identifier": "TO_BE_FILLED_PAPER_URL_OR_DOI",
                "relation": "isSupplementTo",
                "resource_type": "publication-article",
            },
        ],
        "notes": (
            "This release supports bounded AIDev-pop handoff-evidence gap estimates. "
            "It does not claim patch correctness, mergeability, reviewer utility, "
            "AI-vs-human causal effects, all-GitHub population rates, or inter-rater "
            "reliability unless a completed external audit is added separately."
        ),
    }


def _github_release_notes() -> str:
    return "\n".join(
        [
            "# MergeDossier-Bench v0.1.0",
            "",
            "Public archival-release notes template. Replace placeholders before release.",
            "",
            "## Release Contents",
            "",
            "- MergeDossier schema and validation code.",
            "- CLI support for single dossiers, corpus summaries, provenance audit, perturbation checks, dossier cards, and pilot/population analysis outputs.",
            "- Synthetic fixtures and toy corpus examples.",
            "- Sanitized 33,596-row AIDev-pop population-frame manifest.",
            "- Deterministic 500-PR AIDev-pop sample manifest.",
            "- Completed single-operator audit CSV and generated handoff-evidence gap tables.",
            "- Dependency-sensitive audit results.",
            "- External-audit slice packet, analysis script, and sendable handoff zip.",
            "- ICSE-format paper PDF and paper-facing tables.",
            "",
            "## Claim Boundary",
            "",
            "This artifact measures review-evidence availability and the handoff-evidence gap within the declared AIDev-pop frame. It is not a correctness benchmark, mergeability benchmark, reviewer-utility study, AI-vs-human causal comparison, all-GitHub population estimate, or inter-rater-reliability claim.",
            "",
            "## Before Publishing",
            "",
            "- Replace anonymous author metadata in `CITATION.cff`, `pyproject.toml`, and Zenodo metadata.",
            "- Add public repository URL.",
            "- Add archival DOI after deposit.",
            "- Decide whether raw PR text remains excluded or receives separate privacy/secret screening.",
            "- Replace AI-assistance disclosure with the exact venue-required text.",
            "",
        ]
    )


def _checklist() -> str:
    rows = [
        ("Public repository URL", "missing", "Replace anonymous placeholders."),
        ("Archival DOI", "missing", "Mint through Zenodo or institutional archive."),
        ("Author metadata", "missing", "Replace anonymous author fields after review."),
        ("License metadata", "ready", "MIT license present; confirm holder before public release."),
        ("Sanitized sampling frame", "ready", "Text-free 33,596-row manifest exists."),
        ("Raw frame release decision", "open", "Keep excluded or run dedicated secret/privacy scrub."),
        ("External audit result", "open", "Packet and analysis path exist; independent sheet not completed."),
        ("ICSE format gate", "ready", "Current check passes with 8 pages and 0 warnings."),
        ("Paper readiness gate", "ready", "Current readiness check passes."),
    ]
    lines = [
        "# Public Release Checklist",
        "",
        "| Item | Status | Action |",
        "|---|---|---|",
    ]
    for item, status, action in rows:
        lines.append(f"| {item} | {status} | {action} |")
    lines.extend(
        [
            "",
            "Do not mark the artifact as archived, available, reusable, or externally validated until the relevant missing/open rows are resolved.",
            "",
        ]
    )
    return "\n".join(lines)


def _zenodo_copy_fields(metadata: dict[str, object]) -> str:
    creators = metadata.get("creators", [])
    creator_lines = []
    if isinstance(creators, list):
        for creator in creators:
            if isinstance(creator, dict):
                creator_lines.append(
                    f"- Name: `{creator.get('name', '')}`; Affiliation: `{creator.get('affiliation', '')}`"
                )
    related = metadata.get("related_identifiers", [])
    related_lines = []
    if isinstance(related, list):
        for item in related:
            if isinstance(item, dict):
                related_lines.append(
                    f"- `{item.get('identifier', '')}` / relation `{item.get('relation', '')}` / type `{item.get('resource_type', '')}`"
                )
    keywords = metadata.get("keywords", [])
    keywords_text = ", ".join(str(item) for item in keywords) if isinstance(keywords, list) else str(keywords)
    lines = [
        "# Zenodo Copy Fields",
        "",
        "Copy these fields into Zenodo after replacing placeholders with real public metadata.",
        "This file is a copy-paste helper only; it does not mint a DOI.",
        "",
        "## Required Fields",
        "",
        f"- Title: `{metadata.get('title', '')}`",
        f"- Upload type: `{metadata.get('upload_type', '')}`",
        f"- Publication date: `{metadata.get('publication_date', '')}`",
        f"- Version: `{metadata.get('version', '')}`",
        f"- License: `{metadata.get('license', '')}`",
        f"- Keywords: `{keywords_text}`",
        "",
        "## Creators",
        "",
        *creator_lines,
        "",
        "## Description",
        "",
        str(metadata.get("description", "")),
        "",
        "## Related Identifiers",
        "",
        *related_lines,
        "",
        "## Notes / Claim Boundary",
        "",
        str(metadata.get("notes", "")),
        "",
        "## Before Minting",
        "",
        "- Replace `TO_BE_FILLED` publication date.",
        "- Replace anonymous creator name and affiliation.",
        "- Replace public repository and paper URL/DOI placeholders.",
        "- Confirm the uploaded archive checksum matches `SHA256SUMS.txt`.",
        "- Do not claim public availability until the DOI is minted and links resolve.",
        "",
    ]
    return "\n".join(lines)


def _github_copy_fields() -> str:
    notes = _github_release_notes()
    return "\n".join(
        [
            "# GitHub Release Copy Fields",
            "",
            "Use these fields when creating the public repository release after anonymous review.",
            "Replace placeholders before publication.",
            "",
            "- Tag: `v0.1.0`",
            "- Release title: `MergeDossier-Bench v0.1.0`",
            "- Attach archive: `MergeDossier-Bench-anonymous-review.zip` or the final public archive produced after metadata replacement.",
            "- Attach/check checksum: `SHA256SUMS.txt`",
            "",
            "## Release Notes",
            "",
            notes,
            "",
            "## Boundary",
            "",
            "These fields prepare a public release. They do not by themselves create an archival DOI or prove external validation.",
            "",
        ]
    )


def build_public_release_metadata_packet(out_dir: Path) -> dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=True)
    zenodo_metadata = _zenodo_metadata()
    files = {
        "zenodo_metadata_template.json": json.dumps(zenodo_metadata, indent=2) + "\n",
        "github_release_notes_template.md": _github_release_notes(),
        "public_release_checklist.md": _checklist(),
        "ZENODO_COPY_FIELDS.md": _zenodo_copy_fields(zenodo_metadata),
        "GITHUB_RELEASE_COPY_FIELDS.md": _github_copy_fields(),
    }
    for name, content in files.items():
        (out_dir / name).write_text(content, encoding="utf-8")
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "template_only",
        "claim_boundary": "No DOI, public repository URL, or public archival status is claimed by this packet.",
        "files": sorted(files),
    }
    (out_dir / "public_release_metadata_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build public release metadata templates")
    parser.add_argument("--out", default="outputs/public_release_metadata_20260617")
    args = parser.parse_args(argv)
    summary = build_public_release_metadata_packet(ROOT / args.out)
    print(f"Public release metadata packet written: {args.out} ({len(summary['files'])} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
