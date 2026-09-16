import json

from agents.critic_agent import CriticAgent
from agents.llm_client import GeminiClient


draft = {
    "research_question": (
        "How do transformer-based models compare with convolutional/recurrent "
        "deep-learning approaches for EEG-based emotion recognition?"
    ),
    "draft_id": "manual_critic_failure_test",
    "claims": [
        {
            "claim_id": "claim_001",
            "claim": "Transformer models achieve 99% accuracy on EEG emotion recognition.",
            "supporting_comparison_ids": ["cmp_001"],
        }
    ],
    "report": (
        "Transformer models achieve 99% accuracy on EEG emotion recognition."
    ),
}


evidence_result = {
    "draft_id": "manual_critic_failure_test",
    "claim_checks": [
        {
            "claim_id": "claim_001",
            "status": "unsupported",
            "evidence": [],
            "reason": "No valid source evidence supports the 99% accuracy claim.",
        }
    ],
}


agent = CriticAgent(GeminiClient())
result = agent.evaluate(draft, evidence_result)

print(json.dumps(result, indent=2))

assert result["draft_id"] == "manual_critic_failure_test"
assert len(result["flags"]) > 0
assert result["decision"] == "revise"

print("Critic failure-path test passed.")