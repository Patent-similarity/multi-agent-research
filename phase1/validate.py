"""
Shared JSON-Schema validation helper for every agent handoff in the pipeline.

Every agent's output MUST be validated against its locked schema in
phase0/schemas/ before being passed to the next agent. This is not optional —
Phase 0 locked these contracts specifically so integration in Phase 2 doesn't
turn into silent schema drift.
"""
import json
import os
from pathlib import Path

from jsonschema import Draft7Validator

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "phase0" / "schemas"


def load_schema(schema_filename: str) -> dict:
    """Load a locked schema from phase0/schemas/ by filename."""
    path = SCHEMA_DIR / schema_filename
    if not path.exists():
        raise FileNotFoundError(
            f"Schema not found: {path}. Did phase0/schemas/ get copied in?"
        )
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_payload(payload: dict, schema_filename: str) -> list[str]:
    """
    Validate `payload` against the named schema.

    Returns a list of human-readable error strings (empty list = valid).
    Does NOT raise — callers decide whether a validation failure is fatal
    (it should almost always be fatal for a locked contract boundary).
    """
    schema = load_schema(schema_filename)
    validator = Draft7Validator(schema)
    errors = []
    for err in sorted(validator.iter_errors(payload), key=lambda e: list(e.path)):
        loc = ".".join(str(p) for p in err.path) or "<root>"
        errors.append(f"{loc}: {err.message}")
    return errors


def validate_or_raise(payload: dict, schema_filename: str) -> None:
    errors = validate_payload(payload, schema_filename)
    if errors:
        formatted = "\n  - ".join(errors)
        raise ValueError(
            f"Payload failed validation against {schema_filename}:\n  - {formatted}"
        )


def check_no_empty_strings_where_null_expected(payload: dict, nullable_fields: list[str]) -> list[str]:
    """
    Extra guardrail beyond jsonschema: schema allows [\"string\", \"null\"] for
    nullable fields, but jsonschema alone won't catch an LLM emitting \"\" instead
    of null (both are valid strings). This is explicitly called out in Phase 0
    as load-bearing, so we check it separately.

    `nullable_fields` are dotted paths, e.g. \"disagreement.description\".
    Only checks top-level and one level of nesting — extend if you add deeper
    nullable fields.
    """
    problems = []

    def _get(obj, path_parts):
        cur = obj
        for part in path_parts:
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return None, False
        return cur, True

    def _check_one(record, field_path):
        parts = field_path.split(".")
        value, found = _get(record, parts)
        if found and value == "":
            problems.append(f"{field_path} is empty string, expected null when missing")

    # payload here is expected to be a single record OR a container with a list
    if isinstance(payload, list):
        for i, record in enumerate(payload):
            for field_path in nullable_fields:
                before = len(problems)
                _check_one(record, field_path)
                if len(problems) > before:
                    problems[-1] = f"[{i}] {problems[-1]}"
    elif isinstance(payload, dict):
        for field_path in nullable_fields:
            _check_one(payload, field_path)

    return problems