import json

from agents.synthesis_agent import SynthesisAgent


class FakeLLM:
    def complete(self, system, user):
        return json.dumps({
            "research_question": (
                "How do transformer-based models compare with "
                "convolutional/recurrent deep-learning approaches "
                "for EEG-based emotion recognition?"
            ),
            "draft_id": "manual_revision_test",
            "claims": [
                {
                    "claim_id": "claim_001",
                    "claim": (
                        "Transformer models achieved a reported accuracy "
                        "of 86% on the DEAP dataset."
                    ),
                    "supporting_comparison_ids": ["cmp_001"],
                }
            ],
            "report": (
                "Transformer models achieved a reported accuracy "
                "of 86% on the DEAP dataset."
            ),
        })


draft = {
    "research_question": (
        "How do transformer-based models compare with "
        "convolutional/recurrent deep-learning approaches "
        "for EEG-based emotion recognition?"
    ),
    "draft_id": "manual_revision_test",
    "claims": [
        {
            "claim_id": "claim_001",
            "claim": (
                "Transformer models achieve 99% accuracy "
                "on EEG emotion recognition."
            ),
            "supporting_comparison_ids": ["cmp_001"],
        }
    ],
    "report": (
        "Transformer models achieve 99% accuracy "
        "on EEG emotion recognition."
    ),
}


revision_instructions = {
    "draft_id": "manual_revision_test",
    "revision_instructions": [
        {
            "claim_id": "claim_001",
            "original_claim": (
                "Transformer models achieve 99% accuracy "
                "on EEG emotion recognition."
            ),
            "reason": "The 99% accuracy claim is unsupported.",
            "required_change": (
                "Replace the unsupported 99% value with the "
                "86% accuracy reported in cmp_001."
            ),
            "allowed_action": "rewrite",
            "supporting_evidence": [
                {
                    "comparison_id": "cmp_001",
                    "arxiv_id": "mock-001",
                }
            ],
        }
    ],
}


agent = SynthesisAgent(FakeLLM())
result = agent.revise(draft, revision_instructions)

print(json.dumps(result, indent=2))

assert result["draft_id"] == draft["draft_id"]
assert result["research_question"] == draft["research_question"]
assert result["claims"][0]["claim_id"] == "claim_001"
assert "86%" in result["claims"][0]["claim"]
assert "99%" not in result["claims"][0]["claim"]
assert result["claims"][0]["supporting_comparison_ids"] == ["cmp_001"]

print("Synthesis revision test passed.")
