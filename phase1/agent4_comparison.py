"""
Agent 4 — Comparison

Job: read all 5 analysis_<sub_question_id>.json files (Agent 3's output)
and merge them into ONE table matching
phase0/schemas/comparison_to_synthesis.json — the CRITICAL SHARED CONTRACT
that swayam's Synthesis/Evidence/Critic agents (5-7) build against.

Key responsibilities per the schema's own _invariants:
- source_claim_id MUST be copied forward from each finding's claim_id.
  Only null if a row merges multiple findings with no single source
  (rare — we don't do that kind of merging here, so this should never
  actually be null in our output).
- Nullable fields stay null, never empty string.
- evidence needs `title` (Analysis's evidence only has arxiv_id +
  source_text) — we look titles up from the retrieval_<id>.json papers.
- reported_performance needs a `unit` (Analysis's reported_values only has
  metric + value) — we parse a trailing % or similar off the value string
  where present, else unit is null (never guessed/invented).

Design choices this agent owns (schema doesn't dictate these, so
documenting the reasoning rather than hiding it):
- comparison_group: set to `dataset` when present, since "which papers are
  comparable" is most naturally grouped by shared evaluation dataset. null
  if the finding has no dataset.
- disagreement.present: True only for rows from the 'disagreements'
  sub-question (that's literally what Analysis already extracted them
  for). Everything else defaults to present=False, description=null.
  Deeper cross-row disagreement detection belongs to swayam's
  Evidence/Critic agents downstream, not this agent.

Run:
    python agent4_comparison.py
Reads:
    phase1/output/analysis_<id>.json        (all 5)
    phase1/output/retrieval_<id>.json        (for evidence titles)
    phase1/output/planner_output.json        (for research_question)
Writes:
    phase1/output/comparison_output.json     (validated — Phase 1 exit criteria)
"""
import json
import re
from pathlib import Path

from validate import validate_or_raise, check_no_empty_strings_where_null_expected

OUTPUT_DIR = Path(__file__).resolve().parent / "output"
SUB_QUESTION_IDS = ["approaches", "datasets", "architectures", "metrics", "disagreements"]

# Matches a trailing unit like %, ms, s, MB — conservative, only strips
# what it's confident about. Falls back to unit=null rather than guessing.
_UNIT_PATTERN = re.compile(r"^([\d.]+)\s*(%|ms|s|MB|GB|Hz)$")


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"{path} not found.")
    return json.loads(path.read_text(encoding="utf-8"))


def build_title_lookup() -> dict[str, str]:
    """arxiv_id -> title, built from all 5 retrieval files, so Comparison's
    evidence entries can carry a title (Analysis's evidence doesn't have one)."""
    lookup = {}
    for sub_question_id in SUB_QUESTION_IDS:
        path = OUTPUT_DIR / f"retrieval_{sub_question_id}.json"
        if not path.exists():
            continue
        data = load_json(path)
        for paper in data.get("papers", []):
            lookup[paper["arxiv_id"]] = paper["title"]
    return lookup


def parse_reported_value(metric: str, value: str) -> dict:
    """Turn Analysis's {metric, value} into Comparison's {metric, value, unit}.
    Only splits a unit off when confident (matches _UNIT_PATTERN exactly).
    Never invents a unit — null is the correct answer when unsure."""
    match = _UNIT_PATTERN.match(value.strip())
    if match:
        number, unit = match.groups()
        return {"metric": metric, "value": number, "unit": unit}
    return {"metric": metric, "value": value, "unit": None}


def build_evidence(finding_evidence: list[dict], title_lookup: dict[str, str]) -> list[dict]:
    result = []
    for ev in finding_evidence:
        arxiv_id = ev["arxiv_id"]
        result.append({
            "arxiv_id": arxiv_id,
            "title": title_lookup.get(arxiv_id, "(title unavailable)"),
            "source_text": ev["source_text"],
        })
    return result


def build_disagreement(sub_question_id: str, claim: str) -> dict:
    if sub_question_id == "disagreements":
        return {"present": True, "description": claim}
    return {"present": False, "description": None}


def finding_to_comparison_row(
    finding: dict,
    sub_question_id: str,
    comparison_id: str,
    title_lookup: dict[str, str],
) -> dict:
    return {
        "comparison_id": comparison_id,
        "source_claim_id": finding["claim_id"],  # copied forward — see schema invariant
        "sub_question_id": sub_question_id,
        "claim": finding["claim"],
        "approach": finding["approach"],
        "dataset": finding["dataset"],
        "architecture": finding["architecture"],
        "metrics": finding["metrics"],
        "reported_performance": [
            parse_reported_value(rv["metric"], rv["value"]) for rv in finding["reported_values"]
        ],
        "evidence": build_evidence(finding["evidence"], title_lookup),
        "comparison_group": finding["dataset"],  # see module docstring for reasoning
        "disagreement": build_disagreement(sub_question_id, finding["claim"]),
        "confidence": finding["confidence"],
    }


def run() -> dict:
    planner_output = load_json(OUTPUT_DIR / "planner_output.json")
    research_question = planner_output["research_question"]
    title_lookup = build_title_lookup()

    comparison_rows = []
    row_counter = 1
    for sub_question_id in SUB_QUESTION_IDS:
        analysis_path = OUTPUT_DIR / f"analysis_{sub_question_id}.json"
        if not analysis_path.exists():
            print(f"  (skipping '{sub_question_id}' — {analysis_path.name} not found)")
            continue
        analysis_data = load_json(analysis_path)
        for finding in analysis_data["findings"]:
            comparison_id = f"cmp-{row_counter:03d}"
            row_counter += 1
            comparison_rows.append(
                finding_to_comparison_row(finding, sub_question_id, comparison_id, title_lookup)
            )

    payload = {
        "research_question": research_question,
        "comparison": comparison_rows,
    }

    # Guardrail: every source_claim_id we set should be a real string (never
    # accidentally None) since we don't do multi-finding merges here.
    missing_source_claim = [r["comparison_id"] for r in comparison_rows if not r["source_claim_id"]]
    if missing_source_claim:
        raise ValueError(
            f"source_claim_id unexpectedly missing/null for rows: {missing_source_claim}. "
            f"This agent doesn't merge multiple findings into one row, so every row should "
            f"have traced back to exactly one Analysis claim_id."
        )

    # Guardrail beyond jsonschema: catch empty-string-instead-of-null on the
    # nullable fields, including the nested disagreement.description.
    empty_string_errors = check_no_empty_strings_where_null_expected(
        comparison_rows,
        ["approach", "dataset", "architecture", "comparison_group", "source_claim_id", "disagreement.description"],
    )
    if empty_string_errors:
        raise ValueError(
            "Found empty string where null was expected:\n  - " + "\n  - ".join(empty_string_errors)
        )

    validate_or_raise(payload, "comparison_to_synthesis.json")

    out_path = OUTPUT_DIR / "comparison_output.json"
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\n{len(comparison_rows)} comparison rows written to {out_path}")
    print("This is the file swayam's Synthesis agent (Phase 2) will consume.")
    return payload


if __name__ == "__main__":
    run()