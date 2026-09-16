from agents.revision_log import create_revision_row, derive_run_outcome


row = create_revision_row(
    run_id="run_001",
    draft_id="draft_001",
    revision_number=1,
    claim_id="claim_001",
    before_claim="Transformer models achieve 99% accuracy.",
    after_claim="Transformer models achieved a reported accuracy of 86%.",
    flag_reason="The 99% value was unsupported.",
    flag_severity="major",
    critic_decision="revise",
    revision_action="rewrite",
    resolved=True,
    final_status="revised",
)

assert row["run_id"] == "run_001"
assert row["draft_id"] == "draft_001"
assert row["revision_number"] == 1
assert row["claim_id"] == "claim_001"
assert row["resolved"] is True
assert row["final_status"] == "revised"


outcome = derive_run_outcome(
    [row],
    ["claim_001"],
)

assert outcome["run_id"] == "run_001"
assert outcome["final_status"] == "revised_and_accepted"
assert outcome["revision_count"] == 1
assert outcome["claims_total"] == 1
assert outcome["claims_revised"] == 1
assert outcome["flags_remaining"] == 0

print("Revision log test passed.")