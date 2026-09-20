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
                        },
                        {
                            "comparison_id": "cmp_031",
                            "arxiv_id": "mock-031",
                        },
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
                    "title": "Mock Disagreement Study A",
                    "source_text": "Mock evidence describing one methodological position.",
                },
                {
                    "arxiv_id": "mock-032",
                    "title": "Mock Disagreement Study B",
                    "source_text": "Mock evidence describing a conflicting methodological position.",
                },
            ],
            "comparison_group": None,
            "disagreement": {
                "present": True,
                "description": "Study A reports one methodological choice.",
            },
            "confidence": "high",
        },
        {
            "comparison_id": "cmp_031",
            "source_claim_id": "disagreements-002",
            "sub_question_id": "disagreements",
            "claim": "Study B reports a different methodological choice.",
            "approach": "end-to-end learning",
            "dataset": None,
            "architecture": None,
            "metrics": ["accuracy"],
            "reported_performance": [],
            "evidence": [
                {
                    "arxiv_id": "mock-031",
                    "title": "Mock Disagreement Study B",
                    "source_text": "Mock evidence describing a different methodological position.",
                },
                {
                    "arxiv_id": "mock-033",
                    "title": "Mock Disagreement Study C",
                    "source_text": "Mock evidence describing another conflicting methodological position.",
                },
            ],
            "comparison_group": None,
            "disagreement": {
                "present": True,
                "description": "Study B reports a different methodological choice.",
            },
            "confidence": "high",
        },
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
            "supporting_comparison_ids": ["cmp_030", "cmp_031"],
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
    },
    {
        "comparison_id": "cmp_031",
        "arxiv_id": "mock-031",
    },
]

print("Positive disagreement evidence test passed.")
