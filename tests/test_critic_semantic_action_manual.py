from agents.critic_agent import CriticAgent


class FakeLLM:
    def complete(self, system: str, user: str) -> str:
        return "{}"


def test_unsupported_claim_cannot_be_weakened():
    agent = CriticAgent(FakeLLM())

    draft = {
        "draft_id": "semantic_action_test",
        "claims": [
            {
                "claim_id": "claim_001",
                "claim": "Transformer models outperform CNN models.",
            }
        ],
    }

    evidence = {
        "draft_id": "semantic_action_test",
        "claim_checks": [
            {
                "claim_id": "claim_001",
                "status": "unsupported",
                "evidence": [],
                "reason": "No evidence supports the claim.",
            }
        ],
    }

    invalid_result = {
        "draft_id": "semantic_action_test",
        "flags": [
            {
                "claim_id": "claim_001",
                "reason": "The claim lacks supporting evidence.",
                "severity": "major",
                "revision_instruction": "Weaken the claim.",
                "allowed_action": "weaken",
            }
        ],
        "decision": "revise",
    }

    try:
        agent._validate_response_structure(
            invalid_result,
            draft,
            evidence,
        )
    except ValueError:
        print("Critic semantic action test passed.")
        return

    raise AssertionError(
        "Critic accepted 'weaken' for a claim whose evidence status is unsupported."
    )


if __name__ == "__main__":
    test_unsupported_claim_cannot_be_weakened()