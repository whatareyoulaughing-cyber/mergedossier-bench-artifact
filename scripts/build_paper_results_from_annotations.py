"""Build paper-ready result snippets from completed annotation exports."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

from mergedossier_bench.annotation_stats import write_annotation_stats
from mergedossier_bench.label_studio import EVIDENCE_CATEGORIES, LABEL_VALUES, validate_annotation_csv

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from build_adjudication_sheet import build_adjudication_sheet


def latex_escape(value: Any) -> str:
    text = str(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in text)


def percent(value: float | int | None) -> str:
    if value is None:
        return "--"
    return f"{float(value) * 100:.1f}\\%"


def number(value: float | int | None) -> str:
    if value is None:
        return "--"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def rounded(value: float | int | None, digits: int = 4) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


def wilson_interval(successes: int, total: int, z: float = 1.96) -> dict[str, float | int | None]:
    """Return a Wilson score interval for a descriptive binomial proportion."""
    if total <= 0:
        return {"successes": successes, "total": total, "proportion": None, "lower": None, "upper": None}
    phat = successes / total
    denominator = 1 + z**2 / total
    center = (phat + z**2 / (2 * total)) / denominator
    half_width = z * math.sqrt((phat * (1 - phat) + z**2 / (4 * total)) / total) / denominator
    return {
        "successes": successes,
        "total": total,
        "proportion": rounded(phat),
        "lower": rounded(max(0.0, center - half_width)),
        "upper": rounded(min(1.0, center + half_width)),
    }


def label_distribution_rows(summary: dict[str, Any]) -> list[list[Any]]:
    distribution = summary["label_distribution_by_category"]
    rows = []
    for category in EVIDENCE_CATEGORIES:
        counts = distribution.get(category, {})
        rows.append(
            [
                category,
                counts.get("present", 0),
                counts.get("partially_present", 0),
                counts.get("missing", 0),
                counts.get("not_applicable", 0),
            ]
        )
    return rows


def agreement_rows(summary: dict[str, Any]) -> list[list[Any]]:
    rows = []
    for category in EVIDENCE_CATEGORIES:
        rows.append(
            [
                category,
                summary["percent_agreement_by_category"].get(category),
                summary["cohen_kappa_by_category"].get(category),
                summary["majority_label_by_category"].get(category) or "--",
            ]
        )
    return rows


DISPLAY_CATEGORY_LABELS = {
    "intent_evidence": "Intent",
    "requirement_evidence": "Requirement",
    "test_evidence": "Test",
    "risk_analysis": "Risk",
    "scope_evidence": "Scope",
    "trace_evidence": "Trace",
    "dependency_evidence": "Dependency",
    "regression_evidence": "Regression",
    "rationale_evidence": "Rationale",
    "ownership_handoff": "Ownership",
}


def display_category(category: str) -> str:
    return DISPLAY_CATEGORY_LABELS.get(category, category)


def disagreement_category_name(item: Any) -> str:
    if isinstance(item, dict):
        item = item.get("category") or item.get("evidence_category") or str(item)
    return display_category(str(item))


def summarize_majority_pattern(summary: dict[str, Any]) -> str:
    majority = summary["majority_label_by_category"]
    groups: dict[str, list[str]] = {}
    for category in EVIDENCE_CATEGORIES:
        label = majority.get(category) or "--"
        groups.setdefault(label, []).append(display_category(category))
    label_names = {
        "present": "present",
        "partially_present": "partial",
        "missing": "missing",
        "not_applicable": "N/A",
        "--": "unavailable",
    }
    ordered_labels = ["present", "partially_present", "missing", "not_applicable", "--"]
    parts = []
    for label in ordered_labels:
        categories = groups.get(label)
        if categories:
            parts.append(f"{label_names[label]}: {', '.join(categories)}")
    return "; ".join(parts)


def write_label_distribution_table(summary: dict[str, Any], out: str | Path) -> None:
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Annotated evidence-category label distribution.}",
        r"\label{tab:annotation-label-distribution}",
        r"\footnotesize",
        r"\begin{tabular}{@{}lrrrr@{}}",
        r"\toprule",
        r"Category & Present & Partial & Missing & N/A \\",
        r"\midrule",
    ]
    for category, present, partial, missing, na in label_distribution_rows(summary):
        lines.append(f"{latex_escape(category)} & {present} & {partial} & {missing} & {na} \\\\")
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    Path(out).write_text("\n".join(lines), encoding="utf-8")


def write_agreement_table(summary: dict[str, Any], out: str | Path) -> None:
    if summary.get("annotator_count") == 1:
        category_count = len(summary.get("evidence_categories") or EVIDENCE_CATEGORIES)
        repeat_count = summary.get("reliability_repeat_annotations", "--")
        disagreements = summary.get("most_disagreed_categories") or []
        disagreement_text = "No category-level disagreements were observed."
        if disagreements:
            names = ", ".join(disagreement_category_name(item) for item in disagreements)
            disagreement_text = f"Disagreements were observed in: {names}."
        stable_categories = [
            display_category(category)
            for category, value in summary["percent_agreement_by_category"].items()
            if value == 1.0
        ]
        stable_text = ", ".join(stable_categories) if stable_categories else "--"
        lines = [
            r"\begin{table}[t]",
            r"\centering",
            r"\caption{Delayed-repeat self-consistency audit summary.}",
            r"\label{tab:annotation-agreement}",
            r"\footnotesize",
            r"\begin{tabular}{@{}p{0.34\columnwidth}p{0.60\columnwidth}@{}}",
            r"\toprule",
            r"Audit item & Result \\",
            r"\midrule",
            f"Repeat design & {latex_escape(repeat_count)} delayed repeats over {category_count} evidence families. \\\\",
            f"Disagreement check & {latex_escape(disagreement_text)} \\\\",
            f"Stable families & {latex_escape(stable_text)}. \\\\",
            f"Majority pattern & {latex_escape(summarize_majority_pattern(summary))}. \\\\",
            r"Interpretation & Single-annotator self-consistency only; no inter-rater agreement or kappa. \\",
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{table}",
            "",
        ]
        Path(out).write_text("\n".join(lines), encoding="utf-8")
        return

    caption = "Annotation agreement by evidence category."
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        rf"\caption{{{caption}}}",
        r"\label{tab:annotation-agreement}",
        r"\footnotesize",
        r"\begin{tabular}{@{}lrrl@{}}",
        r"\toprule",
        r"Category & Agreement & Kappa & Majority \\",
        r"\midrule",
    ]
    for category, agreement, kappa, majority in agreement_rows(summary):
        lines.append(
            f"{latex_escape(category)} & {percent(agreement)} & {number(kappa)} & {latex_escape(majority)} \\\\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    Path(out).write_text("\n".join(lines), encoding="utf-8")


def compute_pilot_statistical_treatment(summary: dict[str, Any]) -> dict[str, Any]:
    distribution = summary["label_distribution_by_category"]
    total_annotations = int(summary["total_annotations"])
    coverage_intervals: dict[str, dict[str, float | int | None]] = {}
    positive_counts: dict[str, int] = {}
    for category in EVIDENCE_CATEGORIES:
        counts = distribution.get(category, {})
        positive = int(counts.get("present", 0)) + int(counts.get("partially_present", 0))
        positive_counts[category] = positive
        coverage_intervals[category] = wilson_interval(positive, total_annotations)

    total_positive = sum(positive_counts.values())
    positive_share = {
        category: rounded(count / total_positive) if total_positive else None
        for category, count in positive_counts.items()
    }
    evidence_concentration_hhi = None
    if total_positive:
        evidence_concentration_hhi = sum((count / total_positive) ** 2 for count in positive_counts.values())

    repeat_count = int(summary.get("reliability_repeat_annotations") or 0)
    category_count = len(summary.get("evidence_categories") or EVIDENCE_CATEGORIES)
    repeat_category_decisions = repeat_count * category_count
    disagreed = summary.get("most_disagreed_categories") or []
    disagreement_categories = [disagreement_category_name(item) for item in disagreed]
    disagreement_count = len(disagreement_categories)
    self_disagreement_rate = disagreement_count / repeat_category_decisions if repeat_category_decisions else None
    rule_of_three_upper = 3 / repeat_category_decisions if repeat_category_decisions and disagreement_count == 0 else None

    return {
        "interpretation": (
            "Descriptive pilot statistics only. Wilson intervals and rule-of-three bounds express "
            "small-sample instability under a binomial abstraction; they are not population estimates."
        ),
        "total_annotations": total_annotations,
        "coverage_wilson_95_by_category": coverage_intervals,
        "positive_evidence_counts_by_category": positive_counts,
        "positive_evidence_share_by_category": positive_share,
        "positive_evidence_concentration_hhi": rounded(evidence_concentration_hhi),
        "uniform_concentration_baseline": rounded(1 / category_count) if category_count else None,
        "repeat_category_decisions": repeat_category_decisions,
        "repeat_disagreement_categories": disagreement_categories,
        "repeat_disagreement_rate": rounded(self_disagreement_rate),
        "repeat_zero_disagreement_rule_of_three_upper": rounded(rule_of_three_upper),
    }


def write_pilot_statistical_treatment(summary: dict[str, Any], out_dir: str | Path) -> dict[str, Any]:
    output_path = Path(out_dir)
    treatment = compute_pilot_statistical_treatment(summary)
    (output_path / "pilot_statistical_treatment.json").write_text(
        json.dumps(treatment, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    intent = treatment["coverage_wilson_95_by_category"].get("intent_evidence", {})
    risk = treatment["coverage_wilson_95_by_category"].get("risk_analysis", {})
    trace = treatment["coverage_wilson_95_by_category"].get("trace_evidence", {})
    rationale = treatment["coverage_wilson_95_by_category"].get("rationale_evidence", {})
    lines = [
        "# Pilot Statistical Treatment",
        "",
        treatment["interpretation"],
        "",
        "## Descriptive Coverage Intervals",
        "",
        (
            f"- Intent evidence: {intent.get('successes')}/{intent.get('total')} positive labels; "
            f"Wilson 95% interval [{intent.get('lower')}, {intent.get('upper')}]."
        ),
        (
            f"- Risk, trace, and rationale evidence: {risk.get('successes')}/{risk.get('total')}, "
            f"{trace.get('successes')}/{trace.get('total')}, and "
            f"{rationale.get('successes')}/{rationale.get('total')} positive labels; "
            f"upper endpoints are {risk.get('upper')}, {trace.get('upper')}, and {rationale.get('upper')}."
        ),
        "",
        "## Concentration and Repeat Audit",
        "",
        (
            f"- Positive-evidence concentration HHI: {treatment['positive_evidence_concentration_hhi']} "
            f"(uniform baseline: {treatment['uniform_concentration_baseline']})."
        ),
        (
            f"- Delayed-repeat category decisions: {treatment['repeat_category_decisions']}; "
            f"observed disagreement rate: {treatment['repeat_disagreement_rate']}; "
            f"zero-disagreement rule-of-three upper bound: "
            f"{treatment['repeat_zero_disagreement_rule_of_three_upper']}."
        ),
        "",
    ]
    (output_path / "pilot_statistical_treatment.md").write_text("\n".join(lines), encoding="utf-8")
    return treatment


def write_results_summary(summary: dict[str, Any], out: str | Path) -> None:
    distribution = summary["label_distribution_by_category"]
    missing_counts = sorted(
        ((category, counts.get("missing", 0)) for category, counts in distribution.items()),
        key=lambda item: item[1],
        reverse=True,
    )
    top_missing = missing_counts[:5]
    lines = [
        "# Annotation Results Snippet",
        "",
        "## Overview",
        "",
        f"- Total reliability groups/tasks: {summary['total_tasks']}",
        f"- Total annotation records: {summary['total_annotations']}",
        f"- Annotator count: {summary['annotator_count']}",
        f"- Reliability repeat annotations: {summary['reliability_repeat_annotations']}",
        "",
        "## Most Missing Evidence Categories",
        "",
    ]
    for category, count in top_missing:
        lines.append(f"- `{category}`: {count} missing labels")
    lines.extend(
        [
            "",
            "## Paper Integration Notes",
            "",
            "- Use `annotation_label_distribution_table.tex` for the evidence-gap table.",
            "- Use `annotation_agreement_table.tex` for self-consistency or agreement reporting.",
            "- Do not describe this as inter-rater reliability unless `annotator_count` is at least 2.",
            "- Keep patch correctness and mergeability out of the result interpretation.",
            "",
        ]
    )
    Path(out).write_text("\n".join(lines), encoding="utf-8")


def build_paper_results(annotations: str | Path, out_dir: str | Path, allow_incomplete: bool = False) -> dict[str, Any]:
    annotation_path = Path(annotations)
    output_path = Path(out_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    if annotation_path.suffix.lower() == ".csv":
        validation = validate_annotation_csv(annotation_path, require_complete=not allow_incomplete)
        (output_path / "annotation_csv_validation.json").write_text(
            json.dumps(validation, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        if not validation["valid"]:
            raise ValueError(
                "Annotation CSV is not complete enough for paper results. "
                f"See {output_path / 'annotation_csv_validation.json'}"
            )
    stats_dir = output_path / "annotation_stats"
    summary = write_annotation_stats(annotation_path, stats_dir)
    write_label_distribution_table(summary, output_path / "annotation_label_distribution_table.tex")
    write_agreement_table(summary, output_path / "annotation_agreement_table.tex")
    write_pilot_statistical_treatment(summary, output_path)
    write_results_summary(summary, output_path / "annotation_results_summary.md")
    build_adjudication_sheet(
        stats_dir,
        output_path / "adjudication_sheet.csv",
        output_path / "adjudication_sheet.md",
    )
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build paper result snippets from annotations")
    parser.add_argument("--annotations", required=True, help="Completed annotation CSV or Label Studio JSON export")
    parser.add_argument("--out", required=True, help="Output directory for paper-ready result snippets")
    parser.add_argument("--allow-incomplete", action="store_true", help="Allow incomplete CSV for dry-run snippets")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = build_paper_results(args.annotations, args.out, allow_incomplete=args.allow_incomplete)
    print(
        "Paper annotation result snippets written: "
        f"{summary['total_annotations']} annotations across {summary['total_tasks']} tasks -> {args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
