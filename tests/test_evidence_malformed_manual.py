import json

from agents.evidence_agent import EvidenceAgent
from agents.llm_client import GeminiClient


with open("phase0/mocks/comparison_malformed.json", "r", encoding="utf-8") as f:
    comparison_input = json.load(f)


llm = GeminiClient()
agent = EvidenceAgent(llm)

draft = {
    "research_question": comparison_input["research_question"],
    "draft_id": "malformed_evidence_test",
    "claims": [
        {
            "claim_id": "fake_performance_claim",
            "claim": "The model achieved 99% accuracy.",
            "supporting_comparison_ids": [],
        }
    ],
    "report": "The model achieved 99% accuracy.",
}


result = agent.check(draft, comparison_input)

print(json.dumps(result, indent=2))

check = result["claim_checks"][0]

assert check["claim_id"] == "fake_performance_claim"
assert check["status"] == "unsupported"
assert check["evidence"] == []

print("\nMalformed evidence test passed.")