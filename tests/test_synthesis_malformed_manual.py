import json

from agents.synthesis_agent import SynthesisAgent


class FakeLLM:
    def complete(self, system, user):
        return json.dumps(
            {
                "draft_id": "bad_draft",
                "claims": "this should be a list",
                "report": "test",
            }
        )


with open("phase0/mocks/comparison_happy.json", "r", encoding="utf-8") as f:
    comparison_input = json.load(f)


agent = SynthesisAgent(FakeLLM())

try:
    agent.build(comparison_input)
except RuntimeError as exc:
    assert "claims list" in str(exc)
    print("Malformed synthesis output correctly rejected.")
else:
    raise AssertionError(
        "Expected SynthesisAgent.build() to reject malformed claims."
    )