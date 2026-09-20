import json

from agents.evidence_agent import EvidenceAgent


class FakeLLM:
    def complete(self, system, user):
        return json.dumps({
            "draft_id": "disagreement_guard_test",
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
                    "reason": "The cited comparison row supports the claim.",
                }
            ],
        })


comparison_input = {
    "research_question": "Test question",
    "comparison": [
        {
            "comparison_id": "cmp_001",
            "source_claim_id": "source_001",
            "sub_question_id": "approaches",
            "claim": "Transformer models were applied to EEG emotion recognition.",
            "approach": "Transformer",
            "dataset": "DEAP",
            "architecture": "Transformer encoder",
            "metrics": ["accuracy"],
            "reported_performance": [],
            "evidence": [
                {
                    "arxiv_id": "mock-001",
                    "title": "Mock Transformer EEG Study",
                    "source_text": "Transformer model applied to EEG emotion recognition.",
                }
            ],
            "comparison_group": "transformer",
            "disagreement": {
                "present": True,
                "description": "Mock disagreement finding backed by one paper.",
            },
            "confidence": "high",
        }
    ],
}


draft = {
    "research_question": comparison_input["research_question"],
    "draft_id": "disagreement_guard_test",
    "claims": [
        {
            "claim_id": "claim_001",
            "claim": (
                "Published studies exhibit disagreements about which "
                "architecture performs best."
            ),
            "supporting_comparison_ids": ["cmp_001"],
        }
    ],
    "report": (
        "Published studies exhibit disagreements about which "
        "architecture performs best."
    ),
}


agent = EvidenceAgent(FakeLLM())
result = agent.check(draft, comparison_input)

check = result["claim_checks"][0]

assert check["claim_id"] == "claim_001"
assert check["status"] == "unsupported"
assert check["evidence"] == []
assert "disagreement" in check["reason"].lower()

print("Evidence disagreement guard test passed.")
