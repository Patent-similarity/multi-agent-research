# Research Agent (Work in Progress)

A multi-agent research pipeline that answers a research question by retrieving papers from arXiv, extracting and comparing findings, synthesizing a report, and running a verification loop (Evidence + Critic) that revises unsupported claims before shipping.

## Research Question

> How do transformer-based models compare with convolutional/recurrent deep-learning approaches for EEG-based emotion recognition, in terms of datasets, architectures, evaluation metrics, and reported performance — and where do published studies disagree?

See `phase0/research_question.md` for the full scope and boundaries.

## Pipeline

```text
Planner -> Retrieval -> Analysis -> Comparison -> Synthesis -> Evidence -> Critic
                                                        ^              |
                                                        |              |
                                                        +-- Revision --+
```

Agents 1–4 (Planner, Retrieval, Analysis, Comparison) retrieve and structure arXiv evidence.

Agents 5–7 (Synthesis, Evidence, Critic) synthesize the research report and run a bounded revision loop. Unsupported or partially supported claims are flagged by the Critic and passed back to Synthesis for revision. Evidence and Critic then re-check the revised draft. The loop stops when the report is accepted or the revision cap is reached, in which case remaining flags are shipped with the report.

## Research Baseline

The retrieval, analysis, and comparison pipeline has a **frozen 22-paper baseline** used as the canonical input for downstream validation.

The frozen baseline contains:

* 22 canonical papers
* 34 comparison rows
* 20 unique cited papers
* 0 comparison citations outside the frozen 22-paper corpus
* Planner output
* 5 Retrieval outputs
* 5 Analysis outputs
* Comparison output
* Retrieval checkpoint

The frozen baseline is preserved under:

```text
phase1/results/baseline/
```

Experimental validation outputs are kept separate and do not replace the frozen baseline.

## Validation Findings

Several failure modes were identified and addressed during development:

* LLM grounding instructions alone were insufficient to prevent unsupported synthesis claims.
* Evidence validation must independently validate comparison and arXiv references.
* Malformed comparison data can lead to incorrect evidence verification if structural validation is not applied.
* Explicit comparative claims require explicit comparative evidence rather than merely citing two unrelated studies.
* Claims describing published disagreement require disagreement evidence supported by at least two distinct arXiv sources.
* Agent 3 disagreement extraction was tightened so that a disagreement finding must represent an explicit cross-paper conflict rather than a single-paper claim.
* The revision loop is bounded and records each revision in the revision log.

After tightening Agent 3's disagreement extraction, the experimental comparison output contained:

```text
29 comparison rows
0 disagreement rows
0 disagreement findings
```

This experimental output is **not a replacement for the frozen 34-row baseline**. It demonstrates the effect of the stricter disagreement rule.

## Revision Loop

The revision loop performs:

```text
Synthesis
   |
Evidence
   |
Critic
   |
   +---- accept ----> Report
   |
   +---- revise ----> Synthesis
```

The pipeline allows a maximum of two revisions.

After each revision, the **full revised draft** is passed through Evidence and Critic again rather than checking only the previously flagged claim.

This behavior is covered by deterministic tests that verify:

* Evidence is rerun after each revision.
* Critic is rerun after each revision.
* The revised draft is actually supplied to the next Evidence pass.
* Two revision cycles can occur before acceptance.
* The revision count and revision log are updated correctly.
* The retry cap results in a `shipped_with_flags` outcome when issues remain unresolved.

The full-draft retry behavior is documented as **implemented pipeline behavior**, rather than as a jointly agreed Phase 0 design decision.

## Ownership

| Phase   | Swayam (Synthesis/Evidence/Critic/Deploy) | Ayush (Planner/Retrieval/Analysis/Comparison/Frontend) |
| ------- | ----------------------------------------- | ------------------------------------------------------ |
| Phase 1 | Agents 5–7 against mocks                  | Agents 1–4 against arXiv                               |
| Phase 2 | Integrate real Comparison -> Synthesis    | Support integration/debugging                          |
| Phase 3 | Revision loop + logging                   | —                                                      |
| Phase 4 | Agents 5–7 robustness                     | Agents 1–4 robustness                                  |
| Phase 5 | Backend deployment + revision-log API     | Streamlit frontend                                     |
| Phase 6 | Verification-loop argument                | Retrieval/extraction/comparison methodology            |

## Repo Layout

```text
phase0/
  research_question.md      research question, scope, boundaries
  decomposition.json        locked 5-way Planner decomposition
  retrieval_spec.md         corpus, query strategy, dedup rule
  loop_contract.md          binary trigger, retry cap, ship-with-flags
  revision_log_schema.json  unified revision-log schema (Phase 3 + Phase 5)
  schemas/                  every agent-to-agent JSON contract
  mocks/                    hand-crafted Comparison table fixtures

phase1/
  results/
    baseline/               frozen 22-paper canonical baseline
  output/                   experimental/current pipeline outputs
```

## Status

### Phase 0 — Spec & Schema Lock

**Complete**

Research question, scope, decomposition, retrieval specification, loop contract, schemas, and revision-log schema were locked.

### Phase 1 — Retrieval, Analysis & Comparison

**Baseline complete and frozen**

The canonical 22-paper / 34-row baseline is frozen and preserved under `phase1/results/baseline/`.

Additional validation identified and addressed provenance and disagreement-extraction issues without modifying the frozen baseline.

### Phase 2 — Synthesis, Evidence & Critic

**Implemented and validated with deterministic tests**

The Synthesis, Evidence, and Critic agents are integrated with the real Comparison output.

Evidence validation includes structural checks for:

* valid comparison references
* valid arXiv provenance
* missing evidence
* explicit comparative claims
* disagreement claims requiring multiple distinct sources

### Phase 3 — Revision Loop

**Implemented; deterministic validation complete**

The bounded revision loop, revision logging, full-draft retry behavior, and ship-with-flags path are implemented and covered by deterministic tests.

A fresh live end-to-end run against the frozen baseline remains pending because the Gemini Free Tier API quota was exhausted during validation.

### Phase 4 — Robustness

**In progress**

Current work is focused on robustness and failure handling, including malformed LLM responses, API failures, rate limits, and ensuring the verification loop fails safely without relying exclusively on live LLM calls.

The comparative-claim and disagreement-evidence guards described in Phase 2 are implemented and covered by deterministic tests; they are not considered open Phase 4 work.

## Setup

```bash
pip install -r requirements.txt
```

## Running the Pipeline

The canonical pipeline reads from the frozen baseline:

```text
phase1/results/baseline/comparison_output.json
```

Run:

```bash
python run_pipeline.py
```

The pipeline writes the final output to:

```text
phase1/output/final_pipeline_output.json
```

Live end-to-end execution requires an available Gemini API quota.

## Testing

Deterministic manual tests cover:

* Evidence validation
* Evidence coverage
* malformed evidence references
* comparative-claim validation
* disagreement evidence validation
* frozen-baseline disagreement regression
* synthesis revision
* revision handoff
* revision logging
* full-draft revision retries
* retry-cap / ship-with-flags behavior

The deterministic tests do not require Gemini API calls and are used to validate pipeline behavior without consuming API quota.
