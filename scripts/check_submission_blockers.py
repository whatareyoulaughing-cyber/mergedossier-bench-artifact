"""Build an evidence-backed submission blocker dashboard.

The dashboard answers: what still prevents a high-confidence ICSE submission?
It treats local green checks as evidence, while keeping external audit and DOI
publication as unresolved until the corresponding artifacts prove completion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

PASS = "pass"
READY = "ready"
OPEN = "open"
FAIL = "fail"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _display(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _record(name: str, status: str, evidence: str, action: str, severity: str) -> dict[str, str]:
    return {
        "name": name,
        "status": status,
        "severity": severity,
        "evidence": evidence,
        "action": action,
    }


def check_external_audit(path: Path) -> dict[str, str]:
    data = _read_json(path)
    status = str(data.get("status", "missing"))
    if status == "complete":
        return _record(
            "External audit slice",
            PASS,
            f"{_display(path)} reports complete.",
            "Add the secondary-audit result to paper/release notes if desired.",
            "P0",
        )
    blank_count = len(data.get("blank_label_cells", [])) if isinstance(data.get("blank_label_cells"), list) else "unknown"
    return _record(
        "External audit slice",
        OPEN,
        f"{_display(path)} status={status}; blank_label_cells={blank_count}.",
        "Have an independent operator complete the 50-task sheet, then rerun analyze_external_audit_slice.py.",
        "P0",
    )


def check_deposit_packet(path: Path) -> dict[str, str]:
    data = _read_json(path)
    if not data:
        return _record(
            "Archival deposit packet",
            OPEN,
            f"Missing {_display(path)}.",
            "Run scripts/build_zenodo_deposit_packet.py.",
            "P0",
        )
    doi_minted = bool(data.get("doi_minted"))
    public_url = bool(data.get("public_repository_url_recorded"))
    if doi_minted and public_url:
        return _record(
            "Archival DOI and public URL",
            PASS,
            f"{_display(path)} records DOI/public URL completion.",
            "Update README/CITATION/paper artifact note with final links.",
            "P0",
        )
    return _record(
        "Archival DOI and public URL",
        READY,
        f"{_display(path)} status={data.get('status')}; doi_minted={doi_minted}; public_repository_url_recorded={public_url}.",
        "Manually publish the deposit/public repository, then run scripts/update_public_release_metadata.py with the real DOI and URLs.",
        "P0",
    )


def check_release_checksum(release_zip: Path, checksum_file: Path) -> dict[str, str]:
    actual = _sha256(release_zip)
    checksum_text = _read_text(checksum_file)
    expected = checksum_text.split()[0] if checksum_text.split() else None
    if actual and expected and actual == expected:
        return _record(
            "Release archive checksum",
            PASS,
            f"{_display(release_zip)} matches {_display(checksum_file)}.",
            "Use this checksum when depositing the archive.",
            "P1",
        )
    return _record(
        "Release archive checksum",
        FAIL,
        f"release_sha256={actual}; deposit_sha256={expected}.",
        "Rebuild the release zip, then rerun scripts/build_zenodo_deposit_packet.py.",
        "P1",
    )


def check_readiness(path: Path) -> dict[str, str]:
    data = _read_json(path)
    status = str(data.get("status", "missing"))
    gates = data.get("records", [])
    failed = [record.get("gate", "?") for record in gates if record.get("status") != PASS]
    if status == PASS and not failed:
        return _record(
            "Local paper readiness",
            PASS,
            f"{_display(path)} status=pass; gates={len(gates)}.",
            "Keep rerunning before final submission.",
            "P1",
        )
    return _record(
        "Local paper readiness",
        FAIL,
        f"{_display(path)} status={status}; failed_gates={failed}.",
        "Fix failing local gate(s) before submission.",
        "P1",
    )


def check_placeholders(paths: list[Path]) -> dict[str, str]:
    findings: list[str] = []
    pattern = re.compile(r"TO_BE_FILLED|To be added after anonymous review|PLACEHOLDER", re.I)
    for path in paths:
        text = _read_text(path)
        if pattern.search(text):
            findings.append(_display(path))
    if not findings:
        return _record(
            "Public metadata placeholders",
            PASS,
            "No public-release placeholders found in checked metadata files.",
            "No action needed.",
            "P1",
        )
    return _record(
        "Public metadata placeholders",
        OPEN,
        "Placeholders remain in: " + ", ".join(findings),
        "After DOI/public repository creation, run scripts/update_public_release_metadata.py.",
        "P1",
    )


def check_raw_frame_policy(path: Path) -> dict[str, str]:
    data = _read_json(path)
    if data.get("status") == "findings_present":
        return _record(
            "Raw-frame release policy",
            READY,
            f"{_display(path)} reports {data.get('affected_rows')} affected raw-frame rows; sanitized release remains default.",
            "Keep raw frame excluded unless a separate scrubbed/restricted archive is prepared.",
            "P2",
        )
    if data.get("status") == "no_pattern_findings":
        return _record(
            "Raw-frame release policy",
            READY,
            f"{_display(path)} reports no pattern findings; sanitized release remains default unless policy changes.",
            "Manual privacy review is still needed before raw-text release.",
            "P2",
        )
    return _record(
        "Raw-frame release policy",
        OPEN,
        f"Missing or unrecognized raw-frame risk report: {_display(path)}.",
        "Run scripts/scan_raw_frame_release_risks.py.",
        "P2",
    )


def check_anonymous_release(path: Path) -> dict[str, str]:
    data = _read_json(path)
    status = str(data.get("status", "missing"))
    if status == PASS:
        return _record(
            "Anonymous release leak scan",
            PASS,
            f"{_display(path)} status=pass; findings={data.get('finding_count', 0)}.",
            "Keep rerunning after rebuilding the release zip.",
            "P1",
        )
    return _record(
        "Anonymous release leak scan",
        FAIL,
        f"{_display(path)} status={status}; findings={data.get('finding_count', 'unknown')}.",
        "Run scripts/check_anonymous_release.py and remove local path/user leaks before submission.",
        "P1",
    )


def check_claim_hygiene(path: Path) -> dict[str, str]:
    data = _read_json(path)
    status = str(data.get("status", "missing"))
    if status == PASS:
        return _record(
            "Manuscript claim hygiene",
            PASS,
            f"{_display(path)} status=pass; findings={data.get('finding_count', 0)}.",
            "Keep rerunning after paper edits.",
            "P1",
        )
    return _record(
        "Manuscript claim hygiene",
        FAIL,
        f"{_display(path)} status={status}; findings={data.get('finding_count', 'unknown')}.",
        "Run scripts/check_manuscript_claim_hygiene.py and fix missing boundary/overclaim findings.",
        "P1",
    )


def check_submission_action_packet(path: Path) -> dict[str, str]:
    data = _read_json(path)
    if data.get("status") == "action_required":
        actions = data.get("p0_actions", [])
        names = ", ".join(str(action.get("name", "?")) for action in actions)
        return _record(
            "Submission action packet",
            PASS,
            f"{_display(path)} records actionable P0 steps: {names}.",
            "Use outputs/submission_action_packet_20260617/NEXT_ACTIONS_ZH.md to execute external actions.",
            "P1",
        )
    return _record(
        "Submission action packet",
        FAIL,
        f"Missing or unrecognized action packet: {_display(path)}.",
        "Run scripts/build_submission_action_packet.py.",
        "P1",
    )


def check_icse_submission_packet(path: Path) -> dict[str, str]:
    data = _read_json(path)
    status = str(data.get("status", "missing"))
    if status in {"ready_except_external_actions", "submission_ready_local"}:
        return _record(
            "ICSE submission packet",
            PASS,
            f"{_display(path)} status={status}; copied_files={len(data.get('copied_files', []))}.",
            "Use outputs/icse_submission_packet_20260617/PORTAL_FIELDS.md and ICSE_SUBMISSION_CHECKLIST_ZH.md at submission time.",
            "P1",
        )
    return _record(
        "ICSE submission packet",
        FAIL,
        f"Missing or unrecognized ICSE submission packet: {_display(path)}.",
        "Run scripts/build_icse_submission_packet.py.",
        "P1",
    )


def check_icse_submission_packet_verifier(path: Path) -> dict[str, str]:
    data = _read_json(path)
    status = str(data.get("status", "missing"))
    if status == PASS:
        return _record(
            "ICSE submission packet self-check",
            PASS,
            f"{_display(path)} status=pass; failures={data.get('failure_count', 0)}; warnings={data.get('warning_count', 0)}.",
            "Keep rerunning after rebuilding the ICSE submission packet.",
            "P1",
        )
    return _record(
        "ICSE submission packet self-check",
        FAIL,
        f"{_display(path)} status={status}; failures={data.get('failure_count', 'unknown')}.",
        "Run scripts/check_icse_submission_packet.py and fix packet mismatches before upload.",
        "P1",
    )


def check_double_anonymous_submission(path: Path) -> dict[str, str]:
    data = _read_json(path)
    status = str(data.get("status", "missing"))
    if status == PASS:
        return _record(
            "Double-anonymous submission check",
            PASS,
            f"{_display(path)} status=pass; failures={data.get('fail_count', 0)}; warnings={data.get('warn_count', 0)}.",
            "Keep rerunning after paper/PDF edits.",
            "P1",
        )
    return _record(
        "Double-anonymous submission check",
        FAIL,
        f"{_display(path)} status={status}; failures={data.get('fail_count', 'unknown')}.",
        "Run scripts/check_double_anonymous_submission.py and remove PDF/source identity leaks.",
        "P1",
    )


def check_ai_assistance_disclosure(path: Path) -> dict[str, str]:
    data = _read_json(path)
    status = str(data.get("status", "missing"))
    if status == PASS:
        return _record(
            "AI assistance disclosure",
            PASS,
            f"{_display(path)} status=pass; failures={data.get('failure_count', 0)}; warnings={data.get('warning_count', 0)}.",
            "Use outputs/ai_assistance_disclosure_packet_20260617/PORTAL_AI_DISCLOSURE.md if the submission portal asks for AI usage.",
            "P1",
        )
    return _record(
        "AI assistance disclosure",
        FAIL,
        f"{_display(path)} status={status}; failures={data.get('failure_count', 'unknown')}.",
        "Run scripts/build_ai_assistance_disclosure_packet.py and scripts/check_ai_assistance_disclosure.py.",
        "P1",
    )


def check_release_zip_smoke(path: Path) -> dict[str, str]:
    data = _read_json(path)
    status = str(data.get("status", "missing"))
    if status == PASS:
        commands = data.get("commands", [])
        return _record(
            "Release zip functional smoke",
            PASS,
            f"{_display(path)} status=pass; commands={len(commands)}.",
            "Keep rerunning after rebuilding the anonymous release zip.",
            "P1",
        )
    return _record(
        "Release zip functional smoke",
        FAIL,
        f"{_display(path)} status={status}; error={data.get('error', 'missing report')}.",
        "Run scripts/check_release_zip_smoke.py against the generated anonymous-review zip.",
        "P1",
    )


def check_public_release_preflight(path: Path) -> dict[str, str]:
    data = _read_json(path)
    status = str(data.get("status", "missing"))
    if status == "ready_for_manual_publication":
        return _record(
            "Public release preflight",
            PASS,
            f"{_display(path)} status={status}; warnings={data.get('warning_count', 0)}.",
            "Use the preflight report while manually publishing the DOI/public repository.",
            "P1",
        )
    return _record(
        "Public release preflight",
        FAIL,
        f"{_display(path)} status={status}; failures={data.get('failure_count', 'unknown')}.",
        "Run scripts/check_public_release_preflight.py and fix failed release-preflight checks.",
        "P1",
    )


def check_external_auditor_handoff(path: Path) -> dict[str, str]:
    data = _read_json(path)
    status = str(data.get("status", "missing"))
    if status == PASS:
        return _record(
            "External auditor handoff independence",
            PASS,
            f"{_display(path)} status=pass; failures={data.get('failure_count', 0)}.",
            "Send the checked handoff zip to the external auditor.",
            "P1",
        )
    return _record(
        "External auditor handoff independence",
        FAIL,
        f"{_display(path)} status={status}; failures={data.get('failure_count', 'unknown')}.",
        "Run scripts/check_external_auditor_handoff.py and fix leaked/pre-filled handoff contents.",
        "P1",
    )


def build_submission_blocker_dashboard(root: Path, out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    checks = [
        check_external_audit(root / "outputs/external_audit_analysis_20260617/external_audit_summary.json"),
        check_deposit_packet(root / "outputs/zenodo_deposit_packet_20260617/deposit_packet_summary.json"),
        check_release_checksum(
            root / "outputs/release/MergeDossier-Bench-anonymous-review.zip",
            root / "outputs/zenodo_deposit_packet_20260617/SHA256SUMS.txt",
        ),
        check_readiness(root / "outputs/paper_readiness_check_20260617_handoff_gap/paper_readiness_check.json"),
        check_claim_hygiene(
            root / "outputs/manuscript_claim_hygiene_20260617/manuscript_claim_hygiene.json"
        ),
        check_submission_action_packet(
            root / "outputs/submission_action_packet_20260617/action_status.json"
        ),
        check_external_auditor_handoff(
            root / "outputs/external_audit_handoff_20260617/external_auditor_handoff_check.json"
        ),
        check_icse_submission_packet(
            root / "outputs/icse_submission_packet_20260617/submission_packet_status.json"
        ),
        check_icse_submission_packet_verifier(
            root / "outputs/icse_submission_packet_check_20260617/icse_submission_packet_check.json"
        ),
        check_double_anonymous_submission(
            root / "outputs/double_anonymous_submission_check_20260617/double_anonymous_submission_check.json"
        ),
        check_ai_assistance_disclosure(
            root / "outputs/ai_assistance_disclosure_check_20260617/ai_assistance_disclosure_check.json"
        ),
        check_release_zip_smoke(
            root / "outputs/release_zip_smoke_20260617/release_zip_smoke.json"
        ),
        check_public_release_preflight(
            root / "outputs/public_release_preflight_20260617/public_release_preflight.json"
        ),
        check_anonymous_release(root / "outputs/anonymous_release_check_20260617/anonymous_release_check.json"),
        check_placeholders(
            [
                root / "outputs/public_release_metadata_20260617/zenodo_metadata_template.json",
                root / "CITATION.cff",
                root / "README.md",
            ]
        ),
        check_raw_frame_policy(root / "outputs/raw_frame_release_risk_20260617/raw_frame_release_risk_summary.json"),
    ]
    p0_open = [check for check in checks if check["severity"] == "P0" and check["status"] != PASS]
    fail = [check for check in checks if check["status"] == FAIL]
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "blocked_on_external_actions" if p0_open else ("fail" if fail else "submission_ready_local"),
        "p0_open_count": len(p0_open),
        "fail_count": len(fail),
        "checks": checks,
        "next_actions": [check["action"] for check in p0_open] or [check["action"] for check in fail],
    }
    (out_dir / "submission_blocker_dashboard.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    _write_markdown(result, out_dir / "submission_blocker_dashboard.md")
    return result


def _write_markdown(result: dict[str, Any], out: Path) -> None:
    lines = [
        "# Submission Blocker Dashboard",
        "",
        f"Overall status: **{result['status']}**",
        "",
        "| Blocker | Severity | Status | Evidence | Action |",
        "|---|---:|---:|---|---|",
    ]
    for check in result["checks"]:
        evidence = str(check["evidence"]).replace("|", "\\|")
        action = str(check["action"]).replace("|", "\\|")
        lines.append(
            f"| {check['name']} | {check['severity']} | {check['status']} | {evidence} | {action} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "P0 open items are external actions required before claiming very high submission confidence. Local pass/ready items reduce reviewer risk but do not prove external audit completion, DOI publication, or public repository availability.",
            "",
        ]
    )
    out.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build submission blocker dashboard")
    parser.add_argument("--out", default="outputs/submission_blocker_dashboard_20260617")
    args = parser.parse_args(argv)
    result = build_submission_blocker_dashboard(ROOT, ROOT / args.out)
    print(
        "Submission blocker dashboard: "
        f"{result['status']} (P0 open={result['p0_open_count']}, fail={result['fail_count']})"
    )
    return 0 if result["status"] != "fail" else 1


if __name__ == "__main__":
    raise SystemExit(main())
