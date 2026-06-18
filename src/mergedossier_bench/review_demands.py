"""Exploratory review-comment evidence-demand extraction."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


DEMAND_PATTERNS: dict[str, tuple[str, ...]] = {
    "test_demand": (
        r"\btest(s|ing)?\b",
        r"\bcoverage\b",
        r"\bpytest\b",
        r"\bunit test\b",
        r"\bintegration test\b",
    ),
    "rationale_demand": (
        r"\bwhy\b",
        r"\brationale\b",
        r"\bexplain\b",
        r"\breason\b",
        r"\bmotivation\b",
    ),
    "risk_demand": (
        r"\brisk\b",
        r"\brollback\b",
        r"\bbreak(s|ing)?\b",
        r"\bfailure\b",
        r"\bedge case\b",
        r"\bsecurity\b",
    ),
    "regression_demand": (
        r"\bregression\b",
        r"\bbackward compatible\b",
        r"\bcompatib(le|ility)\b",
        r"\bexisting behavior\b",
    ),
    "ownership_demand": (
        r"\bowner(ship)?\b",
        r"\bfollow-?up\b",
        r"\bmaintain(er|ership)?\b",
        r"\bmonitor(ing)?\b",
        r"\bhandoff\b",
        r"\brollout\b",
    ),
    "scope_demand": (
        r"\bscope\b",
        r"\bout of scope\b",
        r"\btoo broad\b",
        r"\blimit(ed)?\b",
        r"\bsmaller\b",
    ),
    "requirement_demand": (
        r"\brequirement(s)?\b",
        r"\bissue\b",
        r"\bspec\b",
        r"\bacceptance\b",
        r"\bexpected behavior\b",
    ),
}


def _iter_raw_inputs(path: str | Path) -> Iterable[tuple[str, dict[str, Any] | None, str | None]]:
    raw_path = Path(path)
    if raw_path.is_dir():
        for item in sorted(raw_path.glob("*.json")):
            try:
                yield str(item), json.loads(item.read_text(encoding="utf-8")), None
            except (OSError, json.JSONDecodeError) as exc:
                yield str(item), None, str(exc)
        return

    if raw_path.suffix.lower() == ".jsonl":
        try:
            with raw_path.open("r", encoding="utf-8") as f:
                for line_number, line in enumerate(f, start=1):
                    text = line.strip()
                    if not text:
                        continue
                    try:
                        yield f"{raw_path}:line {line_number}", json.loads(text), None
                    except json.JSONDecodeError as exc:
                        yield f"{raw_path}:line {line_number}", None, str(exc)
        except OSError as exc:
            yield str(raw_path), None, str(exc)
        return

    try:
        yield str(raw_path), json.loads(raw_path.read_text(encoding="utf-8")), None
    except (OSError, json.JSONDecodeError) as exc:
        yield str(raw_path), None, str(exc)


def _comment_sources(raw: dict[str, Any]) -> Iterable[tuple[str, int, str]]:
    for source_kind in ("reviews", "review_comments", "issue_comments"):
        values = raw.get(source_kind, [])
        if not isinstance(values, list):
            continue
        for index, item in enumerate(values):
            if isinstance(item, dict):
                body = item.get("body", "")
            else:
                body = ""
            if isinstance(body, str) and body.strip():
                yield source_kind, index, body.strip()


def _matching_categories(text: str) -> list[tuple[str, list[str]]]:
    matches: list[tuple[str, list[str]]] = []
    for category, patterns in DEMAND_PATTERNS.items():
        hit_patterns = [pattern for pattern in patterns if re.search(pattern, text, flags=re.IGNORECASE)]
        if hit_patterns:
            matches.append((category, hit_patterns))
    return matches


def _excerpt(text: str, limit: int = 220) -> str:
    normalized = " ".join(text.split())
    return normalized if len(normalized) <= limit else normalized[: limit - 3].rstrip() + "..."


def extract_review_demands(raw: str | Path, out_dir: str | Path) -> dict[str, Any]:
    """Write exploratory review-demand signals from raw PR artifacts."""
    output_path = Path(out_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    signals: list[dict[str, Any]] = []
    load_errors: list[dict[str, str]] = []
    total_records = 0
    records_with_demands: set[str] = set()

    for source, item, error in _iter_raw_inputs(raw):
        if error is not None or item is None:
            load_errors.append({"source": source, "error": error or "missing raw PR"})
            continue
        total_records += 1
        instance_id = str(item.get("instance_id") or source)
        repo = str(item.get("repo") or "")
        pr_number = item.get("pr_number", "")
        pr_url = str(item.get("pr_url") or "")
        for source_kind, comment_index, body in _comment_sources(item):
            for category, patterns in _matching_categories(body):
                records_with_demands.add(instance_id)
                signals.append(
                    {
                        "instance_id": instance_id,
                        "repo": repo,
                        "pr_number": pr_number,
                        "pr_url": pr_url,
                        "source": source,
                        "source_kind": source_kind,
                        "comment_index": comment_index,
                        "category": category,
                        "matched_terms": ";".join(patterns),
                        "excerpt": _excerpt(body),
                        "exploratory": True,
                    }
                )

    category_counts = Counter(signal["category"] for signal in signals)
    source_counts = Counter(signal["source_kind"] for signal in signals)
    summary = {
        "total_raw_records": total_records,
        "records_with_review_demand_signals": len(records_with_demands),
        "total_review_demand_signals": len(signals),
        "category_counts": dict(sorted(category_counts.items())),
        "source_kind_counts": dict(sorted(source_counts.items())),
        "load_errors": load_errors,
        "interpretation": (
            "Exploratory deterministic review-demand signals only; these outputs do not measure reviewer utility, "
            "causal effects, correctness, or mergeability."
        ),
    }

    with (output_path / "review_demand_signals.jsonl").open("w", encoding="utf-8") as f:
        for signal in signals:
            f.write(json.dumps(signal, ensure_ascii=False) + "\n")

    (output_path / "review_demand_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    with (output_path / "paper_table_review_demands.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["category", "signals", "interpretation"])
        writer.writeheader()
        for category in sorted(DEMAND_PATTERNS):
            writer.writerow(
                {
                    "category": category,
                    "signals": category_counts.get(category, 0),
                    "interpretation": "exploratory demand signal; not reviewer utility evidence",
                }
            )

    return summary
