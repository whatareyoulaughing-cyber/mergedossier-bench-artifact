import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_layout_quality.py"
SPEC = importlib.util.spec_from_file_location("check_layout_quality", SCRIPT)
assert SPEC and SPEC.loader
layout_quality = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(layout_quality)

check_captions = layout_quality.check_captions
check_figure_style = layout_quality.check_figure_style
check_pdf_freshness = layout_quality.check_pdf_freshness
check_table_style = layout_quality.check_table_style
summarize = layout_quality.summarize


def test_caption_length_warns_only_for_long_captions(tmp_path):
    tex = tmp_path / "main.tex"
    tex.write_text(
        r"""
\caption{Short caption.}
\caption{This caption has a deliberately excessive number of words so the layout quality audit can flag it.}
""",
        encoding="utf-8",
    )

    checks = check_captions(tex, max_words=10)

    assert checks[0]["status"] == "warn"
    assert "line 3" in checks[0]["detail"]


def test_summarize_fails_on_any_failed_check():
    result = summarize(
        [
            {"name": "a", "status": "pass", "detail": "ok"},
            {"name": "b", "status": "fail", "detail": "bad"},
        ]
    )

    assert result["status"] == "fail"
    assert result["fail_count"] == 1


def test_table_style_flags_missing_labels_and_tiny_tables(tmp_path):
    tex = tmp_path / "main.tex"
    tex.write_text(
        r"""
\begin{table}
\caption{No label and tiny font.}
\scriptsize
\begin{tabular}{|l|r|}
A & B \\
\end{tabular}
\end{table}
""",
        encoding="utf-8",
    )

    checks = {check["name"]: check for check in check_table_style(tex)}

    assert checks["tables_present"]["status"] == "pass"
    assert checks["table_captions"]["status"] == "pass"
    assert checks["table_labels"]["status"] == "fail"
    assert checks["table_font_size"]["status"] == "warn"
    assert checks["table_vertical_rules"]["status"] == "warn"


def test_figure_style_accepts_labeled_pdf_figures(tmp_path):
    figures = tmp_path / "figures"
    figures.mkdir()
    (figures / "pipeline.pdf").write_bytes(b"%PDF-1.4\n")
    tex = tmp_path / "main.tex"
    tex.write_text(
        r"""
\begin{figure}
\includegraphics[width=\columnwidth]{figures/pipeline.pdf}
\caption{Pipeline.}
\label{fig:pipeline}
\end{figure}
""",
        encoding="utf-8",
    )

    checks = {check["name"]: check for check in check_figure_style(tex)}

    assert checks["figures_present"]["status"] == "pass"
    assert checks["figure_captions"]["status"] == "pass"
    assert checks["figure_labels"]["status"] == "pass"
    assert checks["figure_includegraphics"]["status"] == "pass"
    assert checks["figure_raster_sources"]["status"] == "pass"
    assert checks["figure_files_exist"]["status"] == "pass"


def test_figure_style_flags_raster_and_missing_files(tmp_path):
    tex = tmp_path / "main.tex"
    tex.write_text(
        r"""
\begin{figure}
\includegraphics{figures/missing.png}
\caption{Missing raster figure.}
\end{figure}
""",
        encoding="utf-8",
    )

    checks = {check["name"]: check for check in check_figure_style(tex)}

    assert checks["figure_labels"]["status"] == "fail"
    assert checks["figure_raster_sources"]["status"] == "warn"
    assert checks["figure_files_exist"]["status"] == "fail"


def test_pdf_freshness_passes_when_pdf_is_newer(tmp_path):
    tex = tmp_path / "main.tex"
    pdf = tmp_path / "main.pdf"
    figure = tmp_path / "fig.pdf"
    tex.write_text(r"\includegraphics{fig.pdf}", encoding="utf-8")
    figure.write_bytes(b"%PDF-1.4\n")
    pdf.write_bytes(b"%PDF-1.4\n")
    newest = max(tex.stat().st_mtime, figure.stat().st_mtime) + 10
    import os

    os.utime(pdf, (newest, newest))

    checks = check_pdf_freshness(tex, pdf)

    assert checks[0]["status"] == "pass"


def test_pdf_freshness_fails_when_tex_is_newer(tmp_path):
    tex = tmp_path / "main.tex"
    pdf = tmp_path / "main.pdf"
    tex.write_text("old", encoding="utf-8")
    pdf.write_bytes(b"%PDF-1.4\n")
    import os

    old = pdf.stat().st_mtime - 10
    os.utime(pdf, (old, old))
    tex.write_text("new", encoding="utf-8")

    checks = check_pdf_freshness(tex, pdf)

    assert checks[0]["status"] == "fail"
    assert "main.tex" in checks[0]["detail"]
