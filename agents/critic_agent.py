"""Critic agent: evaluates evidence checks and flags draft problems."""

from agents.llm_client import parse_json_response


class CriticAgent:
    """Evaluate evidence checks and determine whether a draft needs revision."""

    def __init__(self, llm_client):
        self.llm = llm_client

    @staticmethod
    def _validate_response_structure(
        result: dict,
        draft: dict,
        evidence_result: dict | None = None,
    ) -> None:
        """Reject malformed Critic responses before pipeline processing."""

        if not isinstance(result, dict):
            raise ValueError("Critic response must be a JSON object.")

        flags = result.get("flags")

        if not isinstance(flags, list):
            raise ValueError("Critic response flags must be a list.")

        draft_claim_ids = {
            claim.get("claim_id")
            for claim in draft.get("claims", [])
            if isinstance(claim, dict)
            and isinstance(claim.get("claim_id"), str)
            and claim.get("claim_id").strip()
        }

        allowed_severities = {
            "major",
            "minor",
        }

        allowed_actions = {
            "rewrite",
            "weaken",
            "remove",
        }

        for flag in flags:
            if not isinstance(flag, dict):
                raise ValueError(
                    "Each Critic flag must be an object."
                )

            claim_id = flag.get("claim_id")

            if not isinstance(claim_id, str) or not claim_id.strip():
                raise ValueError(
                    "Critic flag claim_id must be a non-empty string."
                )

            if claim_id not in draft_claim_ids:
                raise ValueError(
                    f"Critic flag references unknown claim_id '{claim_id}'."
                )

            reason = flag.get("reason")

            if not isinstance(reason, str) or not reason.strip():
                raise ValueError(
                    "Critic flag reason must be a non-empty string."
                )

            severity = flag.get("severity")

            if severity not in allowed_severities:
                raise ValueError(
                    "Critic flag severity must be one of: major, minor."
                )

            revision_instruction = flag.get("revision_instruction")

            if (
                not isinstance(revision_instruction, str)
                or not revision_instruction.strip()
            ):
                raise ValueError(
                    "Critic flag revision_instruction must be a "
                    "non-empty string."
                )

            allowed_action = flag.get("allowed_action")

            if allowed_action not in allowed_actions:
                raise ValueError(
                    "Critic flag allowed_action must be one of: "
                    "rewrite, weaken, remove."
                )
            if evidence_result is not None:
                evidence_status_by_claim = {
                    check.get("claim_id"): check.get("status")
                    for check in evidence_result.get("claim_checks", [])
                    if isinstance(check, dict)
                }

                evidence_status = evidence_status_by_claim.get(claim_id)

                if (
                    evidence_status == "unsupported"
                    and allowed_action != "remove"
                ):
                    raise ValueError(
                        "Critic cannot use "
                        f"allowed_action='{allowed_action}' for an "
                        "unsupported claim; unsupported claims must be "
                        "removed."
                    )

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

        self._validate_response_structure(result, draft, evidence_result,)

        result["draft_id"] = draft["draft_id"]

        flags = result["flags"]

        if len(flags) > 0:
            result["decision"] = "revise"
        else:
            result["decision"] = "accept"

        return result