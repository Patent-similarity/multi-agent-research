"""Synthesis agent: turns comparison data into a research draft."""

import json
import uuid

from agents.llm_client import parse_json_response

class SynthesisAgent:
    """Build a research draft from Comparison-agent output."""

    def __init__(self, llm_client):
        self.llm = llm_client

    def build(self, comparison_input: dict) -> dict:
        """Generate a structured synthesis draft from comparison data."""

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

Return this exact structure:
{{
  "research_question": "{research_question}",
  "draft_id": "string",
  "claims": [
    {{
      "claim_id": "string",
      "claim": "string",
      "supporting_comparison_ids": ["string"]
    }}
  ],
  "report": "string"
}}
"""

        response = self.llm.complete(
            system="You are a careful research synthesis agent.",
            user=prompt,
        )

        draft = parse_json_response(response)

        # Give every build a local draft ID if the model did not provide one.
        if not draft.get("draft_id"):
            draft["draft_id"] = str(uuid.uuid4())

        return draft