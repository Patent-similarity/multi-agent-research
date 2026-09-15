import json

from agents.evidence_agent import EvidenceAgent
from agents.llm_client import GeminiClient


with open("phase0/mocks/comparison_happy.json", "r", encoding="utf-8") as f:
    comparison_input = json.load(f)


draft = {
    "research_question": comparison_input["research_question"],
    "draft_id": "coverage_test",
    "claims": [
        {
            "claim_id": "claim_001",
            "claim": "First claim.",
            "supporting_comparison_ids": ["cmp_001"],
        },
        {
            "claim_id": "claim_002",
            "claim": "Second claim.",
            "supporting_comparison_ids": ["cmp_002"],
        },
    ],
}


agent = EvidenceAgent(GeminiClient())

# Simulate Gemini accidentally returning only one check.
incomplete_checks = [
    {
        "claim_id": "claim_001",
        "status": "supported",
        "evidence": [
            {
                "comparison_id": "cmp_001",
                "arxiv_id": "mock-001",
            }
        ],
        "reason": "Supported.",
    }
]


result = agent._validate_claim_checks(
    incomplete_checks,
    draft,
    comparison_input,
)

print(json.dumps(result, indent=2))

assert len(result) == len(draft["claims"])

missing_check = next(
    check for check in result
    if check["claim_id"] == "claim_002"
)

assert missing_check["status"] == "unsupported"
assert missing_check["evidence"] == []
assert missing_check["reason"] == (
    "No evidence check was returned for this synthesis claim."
)

print("\nEvidence coverage test passed.")