# Research Findings

This document records the main findings and engineering lessons discovered while building and validating the multi-agent research system for EEG-based emotion recognition.

The findings are based on actual pipeline tests, retrieval experiments, validation checks, and controlled revision-loop tests performed during development.

---

# PHASE 1 — Retrieval, Analysis & Comparison

## 1. LLM grounding instructions alone are not sufficient

During the initial Synthesis Agent test, Gemini generated placeholder performance values such as `XX%` and `YY%` even though the prompt explicitly prohibited invented performance values.

After strengthening the synthesis prompt, this behavior was reduced. However, the test showed that prompt instructions alone cannot guarantee factual output.

**Key takeaway:** The Synthesis Agent should not be treated as the final verification layer. Independent Evidence and Critic agents are required before a report is accepted.

---

## 2. LLM-generated synthesis can create unsupported comparisons

During synthesis testing, the model generated a comparative statement such as a Transformer achieving 86% accuracy versus a CNN achieving 76%, even though that exact comparison was not directly stated as a single source claim.

This showed that the Synthesis Agent can derive relationships between multiple comparison rows rather than simply restating source claims.

That behavior is useful for generating a research report, but it also creates a verification problem: a comparison may sound reasonable while still being unsupported by the underlying evidence.

**Key takeaway:** Generated synthesis needs to be checked against the original comparison data rather than being trusted because the statement appears plausible.

---

## 3. Malformed comparison data can cause incorrect evidence verification

During malformed-input testing, the Evidence Agent initially marked a 99% performance claim as supported even though the corresponding comparison row did not contain valid source evidence.

A deterministic validation layer was then added to check whether cited comparison entries actually contained valid source information.

After the change, the same claim was downgraded to `unsupported` and the invalid evidence reference was removed.

**Key takeaway:** LLM-based verification should be combined with deterministic checks against the underlying structured data.

---

## 4. Broad arXiv retrieval produced substantial domain noise

The initial arXiv retrieval queries produced papers that matched generic query terms but were not actually about EEG-based emotion recognition.

Examples included:

* EMERSK
* SAFER
* EMOVOME
* DEAP-3600, which refers to a dark-matter detector rather than the EEG emotion dataset
* Seed-Coder, an LLM-related paper

A hard post-retrieval domain filter was therefore added to Agent 2.

A paper is retained when:

* `EEG` or `electroencephalog...` appears in the title, **or**
* the EEG term appears at least twice in the abstract.

Agent 3 also performs an explicit domain check as a second layer of protection.

### Retrieval impact

The canonical paper set decreased from:

**58 papers → 22 papers**

after applying the domain filtering.

The specific false-positive case `EMERSK` was also confirmed to have **zero occurrences** in the regenerated comparison output.

**Key takeaway:** Keyword-based arXiv retrieval alone was too noisy for this research question. Domain-specific filtering was necessary before analysis and comparison.

---

## 5. A frozen baseline was necessary for reliable validation

After retrieval and analysis changes, the Phase 1 outputs were frozen before downstream integration.

The frozen baseline contained:

| Artifact              |                                                    Baseline |
| --------------------- | ----------------------------------------------------------: |
| Canonical papers      |                                                      **22** |
| Comparison rows       |                                                      **34** |
| Comparison categories |                                                       **5** |
| Research dimensions   | Approaches, datasets, architectures, metrics, disagreements |

The frozen comparison data became the reference dataset for later pipeline validation.

This was important because regenerating retrieval or analysis outputs during later phases could change the evidence being tested and make it difficult to determine whether a pipeline improvement or a data change caused the result.

**Key takeaway:** Downstream validation should use a fixed evidence baseline so that changes to the agent pipeline can be evaluated independently of retrieval changes.

---

# PHASE 2 — Evidence & Critic Validation

## 6. Evidence validation can verify claims against the original comparison data

The Evidence Agent was tested using the frozen 34-row comparison dataset.

The agent validates cited comparison IDs against the original comparison data instead of relying only on the text generated by the Synthesis Agent.

This allows the system to check whether:

* the cited comparison entry exists,
* the cited paper matches,
* the reported result is consistent with the comparison data,
* and the evidence actually supports the claim.

This creates a separation between:

**Synthesis → generates claims**

and

**Evidence → verifies claims**

**Key takeaway:** Separating generation from verification reduces the chance that a plausible-looking synthesis claim is automatically accepted as factual.

---

## 7. Disagreement claims require structural disagreement evidence

A deterministic guard was added for claims describing published disagreements.

When a claim contains language such as:

* disagreement
* conflict
* contradiction
* contradict

the Evidence Agent checks whether at least one of the validated comparison entries is explicitly marked as a disagreement.

If no validated evidence is marked as an actual disagreement, the claim is downgraded to `unsupported`.

This was tested using both negative and positive controlled cases.

### Negative test

A synthetic disagreement claim was given evidence from a comparison entry that was **not** marked as a disagreement.

Result:

`unsupported`

### Positive structural test

A disagreement claim was given evidence from comparison entry `cmp-030`, which was marked with:

`disagreement.present = true`

Result:

`supported`

This positive test demonstrates that the Evidence Agent correctly recognizes the structural disagreement marker. However, it does **not** establish that `cmp-030` represents a genuine disagreement between independent published studies.

Further provenance inspection showed that the frozen disagreement rows `cmp-030` through `cmp-034` each cite only one arXiv paper. A later validation rule for Agent 3 therefore required disagreement findings to contain evidence from at least two distinct papers. Under that stricter rule, the regenerated disagreement analysis produced zero findings.

The retrieved corpus was also inspected for explicit cross-paper contradictions, but no sufficiently clear example was established.

**Key takeaway:** The Evidence Agent can enforce the requirement that disagreement claims use entries structurally marked as disagreements, but the current corpus does not yet provide sufficient evidence to claim that a genuine cross-publication disagreement has been established.

---

## 8. Explicit comparative claims require explicit comparative evidence

The initial Evidence Agent could validate each cited comparison row independently without checking whether the relationship asserted by a synthesis claim was actually present in those rows.

A controlled example demonstrated the problem:

> Transformers outperform CNNs for EEG emotion recognition.

The synthetic evidence contained one row describing Transformer performance and another describing CNN performance. Both rows were individually valid, but neither comparison row explicitly stated that Transformers outperform CNNs.

The original Evidence behavior marked the synthesized claim as `supported`.

A deterministic comparative guard was then added.

For claims containing an explicit comparative relationship, such as:

* outperform
* better than
* worse than
* higher/lower than
* superior/inferior to
* compared to
* improves over
* best performance

the Evidence Agent now checks whether at least one cited comparison row itself contains an explicit comparative relationship.

### Negative cross-row test

The synthetic Transformer-vs-CNN claim cited two individually valid rows that did not state the claimed relationship.

Result:

`unsupported`

Reason:

> The claim makes an explicit comparative assertion, but none of its validated comparison evidence states that comparative relationship.

### Positive comparative tests

Frozen comparison entries containing explicit comparative relationships were correctly detected, including examples involving:

* transfer learning performing better than other methods,
* simultaneous spatial-temporal attention performing better than alternative attention designs,
* dynamic multi-scale temporal fusion outperforming feature concatenation.

These cases remained eligible for Evidence support.

**Key takeaway:** Evidence validation must check not only whether individual evidence rows are valid, but also whether the relationship asserted by a synthesized comparative claim is explicitly represented in the cited evidence.

---

## 9. The complete frozen-baseline pipeline can reach acceptance without revision

The canonical Phase 2 integration run used the frozen Phase 1 comparison data.

### Final validation result

| Metric                       |       Result |
| ---------------------------- | -----------: |
| Claims generated             |        **7** |
| Claims supported by Evidence |    **7 / 7** |
| Critic flags                 |        **0** |
| Revisions                    |        **0** |
| Flags remaining              |        **0** |
| Final status                 | **accepted** |

All seven generated claims passed Evidence validation, and the Critic returned an `accept` decision.

This established the positive path for the integrated pipeline:

**Comparison → Synthesis → Evidence → Critic → Accepted report**

The run also confirmed that the system can reach a clean acceptance state without entering the revision loop when all generated claims are supported.

The Synthesis Agent does not enforce a fixed number of claims; therefore, the number of claims generated is determined by the synthesis output for the given comparison data.

---

## 10. Guard coverage was exercised by the live accepted report

The current accepted seven-claim report was not composed entirely of claims outside the guarded failure modes.

Several accepted claims exercised the relevant evidence paths:

* **claim-005** cites `cmp-032`, `cmp-033`, and `cmp-034`.
* **claim-006** cites `cmp-032` and contains the contrastive term **"whereas"** when comparing reported performance.
* **claim-007** cites `cmp-030` through `cmp-034` and explicitly states that published studies disagree.

This means the accepted report did encounter evidence and language associated with the comparative and disagreement validation mechanisms rather than avoiding those cases entirely.

However, acceptance of claim-007 should not be interpreted as evidence that a genuine cross-publication disagreement was established. The cited frozen disagreement rows were later found to have single-paper provenance, and the stricter two-paper provenance validation produced zero validated genuine disagreement findings.

Therefore, the live run demonstrates that the structural validation mechanisms can process and accept these claim types, but it does not establish the scientific validity of the underlying disagreement conclusion.

---

# PHASE 3 — Revision Loop & Self-Correction

## 11. The revision loop can correct a factual mismatch using real comparison data

The revision loop was first tested with controlled synthetic data to verify the pipeline mechanics.

A separate retry-cap test also confirmed that the system does not continue revising indefinitely.

The most important validation was then performed using the **frozen Phase 1 comparison dataset**.

A controlled Synthesis output contained the following incorrect claim:

> AMDET achieved 99.99% accuracy on the SEED-IV dataset.

The claim cited comparison entry `cmp-012`.

The frozen comparison data instead reports:

**87.32% accuracy**

for the corresponding result, with source evidence from arXiv paper `2212.12134`.

### Revision sequence

The pipeline followed this sequence:

1. **Synthesis** generated the incorrect 99.99% claim.
2. **Evidence** checked the claim against the frozen comparison data.
3. Evidence marked the claim as `unsupported`.
4. **Critic** identified the mismatch and issued a major revision instruction.
5. **Synthesis** revised the claim to the reported **87.32%** value.
6. **Evidence** reran against the full revised draft.
7. Evidence marked the revised claim as `supported`.
8. **Critic** returned `accept`.

### Measured result

| Metric                        |                   Result |
| ----------------------------- | -----------------------: |
| Initial incorrect value       |               **99.99%** |
| Verified value after revision |               **87.32%** |
| Revision count                |                    **1** |
| Claims revised                |                    **1** |
| Flags remaining               |                    **0** |
| Final decision                |               **accept** |
| Final status                  | **revised_and_accepted** |

The revision log recorded:

* claim ID
* original claim
* revised claim
* reason for the flag
* severity
* revision action
* resolved status
* final status

**Key takeaway:** The complete Evidence → Critic → Synthesis loop was able to detect and correct a controlled factual mismatch using the original comparison data.

---

## 12. The revision loop has a hard retry limit

The pipeline was also tested with a scenario where the claim remained unsupported after revision.

The system allows a maximum of **2 revisions**.

If the claim is still flagged after the second revision, the pipeline does not attempt a third revision. Instead, it terminates with:

`shipped_with_flags`

### Retry behavior

| Stage         | Result                 |
| ------------- | ---------------------- |
| Initial draft | Flagged                |
| Revision 1    | Still flagged          |
| Revision 2    | Still flagged          |
| Revision 3    | **Not attempted**      |
| Final outcome | **shipped_with_flags** |

**Key takeaway:** The revision mechanism has a defined failure state instead of assuming that every claim can eventually be repaired automatically.

---

## 13. Every revision is rechecked against the full current draft

The implemented revision process does not simply modify a flagged sentence and accept it immediately.

After each revision:

**Synthesis → Evidence → Critic**

is executed again against the resulting draft.

This means a revision must pass the same verification process as the initial draft.

The revision log also preserves the before/after state of the changed claim, making the correction auditable.

The shared-baseline agreement with Ayush established that the frozen dataset would remain unchanged during Phase 2/3. The available agreement does not separately document a decision with Ayush about flagged-only versus full-draft retry scope; the full-draft recheck described here is therefore an **implemented pipeline behavior**, rather than a separately documented collaboration decision.

**Key takeaway:** A revision is treated as a new draft requiring verification, rather than as an automatically trusted correction.

---

# Overall Findings

## 14. The main engineering lesson: generation and verification should be separate

Across the experiments, the same pattern appeared repeatedly:

**LLM generation can produce useful research claims, but plausibility is not enough to establish factual support.**

The pipeline therefore separates responsibilities:

| Agent         | Main responsibility                       |
| ------------- | ----------------------------------------- |
| Planner       | Break down the research question          |
| Retrieval     | Find relevant papers                      |
| Analysis      | Extract structured findings               |
| Comparison    | Combine findings into a common structure  |
| Synthesis     | Generate the research report              |
| Evidence      | Verify claims against structured evidence |
| Critic        | Identify unsupported or overstated claims |
| Revision loop | Correct flagged claims or ship with flags |

This separation makes it possible to test and improve each stage independently.

---

## 15. Evidence verification needs both semantic and structural checks

The validation experiments showed that semantic verification alone is insufficient for certain claim types.

Different classes of claims require different structural checks:

| Claim type                 | Additional validation                                       |
| -------------------------- | ----------------------------------------------------------- |
| Standard factual claim     | Validate cited comparison evidence                          |
| Disagreement claim         | Require disagreement-marked evidence                        |
| Explicit comparative claim | Require explicit comparative relationship in cited evidence |
| Revised claim              | Re-run Evidence and Critic against the full current draft   |

This makes the Evidence Agent more than an LLM-based plausibility checker. It combines model-based verification with deterministic constraints derived from the structured comparison schema.

**Key takeaway:** The strongest verification behavior came from combining LLM reasoning with deterministic validation rules targeted at known failure modes.

---

## 16. Current system-level validation summary

The major validation results obtained so far are:

| Validation                                 |         Result | Type       |
| ------------------------------------------ | -------------: | ---------- |
| Initial retrieval corpus                   |  **58 papers** | Real       |
| Filtered canonical corpus                  |  **22 papers** | Real       |
| Frozen comparison rows                     |         **34** | Real       |
| Current canonical Phase 2 claims           |          **7** | Real       |
| Current canonical Phase 2 supported claims |      **7 / 7** | Real       |
| Current canonical Phase 2 Critic flags     |          **0** | Real       |
| Controlled revision test                   | **1 revision** | Controlled |
| Incorrect value in revision test           |     **99.99%** | Controlled |
| Verified value after revision              |     **87.32%** | Controlled |
| Claims revised                             |          **1** | Controlled |
| Flags remaining after revision             |          **0** | Controlled |
| Maximum revisions allowed                  |          **2** | Controlled |
| Third revision attempted                   |         **No** | Controlled |
| Synthetic cross-row comparative claim      |   **Rejected** | Synthetic  |
| Comparative guard regression               |     **Passed** | Controlled |
| Disagreement negative guard                |     **Passed** | Synthetic  |
| Disagreement structural positive test      |     **Passed** | Synthetic  |

---

## 17. What these experiments demonstrate

The current experiments demonstrate that the system can:

* reduce domain noise before downstream processing,
* maintain a frozen evidence baseline,
* generate structured research claims,
* validate claims against the original comparison data,
* detect disagreement claims that lack structurally marked disagreement evidence,
* detect unsupported synthesized comparative relationships,
* detect and correct a controlled factual mismatch,
* issue targeted revision instructions,
* re-run verification after revision,
* record the complete revision history,
* and terminate safely when repeated revisions fail.

The system is therefore not relying on a single LLM call to produce the final research result.

Instead, the current design uses a pipeline in which **generation, evidence verification, criticism, and revision are separate stages with explicit handoffs and deterministic checks where appropriate.**

---

## Current Limitations

These findings should not be interpreted as proof that the system produces universally correct research reports.

The current validation has several limitations:

1. The revision test uses a **controlled injected error** rather than an organically discovered error from an unrestricted research run.
2. The canonical Phase 2 acceptance test used a relatively small frozen comparison dataset of **34 rows**.
3. Retrieval is currently based on the **arXiv API**, so the corpus does not represent the entire published literature.
4. The EEG domain filter is rule-based and may still allow irrelevant papers or exclude relevant papers.
5. The current tests establish pipeline behavior and verification mechanics, but not yet the overall scientific superiority of Transformer-based approaches over CNN/RNN approaches.
6. The current disagreement validation establishes the **structural enforcement mechanism**, but the frozen baseline does not provide sufficient evidence to establish a genuine cross-publication disagreement. The corrected disagreement analysis currently produces no validated disagreement findings.
7. The comparative guard addresses a specific failure mode: it prevents a claim from being supported solely by combining separate rows that do not explicitly state the claimed relationship. It does not prove that every possible multi-row inference is scientifically valid.
8. Retrieval robustness, API failures, and rate-limit handling still require dedicated robustness testing.
9. System-level evaluation against external research or human-verified baselines has not yet been completed.
10. The frozen baseline is a **historical validation fixture**. Later retrieval and analysis improvements should be evaluated as separate experiments rather than silently replacing the baseline used for Phase 2/3 validation.

These limitations define the next stage of evaluation rather than invalidating the current pipeline tests.
