import json

from agents.evidence_agent import EvidenceAgent


class FakeLLM:
    def complete(self, system, user):
        return json.dumps({
            "draft_id": "frozen_disagreement_test",
            "claim_checks": [
                {
                    "claim_id": "claim-007",
                    "status": "supported",
                    "evidence": [
                        {
                            "comparison_id": "cmp-030",
                            "arxiv_id": "2212.08744",
                        },
                        {
                            "comparison_id": "cmp-031",
                            "arxiv_id": "2110.06553",
                        },
                        {
                            "comparison_id": "cmp-032",
                            "arxiv_id": "2608.09088",
                        },
                        {
                            "comparison_id": "cmp-033",
                            "arxiv_id": "2212.12134",
                        },
                        {
                            "comparison_id": "cmp-034",
                            "arxiv_id": "2407.20519",
                        },
                    ],
                    "reason": "The cited studies disagree.",
                }
            ],
        })


with open(
    "phase1/results/baseline/comparison_output.json",
    encoding="utf-8",
) as f:
    comparison_input = json.load(f)


draft = {
    "research_question": comparison_input["research_question"],
    "draft_id": "frozen_disagreement_test",
    "claims": [
        {
            "claim_id": "claim-007",
            "claim": (
                "Published studies disagree on domain generalization "
                "strategies, optimal attention factorization choices, "
                "dynamic fusion vs feature concatenation across task "
                "granularities, high-density vs minimal channel "
                "configurations, and short-segment versus full long-term "
                "trial processing."
            ),
            "supporting_comparison_ids": [
                "cmp-030",
                "cmp-031",
                "cmp-032",
                "cmp-033",
                "cmp-034",
            ],
        }
    ],
    "report": "",
}


agent = EvidenceAgent(FakeLLM())
result = agent.check(draft, comparison_input)

check = result["claim_checks"][0]

assert check["status"] == "unsupported"
assert check["evidence"] == []
assert "fewer than two distinct arxiv sources" in check["reason"].lower()

print("Frozen disagreement guard test passed.")
print(check["reason"])