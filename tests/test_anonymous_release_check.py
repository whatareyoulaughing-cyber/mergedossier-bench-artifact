import importlib.util
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

BUILD_SPEC = importlib.util.spec_from_file_location(
    "build_anonymous_release_zip", ROOT / "scripts" / "build_anonymous_release_zip.py"
)
assert BUILD_SPEC and BUILD_SPEC.loader
BUILD_MODULE = importlib.util.module_from_spec(BUILD_SPEC)
BUILD_SPEC.loader.exec_module(BUILD_MODULE)
redact_local_paths = BUILD_MODULE.redact_local_paths

CHECK_SPEC = importlib.util.spec_from_file_location(
    "check_anonymous_release", ROOT / "scripts" / "check_anonymous_release.py"
)
assert CHECK_SPEC and CHECK_SPEC.loader
CHECK_MODULE = importlib.util.module_from_spec(CHECK_SPEC)
CHECK_SPEC.loader.exec_module(CHECK_MODULE)
scan_anonymous_release = CHECK_MODULE.scan_anonymous_release
_pdf_metadata_hits = CHECK_MODULE._pdf_metadata_hits


def test_redact_local_paths_removes_workspace_and_python_paths():
    text = (
        r"C:\Users\alice\OneDrive\docs\paper\MergeDossier-Bench-starter\outputs\x.json "
        r"C:\\Users\\alice\\AppData\\Local\\Programs\\Python\\Python312\\python.exe"
    )
    redacted = redact_local_paths(text)
    assert "C:\\Users" not in redacted
    assert "alice" not in redacted
    assert "<REPO_ROOT>/" in redacted


def test_anonymous_release_check_detects_local_path(tmp_path: Path):
    release = tmp_path / "release.zip"
    with zipfile.ZipFile(release, "w") as archive:
        archive.writestr("pkg/report.json", r'{"path":"C:\\Users\\alice\\x"}')

    result = scan_anonymous_release(release, tmp_path / "out")

    assert result["status"] == "fail"
    assert result["finding_count"] == 1


def test_pdf_metadata_scan_allows_minimal_pdf_without_local_path():
    minimal_pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Count 0 >> endobj\n"
        b"trailer << /Root 1 0 R >>\n%%EOF\n"
    )

    assert _pdf_metadata_hits(minimal_pdf, "main.pdf") == []
