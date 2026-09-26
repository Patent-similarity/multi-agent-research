from copy import deepcopy

from agents.synthesis_agent import SynthesisAgent


class FakeLLM:
    def __init__(self):
        self.calls = 0

    def complete(self, system: str, user: str) -> str:
        self.calls += 1

        return """
        {
          "research_question": "Transformer vs CNN for EEG emotion recognition",
          "draft_id": "draft_001",
          "claims": [
            {
              "claim_id": "claim_001",
              "claim": "Transformer models report higher accuracy in this comparison.",
              "supporting_comparison_ids": ["comparison_001"]
            },
            {
              "claim_id": "claim_002",
              "claim": "CNN models were evaluated on EEG datasets.",
              "supporting_comparison_ids": ["comparison_002"]
            }
          ],
          "report": "Revised report."
        }
        """


def test_revise_does_not_mutate_original_draft():
    llm = FakeLLM()
    agent = SynthesisAgent(llm)

    draft = {
        "research_question": "Transformer vs CNN for EEG emotion recognition",
        "draft_id": "draft_001",
        "claims": [
            {
                "claim_id": "claim_001",
                "claim": "Transformer models report lower accuracy.",
                "supporting_comparison_ids": ["comparison_001"],
            },
            {
                "claim_id": "claim_002",
                "claim": "CNN models were evaluated on EEG datasets.",
                "supporting_comparison_ids": ["comparison_002"],
            },
        ],
        "report": "Original report.",
    }

    original_draft = deepcopy(draft)

    revision_instructions = {
        "draft_id": "draft_001",
        "revision_instructions": [
            {
                "claim_id": "claim_001",
                "original_claim": "Transformer models report lower accuracy.",
                "reason": "The evidence does not support the original wording.",
                "required_change": "Rewrite the claim using the available evidence.",
                "allowed_action": "rewrite",
                "supporting_evidence": [
                    {
                        "comparison_id": "comparison_001",
                        "arxiv_id": "paper_001",
                    }
                ],
            }
        ],
    }

    revised = agent.revise(
        draft,
        revision_instructions,
    )

    assert draft == original_draft
    assert revised["draft_id"] == draft["draft_id"]
    assert revised["research_question"] == draft["research_question"]

    assert llm.calls == 1

    print("Synthesis revision idempotence test passed.")


if __name__ == "__main__":
    test_revise_does_not_mutate_original_draft()