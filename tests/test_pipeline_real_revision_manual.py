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
                "research_question": (
                    "How do transformer-based models compare with "
                    "convolutional/recurrent deep-learning approaches "
                    "for EEG-based emotion recognition?"
                ),
                "draft_id": "pipeline_real_revision_test",
                "claims": [
                    {
                        "claim_id": "claim_real_001",
                        "claim": (
                            "AMDET achieved 99.99% accuracy on the "
                            "SEED-IV dataset."
                        ),
                        "supporting_comparison_ids": ["cmp-012"],
                    }
                ],
                "report": (
                    "AMDET achieved 99.99% accuracy on the "
                    "SEED-IV dataset."
                ),
            })

        # Evidence.check() - first pass
        if self.call_count == 2:
            return json.dumps({
                "draft_id": "pipeline_real_revision_test",
                "claim_checks": [
                    {
                        "claim_id": "claim_real_001",
                        "status": "unsupported",
                        "evidence": [
                            {
                                "comparison_id": "cmp-012",
                                "arxiv_id": "2212.12134",
                            }
                        ],
                        "reason": (
                            "The cited comparison row reports 87.32% "
                            "accuracy for SEED-IV, not 99.99%."
                        ),
                    }
                ],
            })

        # Critic.evaluate() - first pass
        if self.call_count == 3:
            return json.dumps({
                "draft_id": "pipeline_real_revision_test",
                "flags": [
                    {
                        "claim_id": "claim_real_001",
                        "reason": (
                            "The claim reports 99.99% accuracy, but the "
                            "frozen comparison data reports 87.32% for "
                            "SEED-IV."
                        ),
                        "severity": "major",
                        "revision_instruction": (
                            "Replace 99.99% with the reported SEED-IV "
                            "accuracy of 87.32%."
                        ),
                        "allowed_action": "rewrite",
                    }
                ],
            })

        # Synthesis.revise()
        if self.call_count == 4:
            return json.dumps({
                "research_question": (
                    "How do transformer-based models compare with "
                    "convolutional/recurrent deep-learning approaches "
                    "for EEG-based emotion recognition?"
                ),
                "draft_id": "pipeline_real_revision_test",
                "claims": [
                    {
                        "claim_id": "claim_real_001",
                        "claim": (
                            "AMDET achieved a reported accuracy of "
                            "87.32% on the SEED-IV dataset."
                        ),
                        "supporting_comparison_ids": ["cmp-012"],
                    }
                ],
                "report": (
                    "AMDET achieved a reported accuracy of "
                    "87.32% on the SEED-IV dataset."
                ),
            })

        # Evidence.check() - second pass
        if self.call_count == 5:
            return json.dumps({
                "draft_id": "pipeline_real_revision_test",
                "claim_checks": [
                    {
                        "claim_id": "claim_real_001",
                        "status": "supported",
                        "evidence": [
                            {
                                "comparison_id": "cmp-012",
                                "arxiv_id": "2212.12134",
                            }
                        ],
                        "reason": (
                            "The frozen comparison data reports 87.32% "
                            "accuracy for AMDET on SEED-IV."
                        ),
                    }
                ],
            })

        # Critic.evaluate() - second pass
        if self.call_count == 6:
            return json.dumps({
                "draft_id": "pipeline_real_revision_test",
                "flags": [],
            })

        raise AssertionError(
            f"Unexpected LLM call number: {self.call_count}"
        )

comparison_path = (
    "phase1/results/baseline/comparison_output.json"
)

with open(comparison_path, "r", encoding="utf-8") as f:
    comparison_input = json.load(f)


fake_llm = FakeLLM()
pipeline = ResearchPipeline(fake_llm)


fake_llm = FakeLLM()
pipeline = ResearchPipeline(fake_llm)

result = pipeline.run(comparison_input)

print(json.dumps(result, indent=2))

assert result["draft"]["draft_id"] == "pipeline_real_revision_test"

final_claim = result["draft"]["claims"][0]["claim"]

assert "87.32%" in final_claim
assert "99.99%" not in final_claim

assert result["critic"]["decision"] == "accept"
assert fake_llm.call_count == 6

assert len(result["revision_log"]) == 1

revision_row = result["revision_log"][0]

assert revision_row["claim_id"] == "claim_real_001"
assert revision_row["revision_number"] == 1
assert "99.99%" in revision_row["before_claim"]
assert "87.32%" in revision_row["after_claim"]
assert revision_row["revision_action"] == "rewrite"
assert revision_row["resolved"] is True
assert revision_row["final_status"] == "revised"

assert result["outcome"]["final_status"] == "revised_and_accepted"
assert result["outcome"]["claims_revised"] == 1
assert result["outcome"]["flags_remaining"] == 0

print("Real frozen-baseline revision test passed.")