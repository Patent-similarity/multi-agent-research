"""Evidence agent: verifies synthesis claims against comparison data."""

import json

from agents.llm_client import parse_json_response


class EvidenceAgent:
    """Check synthesis claims against the original comparison data."""

    def __init__(self, llm_client):
        self.llm = llm_client

    def _validate_claim_checks(
        self,
        claim_checks: list,
        draft: dict,
        comparison_input: dict,
    ) -> list:
        """Validate evidence references and ensure every claim is checked."""

        comparisons = {
            row["comparison_id"]: row
            for row in comparison_input["comparison"]
        }

        returned_checks = {
            check.get("claim_id"): check
            for check in claim_checks
            if check.get("claim_id")
        }

        validated = []

        for claim in draft["claims"]:
            claim_id = claim["claim_id"]
            check = returned_checks.get(claim_id)

            # If Gemini forgot to check a claim, fail closed.
            if not check:
                validated.append(
                    {
                        "claim_id": claim_id,
                        "status": "unsupported",
                        "evidence": [],
                        "reason": (
                            "No evidence check was returned for this "
                            "synthesis claim."
                        ),
                    }
                )
                continue

            valid_evidence = []

            for evidence_ref in check.get("evidence", []) or []:
                comparison_id = evidence_ref.get("comparison_id")
                arxiv_id = evidence_ref.get("arxiv_id")

                row = comparisons.get(comparison_id)

                if not row:
                    continue

                if not arxiv_id:
                    continue

                row_arxiv_ids = {
                    evidence.get("arxiv_id")
                    for evidence in (row.get("evidence") or [])
                    if evidence.get("arxiv_id")
                }

                if arxiv_id not in row_arxiv_ids:
                    continue

                valid_evidence.append(evidence_ref)

            check["evidence"] = valid_evidence

            if not valid_evidence:
                check["status"] = "unsupported"
                check["reason"] = (
                    "The cited evidence failed validation against the original "
                    "comparison data, so the claim cannot be treated as supported."
                )

            validated.append(check)

        return validated

    def check(self, draft: dict, comparison_input: dict) -> dict:
        """Verify each synthesis claim against comparison data."""

        prompt = f"""
You are the evidence verification agent in a multi-agent research pipeline.

Your job is to independently check whether each claim in the synthesis draft
is supported by the original comparison data.

Research question:
{comparison_input["research_question"]}

Synthesis draft:
{json.dumps(draft, indent=2)}

Original comparison data:
{json.dumps(comparison_input["comparison"], indent=2)}

Rules:
1. Use ONLY the original comparison data as evidence.
2. Do not use outside knowledge.
3. Do not invent evidence.
4. A claim is "supported" only when the comparison data clearly supports it
   AND valid source evidence exists for that comparison row.
5. A claim is "partially_supported" when only part of the claim is supported.
6. A claim is "unsupported" when the comparison data does not support it or
   when valid source evidence is missing.
7. Only cite comparison IDs and arxiv IDs that actually exist in the
   comparison data.
8. Never use an empty arxiv_id as evidence.
9. If a claim has no supporting evidence, return an empty evidence list.
10. Explain the verification decision briefly in "reason".
11. Return one claim_check for every claim in the synthesis draft.
12. Return ONLY valid JSON.

Return exactly this structure:
{{
  "draft_id": "{draft.get("draft_id", "")}",
  "claim_checks": [
    {{
      "claim_id": "string",
      "status": "supported|unsupported|partially_supported",
      "evidence": [
        {{
          "comparison_id": "string",
          "arxiv_id": "string"
        }}
      ],
      "reason": "string"
    }}
  ]
}}
"""

        response = self.llm.complete(
            system="You are a conservative research evidence verification agent.",
            user=prompt,
        )

        result = parse_json_response(response)

        result["draft_id"] = draft["draft_id"]

        result["claim_checks"] = self._validate_claim_checks(
            result.get("claim_checks", []),
            draft,
            comparison_input,
        )

        return result