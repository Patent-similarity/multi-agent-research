import json

from agents.critic_agent import CriticAgent


class FakeLLM:
    def __init__(self, response):
        self.response = response

    def complete(self, system: str, user: str) -> str:
        return self.response


draft = {
    "draft_id": "malformed_critic_test",
    "claims": [
        {
            "claim_id": "claim_001",
            "claim": "Transformer models achieved a reported accuracy of 86%.",
            "supporting_comparison_ids": ["cmp_001"],
        }
    ],
    "report": "Transformer models achieved a reported accuracy of 86%.",
}


malformed_cases = {
    "response_not_object": [],
    "flags_not_list": {
        "flags": {},
    },
    "flag_not_object": {
        "flags": ["invalid"],
    },
    "missing_claim_id": {
        "flags": [
            {
                "reason": "Unsupported.",
                "severity": "major",
                "revision_instruction": "Rewrite the claim.",
                "allowed_action": "rewrite",
            }
        ],
    },
    "unknown_claim_id": {
        "flags": [
            {
                "claim_id": "claim_999",
                "reason": "Unsupported.",
                "severity": "major",
                "revision_instruction": "Rewrite the claim.",
                "allowed_action": "rewrite",
            }
        ],
    },
    "invalid_severity": {
        "flags": [
            {
                "claim_id": "claim_001",
                "reason": "Unsupported.",
                "severity": "critical",
                "revision_instruction": "Rewrite the claim.",
                "allowed_action": "rewrite",
            }
        ],
    },
    "invalid_allowed_action": {
        "flags": [
            {
                "claim_id": "claim_001",
                "reason": "Unsupported.",
                "severity": "major",
                "revision_instruction": "Rewrite the claim.",
                "allowed_action": "ignore",
            }
        ],
    },
    "missing_reason": {
        "flags": [
            {
                "claim_id": "claim_001",
                "severity": "major",
                "revision_instruction": "Rewrite the claim.",
                "allowed_action": "rewrite",
            }
        ],
    },
    "missing_revision_instruction": {
        "flags": [
            {
                "claim_id": "claim_001",
                "reason": "Unsupported.",
                "severity": "major",
                "allowed_action": "rewrite",
            }
        ],
    },
}


for name, malformed_response in malformed_cases.items():
    llm = FakeLLM(json.dumps(malformed_response))
    agent = CriticAgent(llm)

    try:
        agent.evaluate(draft, {})
    except ValueError:
        print(f"{name}: correctly rejected")
    else:
        raise AssertionError(
            f"Malformed Critic response was accepted: {name}"
        )


valid_response = {
    "flags": [
        {
            "claim_id": "claim_001",
            "reason": "The claim is unsupported.",
            "severity": "major",
            "revision_instruction": "Rewrite using supported evidence.",
            "allowed_action": "rewrite",
        }
    ]
}

agent = CriticAgent(FakeLLM(json.dumps(valid_response)))
result = agent.evaluate(draft, {})

assert result["draft_id"] == "malformed_critic_test"
assert result["decision"] == "revise"
assert result["flags"][0]["claim_id"] == "claim_001"

print("Critic malformed structure test passed.")