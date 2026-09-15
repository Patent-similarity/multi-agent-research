import json

from agents.llm_client import GeminiClient
from agents.synthesis_agent import SynthesisAgent


with open("phase0/mocks/comparison_happy.json", "r", encoding="utf-8") as f:
    comparison_input = json.load(f)


llm = GeminiClient()
agent = SynthesisAgent(llm)

draft = agent.build(comparison_input)

assert draft["research_question"] == comparison_input["research_question"]
assert draft["draft_id"]
assert isinstance(draft["claims"], list)
assert draft["report"]

for claim in draft["claims"]:
    assert claim["claim_id"]
    assert claim["claim"]
    assert claim["supporting_comparison_ids"]

    for comparison_id in claim["supporting_comparison_ids"]:
        assert comparison_id in {
            row["comparison_id"] for row in comparison_input["comparison"]
        }

assert "XX%" not in draft["report"]
assert "YY%" not in draft["report"]

for claim in draft["claims"]:
    assert "XX%" not in claim["claim"]
    assert "YY%" not in claim["claim"]

print(json.dumps(draft, indent=2))
print("\nSynthesis test passed.")