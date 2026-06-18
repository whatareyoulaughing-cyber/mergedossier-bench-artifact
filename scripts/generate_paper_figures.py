"""Generate paper figures from current pilot result artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


ROOT = Path(__file__).resolve().parents[1]
FIGURE_DIR = ROOT / "paper" / "figures"

SHORT_LABELS = {
    "intent": "Intent",
    "requirement_traceability": "Requirement",
    "test_rationale": "Test",
    "regression_safety": "Regression",
    "risk_analysis": "Risk",
    "scope_justification": "Scope",
    "change_summary": "Summary",
    "agent_trace": "Agent trace",
    "limitations": "Limitations",
    "reviewer_actionability": "Review action",
    "ownership_handoff": "Ownership",
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


def apply_paper_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
            "font.size": 8,
            "axes.labelsize": 8,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "legend.fontsize": 7,
            "pdf.use14corefonts": True,
            "ps.useafm": True,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_pipeline_overview_figure() -> None:
    fig, ax = plt.subplots(figsize=(7.1, 1.55))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    steps = [
        ("Public PR\nartifacts", "diff, commits,\nchecks, comments"),
        ("MergeDossier\nschema", "11 raw evidence\nfields"),
        ("Validation\nand scoring", "schema check,\nEvidence Score"),
        ("Corpus\nreports", "JSONL scores,\nsummary, CSV"),
        ("Annotation\nand release", "Label Studio,\nrepeats, card"),
    ]
    x_positions = [0.03, 0.235, 0.44, 0.645, 0.85]
    width = 0.135
    height = 0.48
    colors = ["#f4f1de", "#e9f0f7", "#eef4ea", "#f8efe5", "#f1edf6"]
    border = "#333333"

    for index, ((title, subtitle), x, color) in enumerate(zip(steps, x_positions, colors)):
        box = FancyBboxPatch(
            (x, 0.34),
            width,
            height,
            boxstyle="round,pad=0.012,rounding_size=0.018",
            linewidth=0.6,
            edgecolor=border,
            facecolor=color,
        )
        ax.add_patch(box)
        ax.text(x + width / 2, 0.66, title, ha="center", va="center", fontsize=8.2, fontweight="bold")
        ax.text(x + width / 2, 0.46, subtitle, ha="center", va="center", fontsize=7.0, color="#333333")
        if index < len(steps) - 1:
            start = (x + width + 0.01, 0.58)
            end = (x_positions[index + 1] - 0.01, 0.58)
            arrow = FancyArrowPatch(
                start,
                end,
                arrowstyle="-|>",
                mutation_scale=8,
                linewidth=0.75,
                color="#444444",
            )
            ax.add_patch(arrow)

    ax.text(
        0.5,
        0.16,
        "Construct boundary: review-evidence availability, not patch correctness, mergeability, or authorship-group effect.",
        ha="center",
        va="center",
        fontsize=7.2,
        color="#222222",
    )
    fig.tight_layout(pad=0.05)
    for suffix in ("pdf", "png"):
        fig.savefig(FIGURE_DIR / f"pipeline_overview.{suffix}", bbox_inches="tight", dpi=300)
    plt.close(fig)


def write_coverage_figure() -> None:
    summary = load_json(ROOT / "outputs" / "real_pilot_mixed_source_summary_20260613" / "summary.json")
    coverage = summary["evidence_category_coverage"]
    ordered = sorted(coverage.items(), key=lambda item: item[1]["coverage_rate"])
    labels = [SHORT_LABELS[key] for key, _ in ordered]
    rates = [value["coverage_rate"] * 100 for _, value in ordered]

    fig, ax = plt.subplots(figsize=(3.45, 2.35))
    colors = ["#6f6f6f" if rate == 0 else "#2a6f97" for rate in rates]
    ax.barh(labels, rates, color=colors, edgecolor="#222222", linewidth=0.35)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Dossiers with category evidence (%)")
    ax.grid(axis="x", color="#dddddd", linewidth=0.45)
    ax.set_axisbelow(True)
    for index, rate in enumerate(rates):
        if rate > 0:
            ax.text(rate + 1.2, index, f"{rate:.0f}", va="center", ha="left", fontsize=6.8)
        else:
            ax.text(1.2, index, "0", va="center", ha="left", fontsize=6.8, color="#333333")
    fig.tight_layout(pad=0.15)
    for suffix in ("pdf", "png"):
        fig.savefig(FIGURE_DIR / f"evidence_coverage_pilot.{suffix}", bbox_inches="tight", dpi=300)
    plt.close(fig)


def write_annotation_distribution_figure() -> None:
    summary = load_json(
        ROOT
        / "outputs"
        / "real_pilot_mixed_source_annotation_paper_results_20260613"
        / "annotation_stats"
        / "agreement_summary.json"
    )
    distribution = summary["label_distribution_by_category"]
    order = [
        "intent_evidence",
        "scope_evidence",
        "regression_evidence",
        "ownership_handoff",
        "test_evidence",
        "requirement_evidence",
        "risk_analysis",
        "trace_evidence",
        "rationale_evidence",
        "dependency_evidence",
    ]
    labels = [SHORT_LABELS[key] for key in order]
    columns = [
        ("present", "Present"),
        ("partially_present", "Partial"),
        ("missing", "Missing"),
        ("not_applicable", "N/A"),
    ]
    values = [[distribution[key][column_key] for column_key, _ in columns] for key in order]
    max_count = summary["total_annotations"]
    status_colors = ["#1b6f5c", "#6b95b8", "#d9d9d9", "#ffffff"]

    fig, ax = plt.subplots(figsize=(3.45, 2.65))
    ax.set_xlim(-0.5, len(columns) - 0.5)
    ax.set_ylim(-0.5, len(labels) - 0.5)
    ax.invert_yaxis()
    ax.set_xticks(range(len(columns)))
    ax.set_xticklabels([label for _, label in columns])
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels)
    ax.tick_params(axis="both", length=0)

    for y_index, row in enumerate(values):
        for x_index, count in enumerate(row):
            size = 30 + 260 * (count / max_count)
            facecolor = status_colors[x_index]
            edgecolor = "#555555" if count else "#cfcfcf"
            ax.scatter(
                x_index,
                y_index,
                s=size,
                color=facecolor,
                edgecolor=edgecolor,
                linewidth=0.5,
                zorder=3,
            )
            text_color = "#ffffff" if x_index == 0 and count >= 10 else "#222222"
            ax.text(x_index, y_index, str(count), ha="center", va="center", fontsize=6.8, color=text_color)

    for x_index in range(len(columns)):
        ax.axvline(x_index + 0.5, color="#eeeeee", linewidth=0.5, zorder=0)
    for y_index in range(len(labels)):
        ax.axhline(y_index + 0.5, color="#eeeeee", linewidth=0.5, zorder=0)

    ax.set_xlabel("Annotation records")
    for spine in ax.spines.values():
        spine.set_visible(False)
    fig.tight_layout(pad=0.15)
    for suffix in ("pdf", "png"):
        fig.savefig(FIGURE_DIR / f"annotation_label_heatmap.{suffix}", bbox_inches="tight", dpi=300)
    plt.close(fig)


def main() -> int:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    apply_paper_style()
    write_pipeline_overview_figure()
    write_coverage_figure()
    write_annotation_distribution_figure()
    print("Figures written to paper/figures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
