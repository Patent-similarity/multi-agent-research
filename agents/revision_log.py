"""Create, validate, and summarize revision-log entries."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jsonschema import validate


_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "phase0" / "revision_log_schema.json"


def _load_schema() -> dict[str, Any]:
    with _SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_revision_row(row: dict[str, Any]) -> None:
    """Raise jsonschema.ValidationError if a revision row is invalid."""
    validate(instance=row, schema=_load_schema())


def create_revision_row(
    *,
    run_id: str,
    draft_id: str,
    revision_number: int,
    claim_id: str,
    before_claim: str,
    after_claim: str | None,
    flag_reason: str,
    flag_severity: str,
    critic_decision: str,
    revision_action: str,
    resolved: bool,
    final_status: str,
    timestamp: str | None = None,
) -> dict[str, Any]:
    """Create and validate one revision-log row."""
    row = {
        "run_id": run_id,
        "draft_id": draft_id,
        "revision_number": revision_number,
        "claim_id": claim_id,
        "before_claim": before_claim,
        "after_claim": after_claim,
        "flag_reason": flag_reason,
        "flag_severity": flag_severity,
        "critic_decision": critic_decision,
        "revision_action": revision_action,
        "resolved": resolved,
        "final_status": final_status,
        "timestamp": timestamp
        or datetime.now(timezone.utc).isoformat(),
    }

    validate_revision_row(row)
    return row


def derive_run_outcome(
    rows: list[dict[str, Any]],
    final_claim_ids: list[str],
) -> dict[str, Any]:
    """Derive the run-level outcome from revision-log rows and final claims."""
    claims_total = len(set(final_claim_ids))
    claims_revised = len(
        {
            row["claim_id"]
            for row in rows
            if row["revision_number"] > 0
        }
    )
    flags_remaining = len(
        {
            row["claim_id"]
            for row in rows
            if row["final_status"] == "shipped_with_flag"
        }
    )

    if flags_remaining > 0:
        final_status = "shipped_with_flags"
    elif claims_revised > 0:
        final_status = "revised_and_accepted"
    else:
        final_status = "accepted"

    run_id = rows[0]["run_id"] if rows else ""

    return {
        "run_id": run_id,
        "final_status": final_status,
        "revision_count": max(
            (row["revision_number"] for row in rows),
            default=0,
        ),
        "claims_total": claims_total,
        "claims_revised": claims_revised,
        "flags_remaining": flags_remaining,
    }
