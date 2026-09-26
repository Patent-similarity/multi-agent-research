from agents.pipeline import PipelineExecutionError, ResearchPipeline


class FakeLLM:
    def complete(self, system: str, user: str) -> str:
        return "{}"


def test_synthesis_failure_has_context():
    pipeline = ResearchPipeline(FakeLLM())

    original_error = ValueError("synthetic synthesis failure")

    def failing_build(comparison_input):
        raise original_error

    pipeline.synthesis.build = failing_build

    try:
        pipeline.run(
            {
                "comparison_rows": [],
            }
        )
    except PipelineExecutionError as exc:
        assert exc.stage == "synthesis"
        assert exc.revision_number == 0
        assert exc.run_id is not None
        assert exc.original_error is original_error
        assert exc.__cause__ is original_error
    else:
        raise AssertionError(
            "Expected PipelineExecutionError from synthesis failure."
        )

    print("Synthesis failure context test passed.")


def test_evidence_failure_has_context():
    pipeline = ResearchPipeline(FakeLLM())

    draft = {
        "draft_id": "failure_test",
        "claims": [],
        "report": "",
    }

    def fake_build(comparison_input):
        return draft

    pipeline.synthesis.build = fake_build

    original_error = ValueError("synthetic evidence failure")

    def failing_check(draft, comparison_input):
        raise original_error

    pipeline.evidence.check = failing_check

    try:
        pipeline.run(
            {
                "comparison_rows": [],
            }
        )
    except PipelineExecutionError as exc:
        assert exc.stage == "evidence"
        assert exc.revision_number == 0
        assert exc.run_id is not None
        assert exc.original_error is original_error
        assert exc.__cause__ is original_error
    else:
        raise AssertionError(
            "Expected PipelineExecutionError from evidence failure."
        )

    print("Evidence failure context test passed.")


def test_critic_failure_has_context():
    pipeline = ResearchPipeline(FakeLLM())

    draft = {
        "draft_id": "failure_test",
        "claims": [],
        "report": "",
    }

    evidence = {
        "draft_id": "failure_test",
        "claim_checks": [],
    }

    pipeline.synthesis.build = lambda comparison_input: draft
    pipeline.evidence.check = lambda draft, comparison_input: evidence

    original_error = ValueError("synthetic critic failure")

    def failing_evaluate(draft, evidence_result):
        raise original_error

    pipeline.critic.evaluate = failing_evaluate

    try:
        pipeline.run(
            {
                "comparison_rows": [],
            }
        )
    except PipelineExecutionError as exc:
        assert exc.stage == "critic"
        assert exc.revision_number == 0
        assert exc.run_id is not None
        assert exc.original_error is original_error
        assert exc.__cause__ is original_error
    else:
        raise AssertionError(
            "Expected PipelineExecutionError from critic failure."
        )

    print("Critic failure context test passed.")


def test_revision_failure_has_context():
    pipeline = ResearchPipeline(FakeLLM())

    draft = {
        "draft_id": "failure_test",
        "claims": [
            {
                "claim_id": "claim_001",
                "claim": "Test claim.",
                "supporting_comparison_ids": [],
            }
        ],
        "report": "Test claim.",
    }

    evidence = {
        "draft_id": "failure_test",
        "claim_checks": [
            {
                "claim_id": "claim_001",
                "status": "supported",
                "evidence": [],
                "reason": "Supported.",
            }
        ],
    }

    critic = {
        "draft_id": "failure_test",
        "flags": [
            {
                "claim_id": "claim_001",
                "reason": "Needs revision.",
                "severity": "major",
                "revision_instruction": "Rewrite the claim.",
                "allowed_action": "rewrite",
            }
        ],
        "decision": "revise",
    }

    pipeline.synthesis.build = lambda comparison_input: draft
    pipeline.evidence.check = lambda draft, comparison_input: evidence
    pipeline.critic.evaluate = lambda draft, evidence_result: critic

    original_error = ValueError("synthetic revision failure")

    def failing_revise(draft, revision_instructions):
        raise original_error

    pipeline.synthesis.revise = failing_revise

    try:
        pipeline.run(
            {
                "comparison_rows": [],
            }
        )
    except PipelineExecutionError as exc:
        assert exc.stage == "revision"
        assert exc.revision_number == 1
        assert exc.run_id is not None
        assert exc.original_error is original_error
        assert exc.__cause__ is original_error
    else:
        raise AssertionError(
            "Expected PipelineExecutionError from revision failure."
        )

    print("Revision failure context test passed.")


if __name__ == "__main__":
    test_synthesis_failure_has_context()
    test_evidence_failure_has_context()
    test_critic_failure_has_context()
    test_revision_failure_has_context()

    print("Pipeline failure handling test passed.")