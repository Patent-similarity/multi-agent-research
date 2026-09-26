from agents.pipeline import ResearchPipeline


class FakeLLM:
    def complete(self, system: str, user: str) -> str:
        return "{}"


def test_partial_resolution_is_preserved_when_final_claim_remains_flagged():
    pipeline = ResearchPipeline(FakeLLM())

    drafts = [
        {
            "draft_id": "partial_resolution_test",
            "claims": [
                {
                    "claim_id": "claim_001",
                    "claim": "Claim one.",
                    "supporting_comparison_ids": ["cmp_001"],
                },
                {
                    "claim_id": "claim_002",
                    "claim": "Claim two.",
                    "supporting_comparison_ids": ["cmp_002"],
                },
            ],
            "report": "Claim one. Claim two.",
        },
        {
            "draft_id": "partial_resolution_test",
            "claims": [
                {
                    "claim_id": "claim_001",
                    "claim": "Claim one corrected.",
                    "supporting_comparison_ids": ["cmp_001"],
                },
                {
                    "claim_id": "claim_002",
                    "claim": "Claim two still problematic.",
                    "supporting_comparison_ids": ["cmp_002"],
                },
            ],
            "report": "Claim one corrected. Claim two still problematic.",
        },
        {
            "draft_id": "partial_resolution_test",
            "claims": [
                {
                    "claim_id": "claim_001",
                    "claim": "Claim one corrected.",
                    "supporting_comparison_ids": ["cmp_001"],
                },
                {
                    "claim_id": "claim_002",
                    "claim": "Claim two still problematic.",
                    "supporting_comparison_ids": ["cmp_002"],
                },
            ],
            "report": "Claim one corrected. Claim two still problematic.",
        },
    ]

    evidence = {
        "draft_id": "partial_resolution_test",
        "claim_checks": [],
    }

    critics = [
        {
            "draft_id": "partial_resolution_test",
            "flags": [
                {
                    "claim_id": "claim_001",
                    "reason": "Claim one is unsupported.",
                    "severity": "major",
                    "revision_instruction": "Rewrite claim one.",
                    "allowed_action": "rewrite",
                },
                {
                    "claim_id": "claim_002",
                    "reason": "Claim two is unsupported.",
                    "severity": "major",
                    "revision_instruction": "Rewrite claim two.",
                    "allowed_action": "rewrite",
                },
            ],
            "decision": "revise",
        },
        {
            "draft_id": "partial_resolution_test",
            "flags": [
                {
                    "claim_id": "claim_002",
                    "reason": "Claim two is still unsupported.",
                    "severity": "major",
                    "revision_instruction": "Rewrite claim two.",
                    "allowed_action": "rewrite",
                }
            ],
            "decision": "revise",
        },
        {
            "draft_id": "partial_resolution_test",
            "flags": [
                {
                    "claim_id": "claim_002",
                    "reason": "Claim two remains unsupported.",
                    "severity": "major",
                    "revision_instruction": "Rewrite claim two.",
                    "allowed_action": "rewrite",
                }
            ],
            "decision": "revise",
        },
    ]

    build_calls = 0
    revise_calls = 0
    critic_calls = 0

    def fake_build(comparison_input):
        nonlocal build_calls
        result = drafts[build_calls]
        build_calls += 1
        return result

    def fake_check(draft, comparison_input):
        return evidence

    def fake_evaluate(draft, evidence_result):
        nonlocal critic_calls
        result = critics[critic_calls]
        critic_calls += 1
        return result

    def fake_revise(draft, revision_instructions):
        nonlocal revise_calls
        result = drafts[revise_calls + 1]
        revise_calls += 1
        return result

    pipeline.synthesis.build = fake_build
    pipeline.evidence.check = fake_check
    pipeline.critic.evaluate = fake_evaluate
    pipeline.synthesis.revise = fake_revise

    result = pipeline.run(
        {
            "comparison_rows": [],
        }
    )

    rows = result["revision_log"]

    claim_001_rows = [
        row for row in rows
        if row["claim_id"] == "claim_001"
    ]

    claim_002_rows = [
        row for row in rows
        if row["claim_id"] == "claim_002"
    ]

    assert len(claim_001_rows) == 1
    assert len(claim_002_rows) == 2

    claim_001_row = claim_001_rows[0]

    assert claim_001_row["resolved"] is True
    assert claim_001_row["final_status"] == "revised"

    assert all(
        row["final_status"] == "shipped_with_flag"
        for row in claim_002_rows
    )

    assert result["outcome"]["flags_remaining"] == 1

    print(
        "Partial-resolution regression test passed."
    )


if __name__ == "__main__":
    test_partial_resolution_is_preserved_when_final_claim_remains_flagged()