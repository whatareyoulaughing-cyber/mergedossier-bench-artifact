import importlib.util
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check_icse_format.py"
SPEC = importlib.util.spec_from_file_location("check_icse_format", SCRIPT_PATH)
assert SPEC is not None
check_icse_format = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(check_icse_format)

check_latex_log_text = check_icse_format.check_latex_log_text
check_latex_log = check_icse_format.check_latex_log
check_pdf_info_text = check_icse_format.check_pdf_info_text
check_tex_source = check_icse_format.check_tex_source
summarize = check_icse_format.summarize


def _status(checks, name):
    return next(check for check in checks if check["name"] == name)["status"]


def test_icse_tex_source_accepts_required_ieeetran_class(tmp_path: Path):
    tex = tmp_path / "main.tex"
    tex.write_text(
        "\n".join(
            [
                r"\documentclass[10pt,conference]{IEEEtran}",
                r"\usepackage{balance}",
                r"\begin{document}",
                r"\balance",
                r"\bibliography{references}",
                r"\end{document}",
            ]
        ),
        encoding="utf-8",
    )

    checks = check_tex_source(tex)

    assert _status(checks, "ieeetran_documentclass") == "pass"
    assert _status(checks, "forbidden_ieee_options") == "pass"
    assert _status(checks, "spacing_tampering") == "pass"
    assert _status(checks, "last_page_balance") == "pass"


def test_icse_tex_source_rejects_compsoc_and_spacing_tampering(tmp_path: Path):
    tex = tmp_path / "main.tex"
    tex.write_text(
        "\n".join(
            [
                r"\documentclass[10pt,conference,compsoc]{IEEEtran}",
                r"\addtolength{\textheight}{0.1in}",
                r"\begin{document}",
                r"\end{document}",
            ]
        ),
        encoding="utf-8",
    )

    checks = check_tex_source(tex)

    assert _status(checks, "ieeetran_documentclass") == "fail"
    assert _status(checks, "forbidden_ieee_options") == "fail"
    assert _status(checks, "spacing_tampering") == "fail"


def test_pdfinfo_checks_page_count_and_letter_size():
    good = "Pages:           5\nPage size:       612 x 792 pts (letter)\n"
    checks = check_pdf_info_text(good)
    assert _status(checks, "pdf_pages") == "pass"
    assert _status(checks, "pdf_page_size") == "pass"

    too_long = "Pages:           13\nPage size:       595 x 842 pts (A4)\n"
    checks = check_pdf_info_text(too_long)
    assert _status(checks, "pdf_pages") == "fail"
    assert _status(checks, "pdf_page_size") == "fail"


def test_latex_log_checks_failures_and_underfull_warnings():
    clean = "Output written on main.pdf\nUnderfull \\hbox (badness 1000) in paragraph\n"
    checks = check_latex_log_text(clean)
    assert _status(checks, "latex_errors") == "pass"
    assert _status(checks, "undefined_references") == "pass"
    assert _status(checks, "overfull_boxes") == "pass"
    assert _status(checks, "underfull_boxes") == "warn"
    assert summarize(checks)["status"] == "pass"

    broken = "! LaTeX Error\nReference foo undefined\nOverfull \\hbox (1.0pt too wide)\n"
    checks = check_latex_log_text(broken)
    assert _status(checks, "latex_errors") == "fail"
    assert _status(checks, "undefined_references") == "fail"
    assert _status(checks, "overfull_boxes") == "fail"
    assert summarize(checks)["status"] == "fail"


def test_latex_log_reader_handles_utf16_build_logs(tmp_path: Path):
    log_path = tmp_path / "build.log"
    log_path.write_text("Underfull \\hbox (badness 1000) in paragraph\n", encoding="utf-16")

    checks = check_latex_log(log_path)

    assert _status(checks, "latex_log_exists") == "pass"
    assert _status(checks, "underfull_boxes") == "warn"
