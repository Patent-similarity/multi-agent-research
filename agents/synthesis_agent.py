"""Synthesis agent: turns comparison data into a research draft."""

import json
import uuid

from agents.llm_client import parse_json_response


class SynthesisAgent:
    def __init__(self, llm_client):
        self.llm = llm_client

    def build(self, comparison_input: dict) -> dict:
        research_question = comparison_input["research_question"]
        comparison = comparison_input["comparison"]

        prompt = f"""
You are the synthesis agent in a multi-agent research pipeline.

Research question:
{research_question}

Comparison data:
{json.dumps(comparison, indent=2)}

Create a research synthesis from ONLY the comparison data above.

Rules:
1. Do not invent facts, numbers, datasets, architectures, metrics, or performance results.
2. Never report a performance value unless it appears in reported_performance.
3. Every claim must be supported by one or more comparison_id values.
4. If a comparison row has no reported performance, do not invent one.
5. Never use placeholders such as "XX%", "YY%", "N/A", or "unknown" as if they were reported results.
6. Keep disagreements faithful to the comparison data.
7. The report must be consistent with the claims.
8. Return ONLY valid JSON.

Return exact structure with research_question, draft_id, claims[{{claim_id, claim, supporting_comparison_ids}}], report.
"""

        response = self.llm.complete(
            system="You are a careful research synthesis agent.",
            user=prompt,
        )

        draft = parse_json_response(response)

        draft["research_question"] = research_question

        if not draft.get("draft_id"):
            draft["draft_id"] = str(uuid.uuid4())

        return draft

    def revise(self, draft: dict, revision_instructions: dict) -> dict:
        """Revise only claims explicitly identified by the critic."""

        prompt = f"""
You are the revision stage of a research synthesis pipeline.

Original draft:
{json.dumps(draft, indent=2)}

Revision instructions:
{json.dumps(revision_instructions, indent=2)}

Revise the draft using ONLY the instructions provided.

Rules:
1. Only modify claims whose claim_id appears in revision_instructions.
2. Do not reword, improve, or otherwise change untouched claims.
3. Follow the allowed_action exactly: rewrite, weaken, or remove.
4. Use only the supporting_evidence supplied in the revision instructions.
5. Do not invent facts, numbers, datasets, architectures, metrics, or performance results.
6. Keep supporting_comparison_ids valid.
7. Keep the report consistent with the final claims.
8. If a claim is removed, remove its corresponding discussion from the report.
9. Preserve the original draft_id.
10. Return ONLY valid JSON.

Return the same structure as the original draft:
{{
  "research_question": "...",
  "draft_id": "...",
  "claims": [
    {{
      "claim_id": "...",
      "claim": "...",
      "supporting_comparison_ids": ["..."]
    }}
  ],
  "report": "..."
}}
"""

        response = self.llm.complete(
            system="You are a careful research revision agent.",
            user=prompt,
        )

        revised = parse_json_response(response)

        revised["research_question"] = draft["research_question"]
        revised["draft_id"] = draft["draft_id"]

        return revised