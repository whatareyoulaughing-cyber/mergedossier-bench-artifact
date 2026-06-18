#!/usr/bin/env bash
set -euo pipefail
python -m mergedossier_bench.cli validate --kind instance --file examples/toy_pr_instance.json
python -m mergedossier_bench.cli validate --kind dossier --file examples/toy_merge_dossier.json
python -m mergedossier_bench.cli validate --kind annotation --file examples/toy_annotation.json
python -m mergedossier_bench.cli score --dossier examples/toy_merge_dossier.json --out /tmp/mergedossier_toy_score.json
python -m mergedossier_bench.cli validate --kind score --file /tmp/mergedossier_toy_score.json
python -m mergedossier_bench.cli build-dossier --instance examples/toy_pr_instance.json --out /tmp/mergedossier_skeleton.json
python -m mergedossier_bench.cli leaderboard --reports /tmp/mergedossier_toy_score.json --out /tmp/mergedossier_leaderboard.csv
echo "Toy pipeline complete. Outputs in /tmp/mergedossier_*.json and /tmp/mergedossier_leaderboard.csv"
