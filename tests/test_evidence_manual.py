import json

from agents.evidence_agent import EvidenceAgent
from agents.llm_client import GeminiClient


with open("phase0/mocks/comparison_happy.json", "r", encoding="utf-8") as f:
    comparison_input = json.load(f)


with open("phase0/mocks/comparison_happy.json", "r", encoding="utf-8") as f:
    comparison_data = json.load(f)


llm = GeminiClient()
agent = EvidenceAgent(llm)

# Build a simple synthesis draft from the comparison data.
draft = {
    "research_question": comparison_input["research_question"],
    "draft_id": "manual_evidence_test",
    "claims": [
        {
            "claim_id": "claim_001",
            "claim": comparison_data["comparison"][0]["claim"],
            "supporting_comparison_ids": [
                comparison_data["comparison"][0]["comparison_id"]
            ],
        }
    ],
    "report": comparison_data["comparison"][0]["claim"],
}


result = agent.check(draft, comparison_input)

print(json.dumps(result, indent=2))

assert result["draft_id"] == draft["draft_id"]
assert len(result["claim_checks"]) == len(draft["claims"])

check = result["claim_checks"][0]

assert check["claim_id"] == "claim_001"
assert check["status"] in {
    "supported",
    "partially_supported",
    "unsupported",
}
assert isinstance(check["evidence"], list)
assert check["reason"]

print("\nEvidence test passed.")