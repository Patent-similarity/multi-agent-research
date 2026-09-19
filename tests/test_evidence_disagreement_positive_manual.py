import json

from agents.evidence_agent import EvidenceAgent


class FakeLLM:
    def complete(self, system, user):
        return json.dumps({
            "draft_id": "disagreement_positive_test",
            "claim_checks": [
                {
                    "claim_id": "claim_001",
                    "status": "supported",
                    "evidence": [
                        {
                            "comparison_id": "cmp_030",
                            "arxiv_id": "mock-030",
                        }
                    ],
                    "reason": "The disagreement evidence is supported.",
                }
            ],
        })


comparison_input = {
    "research_question": "Test question",
    "comparison": [
        {
            "comparison_id": "cmp_030",
            "source_claim_id": "disagreements-001",
            "sub_question_id": "disagreements",
            "claim": "Study A reports a methodological difference from other approaches.",
            "approach": "transfer learning",
            "dataset": None,
            "architecture": None,
            "metrics": ["accuracy"],
            "reported_performance": [],
            "evidence": [
                {
                    "arxiv_id": "mock-030",
                    "title": "Mock Disagreement Study",
                    "source_text": "Mock evidence describing the methodological disagreement.",
                }
            ],
            "comparison_group": None,
            "disagreement": {
                "present": True,
                "description": "A genuine methodological disagreement is documented.",
            },
            "confidence": "high",
        }
    ],
}


draft = {
    "research_question": comparison_input["research_question"],
    "draft_id": "disagreement_positive_test",
    "claims": [
        {
            "claim_id": "claim_001",
            "claim": (
                "Published studies exhibit disagreements about "
                "methodological choices."
            ),
            "supporting_comparison_ids": ["cmp_030"],
        }
    ],
    "report": (
        "Published studies exhibit disagreements about "
        "methodological choices."
    ),
}


agent = EvidenceAgent(FakeLLM())
result = agent.check(draft, comparison_input)

check = result["claim_checks"][0]

assert check["claim_id"] == "claim_001"
assert check["status"] == "supported"
assert check["evidence"] == [
    {
        "comparison_id": "cmp_030",
        "arxiv_id": "mock-030",
    }
]

print("Positive disagreement evidence test passed.")
