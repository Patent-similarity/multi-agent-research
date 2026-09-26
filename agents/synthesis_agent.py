"""Synthesis agent: turns comparison data into a research draft."""

import json
import uuid

from agents.llm_client import parse_json_response


class SynthesisAgent:
    def __init__(self, llm_client):
        self.llm = llm_client

    @staticmethod
    def _validate_draft(draft: dict, comparison_ids: set[str]) -> dict:
        """Validate the structural contract of a synthesis draft."""

        if not isinstance(draft, dict):
            raise RuntimeError("Synthesis output must be a JSON object.")

        claims = draft.get("claims")
        if not isinstance(claims, list):
            raise RuntimeError("Synthesis output must contain a claims list.")

        report = draft.get("report")
        if not isinstance(report, str):
            raise RuntimeError("Synthesis output must contain a report string.")

        draft_id = draft.get("draft_id")
        if not isinstance(draft_id, str) or not draft_id.strip():
            raise RuntimeError("Synthesis output must contain a non-empty draft_id.")

        for index, claim in enumerate(claims):
            if not isinstance(claim, dict):
                raise RuntimeError(
                    f"Synthesis claim at index {index} must be a JSON object."
                )

            claim_id = claim.get("claim_id")
            if not isinstance(claim_id, str) or not claim_id.strip():
                raise RuntimeError(
                    f"Synthesis claim at index {index} must contain a non-empty claim_id."
                )

            claim_text = claim.get("claim")
            if not isinstance(claim_text, str) or not claim_text.strip():
                raise RuntimeError(
                    f"Synthesis claim '{claim_id}' must contain non-empty claim text."
                )

            supporting_ids = claim.get("supporting_comparison_ids")
            if not isinstance(supporting_ids, list):
                raise RuntimeError(
                    f"Synthesis claim '{claim_id}' must contain "
                    "supporting_comparison_ids as a list."
                )

            for comparison_id in supporting_ids:
                if not isinstance(comparison_id, str) or not comparison_id.strip():
                    raise RuntimeError(
                        f"Synthesis claim '{claim_id}' contains an invalid "
                        "supporting comparison_id."
                    )

                if comparison_id not in comparison_ids:
                    raise RuntimeError(
                        f"Synthesis claim '{claim_id}' references unknown "
                        f"comparison_id '{comparison_id}'."
                    )

        return draft

    @staticmethod
    def _comparison_ids(comparison) -> set[str]:
        """Extract valid comparison IDs from comparison data."""

        if not isinstance(comparison, list):
            raise RuntimeError("Comparison data must be a list.")

        comparison_ids = set()

        for index, row in enumerate(comparison):
            if not isinstance(row, dict):
                raise RuntimeError(
                    f"Comparison row at index {index} must be a JSON object."
                )

            comparison_id = row.get("comparison_id")

            if isinstance(comparison_id, str) and comparison_id.strip():
                comparison_ids.add(comparison_id)

        return comparison_ids

    def build(self, comparison_input: dict) -> dict:
        research_question = comparison_input["research_question"]
        comparison = comparison_input["comparison"]

        comparison_ids = self._comparison_ids(comparison)

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

        return self._validate_draft(draft, comparison_ids)

    def revise(self, draft: dict, revision_instructions: dict) -> dict:
        """Revise only claims explicitly identified by the critic."""

        comparison_ids = {
            comparison_id
            for claim in draft.get("claims", [])
            for comparison_id in claim.get("supporting_comparison_ids", [])
            if isinstance(comparison_id, str)
        }

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

        validated = self._validate_draft(revised, comparison_ids)

        if validated["draft_id"] != draft["draft_id"]:
            raise RuntimeError(
                "Synthesis revision changed the original draft_id."
            )

        return validated