"""Check manuscript framing, claim boundaries, and high-risk wording."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any, NamedTuple


ROOT = Path(__file__).resolve().parents[1]


class RequiredPattern(NamedTuple):
    name: str
    pattern: str
    description: str


class ForbiddenPattern(NamedTuple):
    name: str
    pattern: str
    description: str
    allow_negated: bool = False


REQUIRED_PATTERNS = [
    RequiredPattern("handoff_gap", r"handoff-evidence gap", "Handoff-evidence gap is the paper-facing result."),
    RequiredPattern(
        "review_evidence_availability",
        r"review-evidence availability",
        "Review-evidence availability remains the measurement substrate.",
    ),
    RequiredPattern("diff_slogan", r"A diff is not a dossier", "Primary slogan is present."),
    RequiredPattern("provenance_slogan", r"A dossier must cite its evidence", "Provenance slogan is present."),
    RequiredPattern("aidev_pop", r"AIDev-pop", "Declared AIDev-pop frame is named."),
    RequiredPattern("single_operator", r"single-operator", "Single-operator audit wording is used."),
    RequiredPattern("legacy_triage", r"legacy triage score", "Legacy score is demoted to artifact triage."),
    RequiredPattern("claims_nonclaims_table", r"tab:claims-nonclaims", "Claims/non-claims table is anchored."),
    RequiredPattern("handoff_gap_table", r"tab:handoff-gap", "Handoff-gap robustness table is anchored."),
    RequiredPattern("tipping_point_table", r"tab:tipping-point", "Tipping-point table is anchored."),
    RequiredPattern(
        "availability_interval_table",
        r"tab:availability-intervals",
        "Availability-interval table is anchored.",
    ),
    RequiredPattern("population_sample_table", r"tab:population-sample", "Population-sample table is anchored."),
]


BOUNDARY_PATTERNS = [
    RequiredPattern("not_correctness", r"not\s+(?:a\s+)?(?:patch\s+)?correctness|not\s+.*?correctness", "No correctness claim."),
    RequiredPattern("not_mergeability", r"not\s+.*?mergeability", "No mergeability claim."),
    RequiredPattern("not_reviewer_utility", r"not\s+.*?reviewer utility|reviewer-utility study", "Reviewer utility is out of scope."),
    RequiredPattern("not_ai_vs_human", r"not\s+.*?AI-vs-human|AI-vs-human\s+comparisons", "No AI-vs-human effect claim."),
    RequiredPattern("not_all_github", r"not\s+all[- ]GitHub|not\s+all\s+GitHub", "No all-GitHub population claim."),
    RequiredPattern(
        "not_inter_rater",
        r"not\s+inter-rater|do(?:es)?\s+not\s+replace\s+inter-rater|no\s+inter-rater",
        "No inter-rater reliability claim.",
    ),
]


FORBIDDEN_PATTERNS = [
    ForbiddenPattern("affirming_prove", r"\bprove[sd]?\b", "Avoid proof language for empirical claims.", True),
    ForbiddenPattern("validated_labels", r"validated\s+labels", "Do not claim validated labels."),
    ForbiddenPattern(
        "establish_inter_rater",
        r"establish(?:es|ed|ing)?\s+inter-rater",
        "Do not claim established inter-rater reliability.",
    ),
    ForbiddenPattern(
        "ai_prs_worse",
        r"AI[- ]authored\s+PRs\s+(?:are|were)\s+worse",
        "Do not claim AI-authored PRs are worse than human PRs.",
    ),
    ForbiddenPattern(
        "all_github_population",
        r"all\s+GitHub\s+pull\s+requests",
        "Do not generalize to all GitHub pull requests.",
        True,
    ),
    ForbiddenPattern(
        "reviewer_utility_improves",
        r"reviewer\s+utility\s+(?:improves|improved|improvement|benefit|benefits)",
        "Do not claim reviewer utility improvement.",
    ),
    ForbiddenPattern(
        "mergeability_prediction",
        r"mergeability\s+prediction",
        "Do not frame the artifact as mergeability prediction.",
    ),
]


STYLE_WATCH_TERMS = [
    "comprehensive",
    "novel",
    "robust",
    "seamless",
    "transformative",
    "unlock",
    "leverage",
]


def _strip_latex_comments(text: str) -> str:
    stripped_lines: list[str] = []
    for line in text.splitlines():
        out: list[str] = []
        escaped = False
        for char in line:
            if char == "%" and not escaped:
                break
            out.append(char)
            escaped = char == "\\" and not escaped
            if char != "\\":
                escaped = False
        stripped_lines.append("".join(out))
    return "\n".join(stripped_lines)


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _is_negated(text: str, start: int) -> bool:
    window = text[max(0, start - 60) : start].lower()
    return bool(re.search(r"\b(?:not|no|never|without|do\s+not|does\s+not|did\s+not)\b", window))


def _find_required(text: str, patterns: list[RequiredPattern]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for item in patterns:
        if not re.search(item.pattern, text, flags=re.IGNORECASE | re.DOTALL):
            findings.append(
                {
                    "name": item.name,
                    "severity": "fail",
                    "message": item.description,
                    "pattern": item.pattern,
                }
            )
    return findings


def _find_forbidden(text: str, patterns: list[ForbiddenPattern]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for item in patterns:
        for match in re.finditer(item.pattern, text, flags=re.IGNORECASE):
            if item.allow_negated and _is_negated(text, match.start()):
                continue
            context_start = max(0, match.start() - 90)
            context_end = min(len(text), match.end() + 90)
            findings.append(
                {
                    "name": item.name,
                    "severity": "fail",
                    "line": _line_number(text, match.start()),
                    "match": match.group(0),
                    "message": item.description,
                    "context": " ".join(text[context_start:context_end].split()),
                }
            )
    return findings


def _style_watch_counts(text: str) -> dict[str, int]:
    return {
        term: len(re.findall(rf"\b{re.escape(term)}\w*\b", text, flags=re.IGNORECASE))
        for term in STYLE_WATCH_TERMS
    }


def check_manuscript_claim_hygiene(tex_path: Path, out_dir: Path | None = None) -> dict[str, Any]:
    raw_text = tex_path.read_text(encoding="utf-8")
    text = _strip_latex_comments(raw_text)
    required_findings = _find_required(text, REQUIRED_PATTERNS)
    boundary_findings = _find_required(text, BOUNDARY_PATTERNS)
    forbidden_findings = _find_forbidden(text, FORBIDDEN_PATTERNS)
    findings = required_findings + boundary_findings + forbidden_findings
    result = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "tex_path": str(tex_path),
        "status": "fail" if findings else "pass",
        "finding_count": len(findings),
        "findings": findings,
        "style_watch_counts": _style_watch_counts(text),
        "required_checks": [item.name for item in REQUIRED_PATTERNS],
        "boundary_checks": [item.name for item in BOUNDARY_PATTERNS],
    }
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "manuscript_claim_hygiene.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        write_markdown(result, out_dir / "manuscript_claim_hygiene.md")
    return result


def write_markdown(result: dict[str, Any], out: Path) -> None:
    lines = [
        "# Manuscript Claim Hygiene Check",
        "",
        f"Overall status: **{result['status']}**",
        "",
        f"Findings: `{result['finding_count']}`",
        "",
    ]
    if result["findings"]:
        lines.extend(["## Findings", "", "| Check | Severity | Line | Message |", "|---|---:|---:|---|"])
        for finding in result["findings"]:
            line = finding.get("line", "")
            message = str(finding.get("message", "")).replace("|", "\\|")
            lines.append(f"| {finding['name']} | {finding['severity']} | {line} | {message} |")
    else:
        lines.extend(
            [
                "No missing framing anchors, missing non-claim boundaries, or high-risk overclaim phrases were found.",
                "",
            ]
        )
    lines.extend(["## Style Watch Counts", "", "| Term | Count |", "|---|---:|"])
    for term, count in sorted(result["style_watch_counts"].items()):
        lines.append(f"| {term} | {count} |")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check manuscript claim boundaries and high-risk wording")
    parser.add_argument("--tex", default="paper/main.tex", help="LaTeX manuscript path")
    parser.add_argument("--out", default="outputs/manuscript_claim_hygiene_20260617", help="Output directory")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = check_manuscript_claim_hygiene(ROOT / args.tex, ROOT / args.out)
    print(f"Manuscript claim hygiene: {result['status']} -> {args.out}")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
