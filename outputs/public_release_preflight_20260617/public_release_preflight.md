# Public Release Preflight

Status: **ready_for_manual_publication**

| Check | Status | Evidence | Action |
|---|---:|---|---|
| archive_checksum | pass | outputs/zenodo_deposit_packet_20260617/files_to_upload/MergeDossier-Bench-anonymous-review.zip matches deposit summary. | Upload this exact archive. |
| sha256sums_match | pass | SHA256SUMS.txt matches the upload archive. | Use this checksum during deposit. |
| upload_manifest_match | pass | artifact_upload_manifest.csv records the upload archive and checksum. | Use the manifest as upload evidence. |
| metadata_fields | pass | Zenodo metadata template has required fields. | Copy fields into Zenodo after replacing placeholders. |
| publication_placeholders | warn | Placeholders remain: TO_BE_FILLED, TO_BE_FILLED_AFTER_ANONYMOUS_REVIEW, TO_BE_FILLED_PUBLIC_REPOSITORY_URL, TO_BE_FILLED_PAPER_URL_OR_DOI | Replace these only after real public author/repository/paper metadata exists. |
| claim_boundary_notes | pass | Metadata notes include required non-claim boundaries. | Keep these boundaries in the archive notes. |
| metadata_files_copied | pass | Deposit packet contains copied metadata templates. | Use the copies in the deposit packet. |
| post_publication_update_command | pass | Post-publication metadata update command is documented. | Run it after DOI/public URL exist. |
| copy_fields_boundary | pass | Zenodo/GitHub copy-field helpers include claim-boundary text. | Use these files while filling release portals. |
| doi_public_url_boundary | warn | DOI/public URL are correctly recorded as not yet minted/published. | Do not claim public availability until real values exist. |

## Boundary

Preflight readiness only. Passing this check does not mint a DOI, publish a public repository, or establish artifact availability.
