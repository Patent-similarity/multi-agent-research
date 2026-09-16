import json

from agents.pipeline import ResearchPipeline


class FakeLLM:
    def __init__(self):
        self.call_count = 0

    def complete(self, system, user):
        self.call_count += 1

        if self.call_count == 1:
            return json.dumps({
                "research_question": "Test question",
                "draft_id": "ship_flags_test",
                "claims": [
                    {
                        "claim_id": "claim_001",
                        "claim": "Transformer models achieve 99% accuracy.",
                        "supporting_comparison_ids": ["cmp_001"],
                    }
                ],
                "report": "Transformer models achieve 99% accuracy.",
            })

        if self.call_count == 2:
            return json.dumps({
                "draft_id": "ship_flags_test",
                "claim_checks": [
                    {
                        "claim_id": "claim_001",
                        "status": "unsupported",
                        "evidence": [],
                        "reason": "Unsupported.",
                    }
                ],
            })

        if self.call_count == 3:
            return json.dumps({
                "draft_id": "ship_flags_test",
                "flags": [
                    {
                        "claim_id": "claim_001",
                        "reason": "Unsupported.",
                        "severity": "major",
                        "revision_instruction": "Rewrite using supported evidence.",
                        "allowed_action": "rewrite",
                    }
                ],
            })

        if self.call_count == 4:
            return json.dumps({
                "research_question": "Test question",
                "draft_id": "ship_flags_test",
                "claims": [
                    {
                        "claim_id": "claim_001",
                        "claim": "Transformer models achieve 98% accuracy.",
                        "supporting_comparison_ids": ["cmp_001"],
                    }
                ],
                "report": "Transformer models achieve 98% accuracy.",
            })

        if self.call_count == 5:
            return json.dumps({
                "draft_id": "ship_flags_test",
                "claim_checks": [
                    {
                        "claim_id": "claim_001",
                        "status": "unsupported",
                        "evidence": [],
                        "reason": "Still unsupported.",
                    }
                ],
            })

        if self.call_count == 6:
            return json.dumps({
                "draft_id": "ship_flags_test",
                "flags": [
                    {
                        "claim_id": "claim_001",
                        "reason": "Still unsupported.",
                        "severity": "major",
                        "revision_instruction": "Rewrite using supported evidence.",
                        "allowed_action": "rewrite",
                    }
                ],
            })

        if self.call_count == 7:
            return json.dumps({
                "research_question": "Test question",
                "draft_id": "ship_flags_test",
                "claims": [
                    {
                        "claim_id": "claim_001",
                        "claim": "Transformer models achieve 97% accuracy.",
                        "supporting_comparison_ids": ["cmp_001"],
                    }
                ],
                "report": "Transformer models achieve 97% accuracy.",
            })

        if self.call_count == 8:
            return json.dumps({
                "draft_id": "ship_flags_test",
                "claim_checks": [
                    {
                        "claim_id": "claim_001",
                        "status": "unsupported",
                        "evidence": [],
                        "reason": "Still unsupported after revision 2.",
                    }
                ],
            })

        if self.call_count == 9:
            return json.dumps({
                "draft_id": "ship_flags_test",
                "flags": [
                    {
                        "claim_id": "claim_001",
                        "reason": "Still unsupported after revision 2.",
                        "severity": "major",
                        "revision_instruction": "No further revision allowed.",
                        "allowed_action": "rewrite",
                    }
                ],
            })

        raise AssertionError(
            f"Unexpected LLM call number: {self.call_count}"
        )


comparison_input = {
    "research_question": "Test question",
    "comparison": [
        {
            "comparison_id": "cmp_001",
            "source_claim_id": "source_001",
            "sub_question_id": "approaches",
            "claim": "Transformer models were studied.",
            "approach": "Transformer",
            "dataset": "DEAP",
            "architecture": "Transformer encoder",
            "metrics": ["accuracy"],
            "reported_performance": [],
            "evidence": [
                {
                    "arxiv_id": "mock-001",
                    "title": "Mock Study",
                    "source_text": "Transformer models were studied.",
                }
            ],
            "comparison_group": "DEAP",
            "disagreement": {
                "present": False,
                "description": None,
            },
            "confidence": "high",
        }
    ],
}


result = ResearchPipeline(FakeLLM()).run(comparison_input)

assert result["revision_number"] == 2
assert len(result["revision_log"]) == 2

for row in result["revision_log"]:
    assert row["resolved"] is False
    assert row["final_status"] == "shipped_with_flag"

assert result["outcome"]["final_status"] == "shipped_with_flags"
assert result["outcome"]["flags_remaining"] == 1

print("Ship-with-flags test passed.")
