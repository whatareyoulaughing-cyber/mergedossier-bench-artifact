"""Validation helpers for MergeDossier-Bench JSON artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMA_FILENAMES = {
    "dossier": "merge_dossier.schema.json",
    "instance": "pr_instance.schema.json",
    "annotation": "annotation.schema.json",
    "score": "score_report.schema.json",
    "github_pr_raw": "github_pr_raw.schema.json",
}


def package_root() -> Path:
    """Return repository/package root when running from source tree."""
    return Path(__file__).resolve().parents[2]


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def load_schema(kind: str) -> dict[str, Any]:
    if kind not in SCHEMA_FILENAMES:
        raise ValueError(f"Unknown schema kind {kind!r}; expected one of {sorted(SCHEMA_FILENAMES)}")
    schema_path = package_root() / "schemas" / SCHEMA_FILENAMES[kind]
    return load_json(schema_path)


def _basic_validate(data: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    """Small fallback validator used when jsonschema is not installed.

    It checks top-level required fields only. Full validation is performed when
    jsonschema is available.
    """
    errors: list[str] = []
    for field in schema.get("required", []):
        if field not in data:
            errors.append(f"Missing required field: {field}")
    return errors


def validate_data(data: dict[str, Any], kind: str) -> list[str]:
    """Validate data against a named schema. Returns a list of error strings."""
    schema = load_schema(kind)
    try:
        import jsonschema  # type: ignore
    except Exception:
        return _basic_validate(data, schema)

    validator_cls = jsonschema.validators.validator_for(schema)
    validator_cls.check_schema(schema)
    validator = validator_cls(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
    return [f"{list(error.path)}: {error.message}" for error in errors]


def validate_file(path: str | Path, kind: str) -> list[str]:
    return validate_data(load_json(path), kind)
