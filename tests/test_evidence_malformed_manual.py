import json

from agents.evidence_agent import EvidenceAgent


class FakeLLM:
    def __init__(self, response):
        self.response = response

    def complete(self, system, user):
        return self.response


with open(
    "phase0/mocks/comparison_malformed.json",
    "r",
    encoding="utf-8",
) as f:
    comparison_input = json.load(f)


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


malformed_cases = {
    "claim_checks_not_list": {
        "claim_checks": {}
    },
    "check_not_object": {
        "claim_checks": ["invalid"]
    },
    "missing_claim_id": {
        "claim_checks": [
            {
                "status": "supported",
                "evidence": [],
                "reason": "test",
            }
        ]
    },
    "invalid_status": {
        "claim_checks": [
            {
                "claim_id": "fake_performance_claim",
                "status": "invalid",
                "evidence": [],
                "reason": "test",
            }
        ]
    },
    "evidence_not_list": {
        "claim_checks": [
            {
                "claim_id": "fake_performance_claim",
                "status": "supported",
                "evidence": {},
                "reason": "test",
            }
        ]
    },
    "reason_not_string": {
        "claim_checks": [
            {
                "claim_id": "fake_performance_claim",
                "status": "supported",
                "evidence": [],
                "reason": 123,
            }
        ]
    },
    "evidence_reference_not_object": {
        "claim_checks": [
            {
                "claim_id": "fake_performance_claim",
                "status": "supported",
                "evidence": ["invalid"],
                "reason": "test",
            }
        ]
    },
    "empty_comparison_id": {
        "claim_checks": [
            {
                "claim_id": "fake_performance_claim",
                "status": "supported",
                "evidence": [
                    {
                        "comparison_id": "",
                        "arxiv_id": "1234.5678",
                    }
                ],
                "reason": "test",
            }
        ]
    },
    "empty_arxiv_id": {
        "claim_checks": [
            {
                "claim_id": "fake_performance_claim",
                "status": "supported",
                "evidence": [
                    {
                        "comparison_id": "comparison_1",
                        "arxiv_id": "",
                    }
                ],
                "reason": "test",
            }
        ]
    },
}


for name, malformed_response in malformed_cases.items():
    llm = FakeLLM(json.dumps(malformed_response))
    agent = EvidenceAgent(llm)

    try:
        agent.check(draft, comparison_input)
    except ValueError as exc:
        print(f"{name}: correctly rejected ({exc})")
    else:
        raise AssertionError(
            f"Malformed evidence response was accepted: {name}"
        )


print("\nMalformed evidence structure test passed.")