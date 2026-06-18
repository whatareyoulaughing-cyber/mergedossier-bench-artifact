#!/usr/bin/env python3
"""Generate a Label Studio XML config for MergeDossier audit coding."""

import argparse
from pathlib import Path
from xml.sax.saxutils import escape

EVIDENCE_CATEGORIES = [
    "intent_evidence",
    "requirement_evidence",
    "test_evidence",
    "risk_analysis",
    "scope_evidence",
    "trace_evidence",
    "dependency_evidence",
    "regression_evidence",
    "rationale_evidence",
    "ownership_handoff",
]

LABELS = ["present", "partially_present", "missing", "not_applicable"]


def build_config() -> str:
    """Build the Label Studio XML interface.

    The interface asks operators to code whether each evidence category is
    available in the dossier, not whether the patch is correct.
    """
    category_controls = "\n".join(
        f"""  <Header value="{escape(name.replace('_', ' ').title())}"/>
  <Choices name="{name}" toName="task_context" choice="single" showInLine="true">
{chr(10).join(f'    <Choice value="{label}"/>' for label in LABELS)}
  </Choices>
  <TextArea name="{name}_comment" toName="task_context" rows="2" placeholder="Optional short comment for {escape(name)}"/>"""
        for name in EVIDENCE_CATEGORIES
    )
    return f"""<View>
  <Header value="MergeDossier-Bench Annotation"/>
  <Text name="task_context" value="Instance: $instance_id&#10;Repository: $repo&#10;PR: $pr_number $pr_url&#10;Title: $title&#10;&#10;PR body or summary:&#10;$pr_body&#10;&#10;Issue summary:&#10;$issue_summary&#10;&#10;Changed files summary:&#10;$changed_files_summary&#10;&#10;Existing score: $existing_score&#10;Missing evidence: $missing_evidence&#10;&#10;Dossier evidence:&#10;$dossier_text"/>
  <Header value="Review-evidence availability audit codes"/>
{category_controls}
  <Header value="Legacy artifact triage"/>
  <Choices name="overall_acceptability" toName="task_context" choice="single" showInLine="true">
    <Choice value="insufficient"/>
    <Choice value="thin"/>
    <Choice value="adequate"/>
    <Choice value="strong"/>
  </Choices>
  <Header value="Review confidence"/>
  <Rating name="review_confidence" toName="task_context" maxRating="5" icon="star" size="medium"/>
  <TextArea name="notes" toName="task_context" rows="3" placeholder="Optional notes on review-evidence availability, uncertainty, or adjudication needs"/>
</View>
"""

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a MergeDossier-Bench Label Studio XML config")
    parser.add_argument("--out", default="label_studio_mergedossier_config.xml")
    args = parser.parse_args()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_config(), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
