"""Audit PDF and figure layout quality beyond conference-format checks."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any


PASS = "pass"
WARN = "warn"
FAIL = "fail"


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, errors="replace", check=False)


def _record(checks: list[dict[str, Any]], name: str, status: str, detail: str) -> None:
    checks.append({"name": name, "status": status, "detail": detail})


def _font_rows(pdffonts_output: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in pdffonts_output.splitlines():
        if not line.strip() or line.startswith("name") or line.startswith("-"):
            continue
        if "MiKTeX requires" in line or line.startswith("Syntax Error:"):
            continue
        if "Type 3" in line:
            font_type = "Type 3"
        elif "TrueType" in line:
            font_type = "TrueType"
        elif "Type 1" in line:
            font_type = "Type 1"
        else:
            font_type = "Other"
        rows.append({"raw": line, "type": font_type})
    return rows


def _pdfimage_rows(pdfimages_output: str) -> list[str]:
    return [line for line in pdfimages_output.splitlines() if re.match(r"\s*\d+", line)]


def check_main_pdf_fonts(pdf_path: Path) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    if not pdf_path.exists():
        _record(checks, "main_pdf_exists", FAIL, f"Missing PDF: {pdf_path}")
        return checks
    completed = _run(["pdffonts", str(pdf_path)])
    if completed.returncode != 0 and not completed.stdout:
        _record(checks, "main_pdf_fonts_readable", FAIL, completed.stderr.strip() or "pdffonts failed")
        return checks
    rows = _font_rows(completed.stdout)
    true_type = [row for row in rows if row["type"] == "TrueType"]
    type3 = [row for row in rows if row["type"] == "Type 3"]
    other = [row for row in rows if row["type"] == "Other"]
    detail = f"{len(rows)} font row(s); TrueType={len(true_type)}, Type3={len(type3)}, Other={len(other)}."
    if true_type or type3 or other:
        _record(checks, "main_pdf_type1_fonts", FAIL, detail)
    else:
        _record(checks, "main_pdf_type1_fonts", PASS, detail)
    return checks


def check_pdf_figures(figures_dir: Path) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    figure_paths = sorted(figures_dir.glob("*.pdf"))
    if not figure_paths:
        _record(checks, "pdf_figures_exist", WARN, f"No PDF figures found under {figures_dir}.")
        return checks
    _record(checks, "pdf_figures_exist", PASS, f"{len(figure_paths)} PDF figure(s) found.")

    bad_fonts: list[str] = []
    rasterized: list[str] = []
    for figure in figure_paths:
        fonts = _font_rows(_run(["pdffonts", str(figure)]).stdout)
        if any(row["type"] != "Type 1" for row in fonts):
            bad_fonts.append(str(figure))
        images = _pdfimage_rows(_run(["pdfimages", "-list", str(figure)]).stdout)
        if images:
            rasterized.append(f"{figure} ({len(images)} image row(s))")

    if bad_fonts:
        _record(checks, "pdf_figure_type1_fonts", FAIL, "; ".join(bad_fonts))
    else:
        _record(checks, "pdf_figure_type1_fonts", PASS, "All PDF figures use Type 1/core fonts.")

    if rasterized:
        _record(checks, "pdf_figure_vector_only", WARN, "; ".join(rasterized))
    else:
        _record(checks, "pdf_figure_vector_only", PASS, "No raster image rows detected in PDF figures.")
    return checks


def check_latex_log(log_path: Path) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    if not log_path.exists():
        _record(checks, "latex_log_exists", FAIL, f"Missing LaTeX log: {log_path}")
        return checks
    text = log_path.read_text(encoding="utf-8", errors="replace")
    patterns = {
        "latex_errors": r"(^! |LaTeX Error|Emergency stop|Fatal error)",
        "undefined_references": r"(Reference .* undefined|Citation .* undefined|There were undefined references)",
        "overfull_boxes": r"Overfull",
        "underfull_boxes": r"Underfull",
    }
    for name, pattern in patterns.items():
        count = len(re.findall(pattern, text, flags=re.MULTILINE))
        _record(checks, name, FAIL if count else PASS, f"{count} issue(s).")
    return checks


def check_captions(tex_path: Path, max_words: int) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    if not tex_path.exists():
        _record(checks, "tex_exists", FAIL, f"Missing TeX source: {tex_path}")
        return checks
    text = tex_path.read_text(encoding="utf-8", errors="replace")
    long_captions: list[str] = []
    for match in re.finditer(r"\\caption\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}", text, re.S):
        caption = " ".join(match.group(1).split())
        words = re.findall(r"[A-Za-z0-9\\'-]+", caption)
        if len(words) > max_words:
            line = text[: match.start()].count("\n") + 1
            long_captions.append(f"line {line}: {len(words)} words")
    if long_captions:
        _record(checks, "caption_length", WARN, "; ".join(long_captions))
    else:
        _record(checks, "caption_length", PASS, f"No caption exceeds {max_words} words.")
    return checks


def check_table_style(tex_path: Path) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    if not tex_path.exists():
        _record(checks, "table_style_tex_exists", FAIL, f"Missing TeX source: {tex_path}")
        return checks
    text = tex_path.read_text(encoding="utf-8", errors="replace")
    table_blocks = list(re.finditer(r"\\begin\{table\*?\}.*?\\end\{table\*?\}", text, re.S))
    if not table_blocks:
        _record(checks, "tables_present", WARN, "No table environments found.")
        return checks
    _record(checks, "tables_present", PASS, f"{len(table_blocks)} table environment(s) found.")

    missing_caption: list[str] = []
    missing_label: list[str] = []
    tiny_tables: list[str] = []
    vertical_rule_tables: list[str] = []
    for index, match in enumerate(table_blocks, start=1):
        block = match.group(0)
        line = text[: match.start()].count("\n") + 1
        table_id = f"table {index} line {line}"
        if r"\caption" not in block:
            missing_caption.append(table_id)
        if r"\label" not in block:
            missing_label.append(table_id)
        if r"\scriptsize" in block or r"\tiny" in block:
            tiny_tables.append(table_id)
        for source_line in block.splitlines():
            if r"\begin{tabular" in source_line and "|" in source_line:
                vertical_rule_tables.append(table_id)
                break

    if missing_caption:
        _record(checks, "table_captions", FAIL, "; ".join(missing_caption))
    else:
        _record(checks, "table_captions", PASS, "Every table has a caption.")
    if missing_label:
        _record(checks, "table_labels", FAIL, "; ".join(missing_label))
    else:
        _record(checks, "table_labels", PASS, "Every table has a label.")
    if tiny_tables:
        _record(checks, "table_font_size", WARN, "Tiny table font used: " + "; ".join(tiny_tables))
    else:
        _record(checks, "table_font_size", PASS, r"No \scriptsize or \tiny table fonts detected.")
    if vertical_rule_tables:
        _record(checks, "table_vertical_rules", WARN, "Vertical table rules detected: " + "; ".join(vertical_rule_tables))
    else:
        _record(checks, "table_vertical_rules", PASS, "No vertical table rules detected.")
    return checks


def check_figure_style(tex_path: Path) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    if not tex_path.exists():
        _record(checks, "figure_style_tex_exists", FAIL, f"Missing TeX source: {tex_path}")
        return checks
    text = tex_path.read_text(encoding="utf-8", errors="replace")
    base_dir = tex_path.parent
    figure_blocks = list(re.finditer(r"\\begin\{figure\*?\}.*?\\end\{figure\*?\}", text, re.S))
    if not figure_blocks:
        _record(checks, "figures_present", WARN, "No figure environments found.")
        return checks
    _record(checks, "figures_present", PASS, f"{len(figure_blocks)} figure environment(s) found.")

    missing_caption: list[str] = []
    missing_label: list[str] = []
    missing_graphics: list[str] = []
    raster_graphics: list[str] = []
    missing_files: list[str] = []
    for index, match in enumerate(figure_blocks, start=1):
        block = match.group(0)
        line = text[: match.start()].count("\n") + 1
        figure_id = f"figure {index} line {line}"
        if r"\caption" not in block:
            missing_caption.append(figure_id)
        if r"\label" not in block:
            missing_label.append(figure_id)
        graphics = re.findall(r"\\includegraphics(?:\[[^]]*\])?\{([^}]*)\}", block)
        if not graphics:
            missing_graphics.append(figure_id)
        for graphic in graphics:
            suffix = Path(graphic).suffix.lower()
            if suffix in {".png", ".jpg", ".jpeg"}:
                raster_graphics.append(f"{figure_id}: {graphic}")
            candidate = base_dir / graphic
            if suffix:
                if not candidate.exists():
                    missing_files.append(f"{figure_id}: {graphic}")
            else:
                candidates = [candidate.with_suffix(ext) for ext in (".pdf", ".png", ".jpg", ".jpeg")]
                if not any(path.exists() for path in candidates):
                    missing_files.append(f"{figure_id}: {graphic}")

    if missing_caption:
        _record(checks, "figure_captions", FAIL, "; ".join(missing_caption))
    else:
        _record(checks, "figure_captions", PASS, "Every figure has a caption.")
    if missing_label:
        _record(checks, "figure_labels", FAIL, "; ".join(missing_label))
    else:
        _record(checks, "figure_labels", PASS, "Every figure has a label.")
    if missing_graphics:
        _record(checks, "figure_includegraphics", FAIL, "; ".join(missing_graphics))
    else:
        _record(checks, "figure_includegraphics", PASS, "Every figure includes graphics.")
    if raster_graphics:
        _record(checks, "figure_raster_sources", WARN, "Raster graphics used in main TeX: " + "; ".join(raster_graphics))
    else:
        _record(checks, "figure_raster_sources", PASS, "No PNG/JPG graphics are included directly by main TeX.")
    if missing_files:
        _record(checks, "figure_files_exist", FAIL, "; ".join(missing_files))
    else:
        _record(checks, "figure_files_exist", PASS, "Every included figure file exists.")
    return checks


def _included_graphic_paths(tex_path: Path) -> list[Path]:
    if not tex_path.exists():
        return []
    text = tex_path.read_text(encoding="utf-8", errors="replace")
    base_dir = tex_path.parent
    paths: list[Path] = []
    for graphic in re.findall(r"\\includegraphics(?:\[[^]]*\])?\{([^}]*)\}", text):
        candidate = base_dir / graphic
        if candidate.suffix:
            paths.append(candidate)
        else:
            paths.extend(candidate.with_suffix(ext) for ext in (".pdf", ".png", ".jpg", ".jpeg"))
    return paths


def check_pdf_freshness(tex_path: Path, pdf_path: Path) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    if not pdf_path.exists():
        _record(checks, "pdf_freshness", FAIL, f"Missing PDF: {pdf_path}")
        return checks
    if not tex_path.exists():
        _record(checks, "pdf_freshness", FAIL, f"Missing TeX source: {tex_path}")
        return checks

    pdf_mtime = pdf_path.stat().st_mtime
    stale_sources: list[str] = []
    if tex_path.stat().st_mtime > pdf_mtime:
        stale_sources.append(str(tex_path))
    for graphic in _included_graphic_paths(tex_path):
        if graphic.exists() and graphic.stat().st_mtime > pdf_mtime:
            stale_sources.append(str(graphic))

    if stale_sources:
        _record(checks, "pdf_freshness", FAIL, "PDF is older than: " + "; ".join(stale_sources))
    else:
        _record(checks, "pdf_freshness", PASS, "PDF is not older than main TeX or included figure files.")
    return checks


def check_pdf_info(pdf_path: Path) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    completed = _run(["pdfinfo", str(pdf_path)])
    if completed.returncode != 0:
        _record(checks, "pdfinfo", FAIL, completed.stderr.strip() or "pdfinfo failed")
        return checks
    pages_match = re.search(r"^Pages:\s+(\d+)", completed.stdout, flags=re.MULTILINE)
    page_size_match = re.search(r"^Page size:\s+(.+)", completed.stdout, flags=re.MULTILINE)
    pages = int(pages_match.group(1)) if pages_match else -1
    if 1 <= pages <= 10:
        _record(checks, "page_count", PASS, f"{pages} page(s).")
    else:
        _record(checks, "page_count", FAIL, f"Unexpected page count: {pages}.")
    if page_size_match and "612 x 792" in page_size_match.group(1):
        _record(checks, "page_size", PASS, page_size_match.group(1))
    else:
        _record(checks, "page_size", FAIL, page_size_match.group(1) if page_size_match else "Unknown page size.")
    return checks


def summarize(checks: list[dict[str, Any]]) -> dict[str, Any]:
    fail_count = sum(1 for check in checks if check["status"] == FAIL)
    warn_count = sum(1 for check in checks if check["status"] == WARN)
    pass_count = sum(1 for check in checks if check["status"] == PASS)
    return {
        "status": "fail" if fail_count else "pass",
        "pass_count": pass_count,
        "warn_count": warn_count,
        "fail_count": fail_count,
        "checks": checks,
    }


def write_markdown(result: dict[str, Any], out: Path) -> None:
    lines = [
        "# Layout Quality Check",
        "",
        f"Overall status: **{result['status']}**",
        "",
        "| Check | Status | Detail |",
        "|---|---:|---|",
    ]
    for check in result["checks"]:
        detail = str(check["detail"]).replace("|", "\\|")
        lines.append(f"| {check['name']} | {check['status']} | {detail} |")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check paper PDF and figure layout quality")
    parser.add_argument("--tex", default="paper/main.tex")
    parser.add_argument("--pdf", default="paper/main.pdf")
    parser.add_argument("--log", default="paper/build.log")
    parser.add_argument("--figures-dir", default="paper/figures")
    parser.add_argument("--max-caption-words", type=int, default=18)
    parser.add_argument("--out-json", help="Optional JSON report path")
    parser.add_argument("--out-md", help="Optional Markdown report path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    checks: list[dict[str, Any]] = []
    checks.extend(check_pdf_info(Path(args.pdf)))
    checks.extend(check_pdf_freshness(Path(args.tex), Path(args.pdf)))
    checks.extend(check_main_pdf_fonts(Path(args.pdf)))
    checks.extend(check_pdf_figures(Path(args.figures_dir)))
    checks.extend(check_latex_log(Path(args.log)))
    checks.extend(check_captions(Path(args.tex), args.max_caption_words))
    checks.extend(check_table_style(Path(args.tex)))
    checks.extend(check_figure_style(Path(args.tex)))
    result = summarize(checks)
    if args.out_json:
        out_json = Path(args.out_json)
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.out_md:
        write_markdown(result, Path(args.out_md))
    print(f"Layout quality check: {result['status']} ({result['fail_count']} fail, {result['warn_count']} warn)")
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
