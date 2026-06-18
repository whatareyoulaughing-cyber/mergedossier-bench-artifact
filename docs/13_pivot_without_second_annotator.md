# Pivot Without A Second Annotator

The current defensible contribution is provenance-aware, auditable measurement
infrastructure plus a descriptive pilot. It should not be framed as an
inter-rater-reliability study.

## Current Boundary

If only one annotator is available, the paper can report delayed-repeat
self-consistency. That checks whether the same annotator made stable decisions
after a delay. It does not establish independent inter-rater reliability.

The pilot corpus can demonstrate:

- the schema and scoring pipeline run end to end;
- dossiers can be summarized as a corpus;
- annotation tasks and spreadsheet exports can be produced;
- evidence provenance can be audited;
- public pilot evidence gaps can be described for the analyzed corpus.

It cannot support:

- population estimates;
- AI-versus-human authorship effects;
- patch correctness;
- mergeability;
- reviewer utility;
- independent annotator agreement.

## Practical Path

The best one-person path is to make the measurement infrastructure more
auditable:

- cite evidence with provenance snippets;
- detect uncited evidence;
- report observed versus inferred evidence;
- run perturbation checks over synthetic oracle fixtures;
- generate dossier cards for manual inspection;
- keep pilot-analysis outputs descriptive and explicitly bounded.

Future scaling can add a second annotator or a small external audit slice
without changing the core artifact.
