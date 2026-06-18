# Submission Checklist

## Before data collection

- [ ] Freeze research questions.
- [ ] Finalize data collection protocol.
- [ ] Define agent-authorship detection rules.
- [ ] Define privacy and redaction procedure.
- [ ] Prepare IRB/ethics review if human study is included.
- [ ] Pilot schema on 20 PRs.

## Before annotation

- [ ] Run annotator training.
- [ ] Pilot 30 PRs.
- [ ] Revise codebook.
- [ ] Define adjudication process.
- [ ] Define agreement metrics.

## Before modeling

- [ ] Freeze train/test splits if using predictive models.
- [ ] Document features.
- [ ] Define outcome variables.
- [ ] Pre-register main analyses internally.
- [ ] Include repository-level grouping where appropriate.

## Before writing

- [ ] Finalize title.
- [ ] Create Figure 1.
- [ ] Write abstract with the phrase "A diff is not a dossier" only if it fits the tone.
- [ ] Prepare related-work table showing differentiation.
- [ ] Prepare threats-to-validity section.
- [ ] Prepare artifact appendix.

## Before release

- [ ] Remove secrets and private data.
- [ ] Validate JSONL against schemas.
- [ ] Include dataset card.
- [ ] Include replication scripts.
- [ ] Include environment file.
- [ ] Include license.
- [ ] Include citation metadata.

## Artifact evaluation

- [ ] Run `python scripts/reproduce_artifact_smoke.py`.
- [ ] Confirm `outputs/artifact_smoke/artifact_smoke_log.json` records all
      successful commands.
- [ ] Confirm `pytest -q` passes inside the smoke workflow.
- [ ] Confirm provisional pilot files are marked as provisional.
- [ ] Confirm the artifact package includes `docs/12_artifact_evaluation.md`.
- [ ] Confirm the artifact package includes `docs/13_dataset_card.md`.
- [ ] Confirm the artifact package includes `docs/14_release_manifest.md`.
- [ ] Archive the final release on Zenodo or another DOI-bearing repository.
- [ ] Apply only for badges supported by the released artifact:
      Available after archival release, Functional when smoke checks pass, and
      Reusable only after the annotated pilot and dataset card are complete.
