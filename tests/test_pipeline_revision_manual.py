import json

from agents.pipeline import ResearchPipeline


class FakeLLM:
    def __init__(self):
        self.call_count = 0

    def complete(self, system, user):
        self.call_count += 1

        # Synthesis.build()
        if self.call_count == 1:
            return json.dumps({
                "research_question": "Test question",
                "draft_id": "pipeline_revision_test",
                "claims": [
                    {
                        "claim_id": "claim_001",
                        "claim": "Transformer models achieve 99% accuracy.",
                        "supporting_comparison_ids": ["cmp_001"],
                    }
                ],
                "report": "Transformer models achieve 99% accuracy.",
            })

        # Evidence.check() - first pass
        if self.call_count == 2:
            return json.dumps({
                "draft_id": "pipeline_revision_test",
                "claim_checks": [
                    {
                        "claim_id": "claim_001",
                        "status": "unsupported",
                        "evidence": [],
                        "reason": "The 99% value is unsupported.",
                    }
                ],
            })

        # Critic.evaluate() - first pass
        if self.call_count == 3:
            return json.dumps({
                "draft_id": "pipeline_revision_test",
                "flags": [
                    {
                        "claim_id": "claim_001",
                        "reason": "The 99% value is unsupported.",
                        "severity": "major",
                        "revision_instruction": (
                            "Replace the unsupported 99% value "
                            "with the reported 86% value."
                        ),
                        "allowed_action": "rewrite",
                    }
                ],
            })

        # Synthesis.revise()
        if self.call_count == 4:
            return json.dumps({
                "research_question": "Test question",
                "draft_id": "pipeline_revision_test",
                "claims": [
                    {
                        "claim_id": "claim_001",
                        "claim": (
                            "Transformer models achieved a reported "
                            "accuracy of 86%."
                        ),
                        "supporting_comparison_ids": ["cmp_001"],
                    }
                ],
                "report": (
                    "Transformer models achieved a reported "
                    "accuracy of 86%."
                ),
            })

        # Evidence.check() - second pass
        if self.call_count == 5:
            return json.dumps({
                "draft_id": "pipeline_revision_test",
                "claim_checks": [
                    {
                        "claim_id": "claim_001",
                        "status": "supported",
                        "evidence": [
                            {
                                "comparison_id": "cmp_001",
                                "arxiv_id": "mock-001",
                            }
                        ],
                        "reason": "The 86% value is supported.",
                    }
                ],
            })

        # Critic.evaluate() - second pass
        if self.call_count == 6:
            return json.dumps({
                "draft_id": "pipeline_revision_test",
                "flags": [],
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
            "claim": "Transformer models achieved 86% accuracy.",
            "approach": "Transformer",
            "dataset": "DEAP",
            "architecture": "Transformer encoder",
            "metrics": ["accuracy"],
            "reported_performance": [
                {
                    "metric": "accuracy",
                    "value": "86",
                    "unit": "%",
                }
            ],
            "evidence": [
                {
                    "arxiv_id": "mock-001",
                    "title": "Mock Transformer EEG Study",
                    "source_text": "86% accuracy was reported.",
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


fake_llm = FakeLLM()
pipeline = ResearchPipeline(fake_llm)

result = pipeline.run(comparison_input)

print(json.dumps(result, indent=2))

assert result["draft"]["draft_id"] == "pipeline_revision_test"
assert "86%" in result["draft"]["claims"][0]["claim"]
assert "99%" not in result["draft"]["claims"][0]["claim"]
assert result["critic"]["decision"] == "accept"
assert fake_llm.call_count == 6

assert len(result["revision_log"]) == 1

revision_row = result["revision_log"][0]

assert revision_row["claim_id"] == "claim_001"
assert revision_row["revision_number"] == 1
assert revision_row["before_claim"] == "Transformer models achieve 99% accuracy."
assert "86%" in revision_row["after_claim"]
assert revision_row["revision_action"] == "rewrite"
assert revision_row["resolved"] is True
assert revision_row["final_status"] == "revised"

assert result["outcome"]["final_status"] == "revised_and_accepted"
assert result["outcome"]["claims_revised"] == 1
assert result["outcome"]["flags_remaining"] == 0

print("Pipeline revision test passed.")