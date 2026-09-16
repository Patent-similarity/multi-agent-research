"""Orchestrate synthesis, evidence checking, criticism, and revision."""

from __future__ import annotations

import uuid

from agents.critic_agent import CriticAgent
from agents.evidence_agent import EvidenceAgent
from agents.revision_log import create_revision_row, derive_run_outcome
from agents.synthesis_agent import SynthesisAgent


class ResearchPipeline:
    """Run Synthesis -> Evidence -> Critic -> Revision."""

    def __init__(self, llm_client):
        self.synthesis = SynthesisAgent(llm_client)
        self.evidence = EvidenceAgent(llm_client)
        self.critic = CriticAgent(llm_client)

    def run_once(self, comparison_input: dict) -> dict:
        """Run one Synthesis -> Evidence -> Critic pass."""

        draft = self.synthesis.build(comparison_input)

        evidence_result = self.evidence.check(
            draft,
            comparison_input,
        )

        critic_result = self.critic.evaluate(
            draft,
            evidence_result,
        )

        return {
            "draft": draft,
            "evidence": evidence_result,
            "critic": critic_result,
        }

    def build_revision_instructions(
        self,
        draft: dict,
        evidence_result: dict,
        critic_result: dict,
    ) -> dict:
        """Build the locked Critic -> Synthesis revision handoff."""

        claim_map = {
            claim["claim_id"]: claim
            for claim in draft["claims"]
        }

        evidence_map = {
            check["claim_id"]: check
            for check in evidence_result.get("claim_checks", [])
        }

        instructions = []

        for flag in critic_result.get("flags", []):
            claim_id = flag["claim_id"]
            claim = claim_map.get(claim_id)

            if not claim:
                continue

            evidence_check = evidence_map.get(claim_id, {})

            instructions.append(
                {
                    "claim_id": claim_id,
                    "original_claim": claim["claim"],
                    "reason": flag["reason"],
                    "required_change": flag["revision_instruction"],
                    "allowed_action": flag["allowed_action"],
                    "supporting_evidence": evidence_check.get(
                        "evidence", []
                    ),
                }
            )

        return {
            "draft_id": draft["draft_id"],
            "revision_instructions": instructions,
        }

    def run(self, comparison_input: dict) -> dict:
        """Run the pipeline with a maximum of two revisions."""

        run_id = str(uuid.uuid4())
        revision_rows = []

        draft = self.synthesis.build(comparison_input)

        for revision_number in range(3):
            evidence_result = self.evidence.check(
                draft,
                comparison_input,
            )

            critic_result = self.critic.evaluate(
                draft,
                evidence_result,
            )

            flags = critic_result.get("flags", [])

            if critic_result["decision"] == "accept":
                for row in revision_rows:
                    row["resolved"] = True
                    row["final_status"] = "revised"

                outcome = derive_run_outcome(
                    revision_rows,
                    [
                        claim["claim_id"]
                        for claim in draft["claims"]
                    ],
                )

                return {
                    "run_id": run_id,
                    "draft": draft,
                    "evidence": evidence_result,
                    "critic": critic_result,
                    "revision_number": revision_number,
                    "revision_log": revision_rows,
                    "outcome": outcome,
                }

            if revision_number == 2:
                for row in revision_rows:
                    row["resolved"] = False
                    row["final_status"] = "shipped_with_flag"

                outcome = derive_run_outcome(
                    revision_rows,
                    [
                        claim["claim_id"]
                        for claim in draft["claims"]
                    ],
                )

                return {
                    "run_id": run_id,
                    "draft": draft,
                    "evidence": evidence_result,
                    "critic": critic_result,
                    "revision_number": revision_number,
                    "revision_log": revision_rows,
                    "outcome": outcome,
                }

            revision_instructions = self.build_revision_instructions(
                draft,
                evidence_result,
                critic_result,
            )

            before_claims = {
                claim["claim_id"]: claim["claim"]
                for claim in draft["claims"]
            }

            draft = self.synthesis.revise(
                draft,
                revision_instructions,
            )

            after_claims = {
                claim["claim_id"]: claim["claim"]
                for claim in draft["claims"]
            }

            for flag in flags:
                claim_id = flag["claim_id"]

                before_claim = before_claims.get(
                    claim_id,
                    "",
                )

                after_claim = after_claims.get(
                    claim_id,
                )

                revision_action = flag["allowed_action"]

                revision_rows.append(
                    create_revision_row(
                        run_id=run_id,
                        draft_id=draft["draft_id"],
                        revision_number=revision_number + 1,
                        claim_id=claim_id,
                        before_claim=before_claim,
                        after_claim=after_claim,
                        flag_reason=flag["reason"],
                        flag_severity=flag["severity"],
                        critic_decision=critic_result["decision"],
                        revision_action=revision_action,
                        resolved=False,
                        final_status="revised",
                    )
                )

        raise RuntimeError("Pipeline revision loop exited unexpectedly.")