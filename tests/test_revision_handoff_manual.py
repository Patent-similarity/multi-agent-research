import json

from agents.pipeline import ResearchPipeline


pipeline = ResearchPipeline.__new__(ResearchPipeline)

draft = {
    "research_question": "Test question",
    "draft_id": "handoff_test",
    "claims": [
        {
            "claim_id": "claim_001",
            "claim": "Transformer models achieve 99% accuracy.",
            "supporting_comparison_ids": ["cmp_001"],
        }
    ],
    "report": "Transformer models achieve 99% accuracy.",
}

evidence_result = {
    "draft_id": "handoff_test",
    "claim_checks": [
        {
            "claim_id": "claim_001",
            "status": "unsupported",
            "evidence": [],
            "reason": "No valid evidence supports the claim.",
        }
    ],
}

critic_result = {
    "draft_id": "handoff_test",
    "flags": [
        {
            "claim_id": "claim_001",
            "reason": "The accuracy value is unsupported.",
            "severity": "major",
            "revision_instruction": "Remove the unsupported 99% value.",
            "allowed_action": "weaken",
        }
    ],
    "decision": "revise",
}

result = pipeline.build_revision_instructions(
    draft,
    evidence_result,
    critic_result,
)

print(json.dumps(result, indent=2))

assert result["draft_id"] == "handoff_test"
assert len(result["revision_instructions"]) == 1

instruction = result["revision_instructions"][0]

assert instruction["claim_id"] == "claim_001"
assert instruction["original_claim"] == draft["claims"][0]["claim"]
assert instruction["reason"] == critic_result["flags"][0]["reason"]
assert instruction["required_change"] == critic_result["flags"][0]["revision_instruction"]
assert instruction["allowed_action"] == "weaken"
assert instruction["supporting_evidence"] == []

print("Revision handoff test passed.")