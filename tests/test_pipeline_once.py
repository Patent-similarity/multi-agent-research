"""Orchestrate synthesis, evidence checking, criticism, and revision."""

from agents.critic_agent import CriticAgent
from agents.evidence_agent import EvidenceAgent
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