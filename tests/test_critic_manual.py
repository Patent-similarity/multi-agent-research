import json

from agents.critic_agent import CriticAgent
from agents.llm_client import GeminiClient


with open("phase0/mocks/comparison_happy.json", "r", encoding="utf-8") as f:
    comparison_input = json.load(f)


draft = {
    "research_question": comparison_input["research_question"],
    "draft_id": "manual_critic_test",
    "claims": [
        {
            "claim_id": "claim_001",
            "claim": (
                "Transformer-based approaches can model long-range relationships "
                "in EEG representations."
            ),
            "supporting_comparison_ids": ["cmp_001"],
        }
    ],
    "report": (
        "The comparison data supports the claim that Transformer-based "
        "approaches can model long-range relationships in EEG representations."
    ),
}


evidence_result = {
    "draft_id": "manual_critic_test",
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
            "reason": "Supported by the comparison data.",
        }
    ],
}


agent = CriticAgent(GeminiClient())
result = agent.evaluate(draft, evidence_result)

print(json.dumps(result, indent=2))

assert result["draft_id"] == "manual_critic_test"
assert "flags" in result
assert result["decision"] == "accept"
assert result["flags"] == []

print("Critic happy-path test passed.")