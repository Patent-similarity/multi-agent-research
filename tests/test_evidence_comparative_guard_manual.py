import json

from agents.evidence_agent import EvidenceAgent


class FakeLLM:
    def __init__(self, claim, evidence):
        self.claim = claim
        self.evidence = evidence

    def complete(self, system, user):
        return json.dumps({
            "draft_id": "comparative_guard_test",
            "claim_checks": [
                {
                    "claim_id": "claim_001",
                    "status": "supported",
                    "evidence": self.evidence,
                    "reason": "The cited comparison data supports the claim.",
                }
            ],
        })


def run_test(claim, evidence, comparison):
    draft = {
        "research_question": "Test comparative claim verification",
        "draft_id": "comparative_guard_test",
        "claims": [
            {
                "claim_id": "claim_001",
                "claim": claim,
                "supporting_comparison_ids": [
                    item["comparison_id"] for item in evidence
                ],
            }
        ],
        "report": claim,
    }

    agent = EvidenceAgent(FakeLLM(claim, evidence))
    return agent.check(draft, {"research_question": "Test comparative claim verification", "comparison": comparison})["claim_checks"][0]


comparison = [
    {
        "comparison_id": "cmp-005",
        "source_claim_id": "source-005",
        "sub_question_id": "approaches",
        "claim": (
            "Systematic evaluation indicates that transfer learning "
            "approaches perform better than other machine learning methods "
            "in mitigating dataset shift for cross-subject and cross-session "
            "EEG emotion classification."
        ),
        "approach": "Transfer learning",
        "dataset": None,
        "architecture": None,
        "metrics": [],
        "reported_performance": [],
        "evidence": [
            {
                "arxiv_id": "mock-transfer",
                "title": "Mock Transfer Learning Review",
                "source_text": (
                    "Transfer learning approaches perform better than "
                    "other machine learning methods."
                ),
            }
        ],
        "comparison_group": "transfer_learning",
        "disagreement": {
            "present": False,
            "description": None,
        },
        "confidence": "high",
    },
    {
        "comparison_id": "cmp-001",
        "source_claim_id": "source-001",
        "sub_question_id": "approaches",
        "claim": "A transformer model was applied to EEG emotion recognition.",
        "approach": "Transformer",
        "dataset": "DEAP",
        "architecture": "Transformer encoder",
        "metrics": ["accuracy"],
        "reported_performance": ["90% accuracy"],
        "evidence": [
            {
                "arxiv_id": "mock-transformer",
                "title": "Mock Transformer Study",
                "source_text": "The transformer model achieved 90% accuracy.",
            }
        ],
        "comparison_group": "transformer",
        "disagreement": {
            "present": False,
            "description": None,
        },
        "confidence": "high",
    },
    {
        "comparison_id": "cmp-002",
        "source_claim_id": "source-002",
        "sub_question_id": "approaches",
        "claim": "A CNN model was applied to EEG emotion recognition.",
        "approach": "CNN",
        "dataset": "SEED",
        "architecture": "CNN",
        "metrics": ["accuracy"],
        "reported_performance": ["85% accuracy"],
        "evidence": [
            {
                "arxiv_id": "mock-cnn",
                "title": "Mock CNN Study",
                "source_text": "The CNN model achieved 85% accuracy.",
            }
        ],
        "comparison_group": "cnn",
        "disagreement": {
            "present": False,
            "description": None,
        },
        "confidence": "high",
    },
]


# Positive case:
# The comparison row itself explicitly contains the comparative relationship.
positive = run_test(
    (
        "Transfer learning approaches perform better than other machine "
        "learning methods for EEG emotion classification."
    ),
    [
        {
            "comparison_id": "cmp-005",
            "arxiv_id": "mock-transfer",
        }
    ],
    comparison,
)

assert positive["status"] == "supported"


# Negative case:
# Two rows provide valid evidence independently, but neither row states
# that transformers outperform CNNs.
negative = run_test(
    "Transformers outperform CNNs for EEG emotion recognition.",
    [
        {
            "comparison_id": "cmp-001",
            "arxiv_id": "mock-transformer",
        },
        {
            "comparison_id": "cmp-002",
            "arxiv_id": "mock-cnn",
        },
    ],
    comparison,
)

assert negative["status"] == "unsupported"

print("Positive case:", positive["status"])
print("Negative case:", negative["status"])
print("Comparative guard test passed.")
