"""Orchestrate synthesis, evidence checking, criticism, and revision."""

from __future__ import annotations

import uuid

from agents.critic_agent import CriticAgent
from agents.evidence_agent import EvidenceAgent
from agents.revision_log import create_revision_row, derive_run_outcome
from agents.synthesis_agent import SynthesisAgent


class PipelineExecutionError(RuntimeError):
    """Raised when a pipeline stage fails with execution context."""

    def __init__(
        self,
        *,
        run_id: str | None,
        revision_number: int | None,
        stage: str,
        original_error: Exception,
    ):
        self.run_id = run_id
        self.revision_number = revision_number
        self.stage = stage
        self.original_error = original_error

        context = [
            f"stage={stage}",
        ]

        if run_id is not None:
            context.append(f"run_id={run_id}")

        if revision_number is not None:
            context.append(f"revision={revision_number}")

        super().__init__(
            "Pipeline stage failed "
            f"({', '.join(context)}): {original_error}"
        )


class ResearchPipeline:
    """Run Synthesis -> Evidence -> Critic -> Revision."""

    def __init__(self, llm_client):
        self.synthesis = SynthesisAgent(llm_client)
        self.evidence = EvidenceAgent(llm_client)
        self.critic = CriticAgent(llm_client)

    @staticmethod
    def _raise_stage_error(
        *,
        run_id: str | None,
        revision_number: int | None,
        stage: str,
        exc: Exception,
    ) -> None:
        """Raise a contextual pipeline error while preserving the cause."""

        raise PipelineExecutionError(
            run_id=run_id,
            revision_number=revision_number,
            stage=stage,
            original_error=exc,
        ) from exc

    def run_once(self, comparison_input: dict) -> dict:
        """Run one Synthesis -> Evidence -> Critic pass."""

        try:
            draft = self.synthesis.build(comparison_input)
        except Exception as exc:
            self._raise_stage_error(
                run_id=None,
                revision_number=None,
                stage="synthesis",
                exc=exc,
            )

        try:
            evidence_result = self.evidence.check(
                draft,
                comparison_input,
            )
        except Exception as exc:
            self._raise_stage_error(
                run_id=None,
                revision_number=None,
                stage="evidence",
                exc=exc,
            )

        try:
            critic_result = self.critic.evaluate(
                draft,
                evidence_result,
            )
        except Exception as exc:
            self._raise_stage_error(
                run_id=None,
                revision_number=None,
                stage="critic",
                exc=exc,
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

        try:
            draft = self.synthesis.build(comparison_input)
        except Exception as exc:
            self._raise_stage_error(
                run_id=run_id,
                revision_number=0,
                stage="synthesis",
                exc=exc,
            )

        for revision_number in range(3):
            try:
                evidence_result = self.evidence.check(
                    draft,
                    comparison_input,
                )
            except Exception as exc:
                self._raise_stage_error(
                    run_id=run_id,
                    revision_number=revision_number,
                    stage="evidence",
                    exc=exc,
                )

            try:
                critic_result = self.critic.evaluate(
                    draft,
                    evidence_result,
                )
            except Exception as exc:
                self._raise_stage_error(
                    run_id=run_id,
                    revision_number=revision_number,
                    stage="critic",
                    exc=exc,
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
                final_flagged_claim_ids = {
                    flag["claim_id"]
                    for flag in critic_result["flags"]
                }

                for row in revision_rows:
                    if row["claim_id"] in final_flagged_claim_ids:
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

            try:
                draft = self.synthesis.revise(
                    draft,
                    revision_instructions,
                )
            except Exception as exc:
                self._raise_stage_error(
                    run_id=run_id,
                    revision_number=revision_number + 1,
                    stage="revision",
                    exc=exc,
                )

            after_claims = {
                claim["claim_id"]: claim["claim"]
                for claim in draft["claims"]
            }

            current_flagged_claim_ids = {
                flag["claim_id"]
                for flag in flags
            }

            for row in revision_rows:
                if row["claim_id"] not in current_flagged_claim_ids:
                    row["resolved"] = True
                    row["final_status"] = "revised"

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