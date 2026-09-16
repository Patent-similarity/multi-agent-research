"""Critic agent: evaluates evidence checks and flags draft problems."""

from agents.llm_client import parse_json_response


class CriticAgent:
    """Evaluate evidence checks and determine whether a draft needs revision."""

    def __init__(self, llm_client):
        self.llm = llm_client

    def evaluate(self, draft: dict, evidence_result: dict) -> dict:
        """Evaluate the draft using the Evidence-agent results."""

        prompt = f"""
You are the critic agent in a multi-agent research pipeline.

Your job is to review a synthesis draft using the evidence verification results.

Synthesis draft:
{draft}

Evidence verification:
{evidence_result}

Rules:
1. Review every claim in the synthesis draft.
2. Flag claims that are unsupported or partially supported.
3. Also flag claims that overstate what the evidence supports.
4. Do not invent new evidence.
5. For every flag, include:
   - claim_id
   - reason
   - severity
   - revision_instruction
   - allowed_action
6. Use severity values: "major" or "minor".
7. Use allowed_action values:
   - "rewrite" when the claim should be rewritten using the available evidence.
   - "weaken" when the claim is broadly valid but is stated too strongly.
   - "remove" when the claim cannot be supported by the available evidence.
8. Choose allowed_action based only on the evidence verification result.
9. If there are no problems, return an empty flags list.
10. Return ONLY valid JSON.

Return exactly this structure:
{{
  "draft_id": "{draft.get("draft_id", "")}",
  "flags": [
    {{
      "claim_id": "string",
      "reason": "string",
      "severity": "major|minor",
      "revision_instruction": "string",
      "allowed_action": "rewrite|weaken|remove"
    }}
  ]
}}
"""

        response = self.llm.complete(
            system="You are a conservative research critic agent.",
            user=prompt,
        )

        result = parse_json_response(response)

        result["draft_id"] = draft["draft_id"]

        flags = result.get("flags", [])

        if len(flags) > 0:
            result["decision"] = "revise"
        else:
            result["decision"] = "accept"

        return result