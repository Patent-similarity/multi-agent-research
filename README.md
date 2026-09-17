# Research Agent(Work in Progress)

A multi-agent pipeline that answers a research question by retrieving papers
from arXiv, extracting and comparing findings, synthesizing a report, and
running a verification loop (Evidence + Critic) that revises unsupported
claims before shipping.

## Research Question

> How do transformer-based models compare with convolutional/recurrent
> deep-learning approaches for EEG-based emotion recognition, in terms of
> datasets, architectures, evaluation metrics, and reported performance —
> and where do published studies disagree?

See `phase0/research_question.md` for full scope.

## Pipeline

```
Planner -> Retrieval -> Analysis -> Comparison -> Synthesis <-> Evidence <-> Critic -> Report
```

Agents 1-4 (Planner, Retrieval, Analysis, Comparison) retrieve and structure
real arXiv evidence. Agents 5-7 (Synthesis, Evidence, Critic) synthesize a
report and run a bounded revision loop until claims are supported or the
retry cap is hit, at which point the report ships with remaining claims
flagged.

## Ownership

| Phase   | Swayam (Synthesis/Evidence/Critic/Deploy)        | Ayush (Planner/Retrieval/Analysis/Comparison/Frontend) |
|---------|---------------------------------------------------|---------------------------------------------------------|
| Phase 1 | Agents 5-7 against mocks                          | Agents 1-4 against arXiv                                 |
| Phase 2 | Integrate real Comparison -> Synthesis            | Support integration/debugging                            |
| Phase 3 | Revision loop + logging                           | —                                                         |
| Phase 4 | Agents 5-7 robustness                             | Agents 1-4 robustness                                     |
| Phase 5 | Backend deployment + revision-log API             | Streamlit frontend                                        |
| Phase 6 | Verification-loop argument                        | Retrieval/extraction/comparison methodology               |

## Repo Layout

```
phase0/
  research_question.md      research question, scope, boundaries
  decomposition.json        locked 5-way Planner decomposition
  retrieval_spec.md         corpus, query strategy, dedup rule
  loop_contract.md          binary trigger, retry cap, ship-with-flags
  revision_log_schema.json  unified revision-log schema (Phase 3 + Phase 5)
  schemas/                  every agent-to-agent JSON contract
  mocks/                    hand-crafted Comparison table fixtures
```

## Status

Phase 0 — Spec & Schema Lock: **complete**. See exit criteria in
`phase0/loop_contract.md` and `phase0/retrieval_spec.md`.

## Setup

```bash
pip install -r requirements.txt
```
