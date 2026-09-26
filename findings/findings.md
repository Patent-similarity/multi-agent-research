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
| ----------------------------- | -----------: |
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

Therefore, this historical run demonstrates that the structural validation mechanisms *existing at that time* could process and accept these claim types, but it does not establish the scientific validity of the underlying disagreement conclusion.

**This gap has since been closed.** See item 16 (fresh live end-to-end run): under the current Evidence Agent, an equivalent claim citing the same disagreement rows was independently generated by Synthesis, correctly flagged as unsupported, and removed by the revision loop — on a live, unstubbed run.

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
| ------------------------------ | -----------------------: |
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
| -------------- | ---------------------- |
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

# PHASE 2/3 — Guard Correction & Provenance Validation

*(This section covers corrections to the disagreement/comparative guards introduced during Phase 2/3 verification-loop work. It is grouped separately from Phase 4 below, which covers infrastructure-level robustness — API failures, malformed responses, and pipeline-orchestration bugs — a distinct category of work on a different part of the system.)*

## 14. Agent 3 disagreement extraction was tightened using provenance validation

The Evidence Agent's disagreement guard exposed that the frozen baseline contained several disagreement-marked rows whose evidence came from only one paper (`cmp-030` through `cmp-034`).

This led to an upstream correction in Agent 3: the disagreement extraction rule was tightened so that a disagreement finding requires an explicit cross-paper conflict involving at least **two distinct sources**.

The corrected Agent 3 output was regenerated separately from the frozen baseline:

| Experimental disagreement output | Result |
| ---------------------------------- | -----: |
| Disagreement findings             |  **0** |
| Comparison rows                   | **29** |
| Rows marked as disagreements      |  **0** |

This result should not be interpreted as proof that no disagreement exists in the published literature — only that the current retrieval/analysis evidence did not produce a finding satisfying the stricter cross-paper rule.

**Key takeaway:** When an evidence-verification test exposes a provenance problem, the appropriate fix may need to occur upstream in evidence extraction rather than only downstream in claim verification.

---

## 15. The current Evidence Agent correctly re-evaluates the historical claim-007 case

A regression test was constructed by loading the frozen comparison data, reconstructing the historical claim-007 (which cites `cmp-030` through `cmp-034` and asserts a published disagreement), instantiating the actual `EvidenceAgent`, and calling `check()` directly — the real validation code path, not an isolated row-level check.

Under the current Evidence Agent, this same claim flips from `supported` (the historical result) to `unsupported`, because the cited disagreement rows do not have the required two distinct arXiv sources.

| Validation                                                      |     Result |
| ----------------------------------------------------------------- | ---------: |
| Disagreement negative guard                                       | **Passed** |
| Disagreement positive structural test                             | **Passed** |
| Frozen disagreement guard (historical claim-007, current code)    | **Passed** |
| Comparative guard positive case                                   | **Passed** |
| Comparative guard negative case                                   | **Passed** |

**Key takeaway:** The fix was confirmed against the actual historical failure case using the real Evidence Agent code path, not just a newly written synthetic test.

---

## 16. A fresh live end-to-end run confirmed the fix on organically-generated output

A complete live pipeline run was then executed against the frozen 22-paper / 34-row baseline, using the current (post-fix) Synthesis, Evidence, and Critic agents with real Gemini calls — no stubs, no injected errors.

Synthesis generated a claim, independently and without prompting toward any particular failure mode, that asserted published disagreement across multiple methodological paradigms and cited `cmp-030` through `cmp-034` as support:

> "Published studies disagree on key methodological paradigms, including transfer learning superiority versus alternative ML methods, simultaneous versus sequential/single-dimension spatial-temporal attention, dynamic temporal scale fusion versus concatenation across classification granularities, high-density electrode reliance versus radical channel reduction, and short segment-based versus long-term trial-based continuous processing."

### Result

| Stage        | Result |
| ------------- | ------ |
| Evidence     | Marked the claim `unsupported` — cited comparison findings lack verification from multiple distinct sources required to establish cross-study disagreement |
| Critic       | Flagged the claim (severity: major), decision: `revise` |
| Synthesis    | Revised the claim by removing it entirely (`revision_action: remove`) |
| Re-check     | Confirmed resolved on the revised draft |
| Final status | `revised_and_accepted` |

This is the strongest available evidence for the disagreement guard: the failure mode was not injected or synthetically constructed for this test. It emerged from an unconstrained live Synthesis call, was independently caught by Evidence, correctly actioned by Critic, and cleanly resolved by Synthesis — all on the real frozen baseline, in one continuous automated run.

**Key takeaway:** The verification loop was demonstrated to catch and correct an organically-generated overclaim, not only a controlled, hand-injected one. This directly strengthens the project's central claim: the system is not relying on Synthesis alone to produce a trustworthy report.

---

# PHASE 4 — Robustness & Failure-Mode Hardening

## 17. LLM API calls now retry transient failures with bounded backoff

`GeminiClient.complete()` previously had no error handling at all — any network failure, timeout, or transient server error (5xx, 429) propagated straight up and crashed the entire pipeline run mid-call, with no distinction between a failure worth retrying and one that never would succeed.

A retry classifier was added (`_is_retryable_error`) that checks both structured status codes and transient-failure text patterns (timeout, rate limit, service unavailable, etc.) before deciding whether to retry. Non-retryable failures (e.g. a bad API key, a malformed request) fail immediately rather than wasting retry attempts on a guaranteed repeat failure. The retry/backoff schedule reuses the same `API_RETRY_WAIT` pattern already used by Agent 2's retrieval robustness code, rather than inventing a second scheme.

Tested with a deterministic fake API stub (no live Gemini calls, no real network dependency):

| Validation                                                              |     Result |
| -------------------------------------------------------------------------- | ---------: |
| Transient failure retried, succeeds on next attempt                       | **Passed** |
| All retries exhausted → raises with attempt count                         | **Passed** |
| Non-retryable failure fails immediately, no retry                         | **Passed** |
| Transient failure succeeds on the final allowed attempt (boundary case)   | **Passed** |

**Key takeaway:** Retry logic needs to distinguish retryable from non-retryable failures explicitly — retrying blindly on any exception wastes quota on failures that will never succeed.

---

## 18. Malformed LLM JSON output is now a distinct, catchable error type

`parse_json_response()` previously let a raw `json.JSONDecodeError` propagate on genuinely malformed (not just code-fenced) output, with no context on which agent or call produced it. It now raises a dedicated `LLMResponseParseError`, distinguishable from a structurally-valid-but-semantically-wrong response.

**Key takeaway:** Distinguishing "the LLM didn't return JSON at all" from "the LLM returned JSON with the wrong shape" from "the LLM returned a well-formed but unsupported claim" matters — these are three different failure modes and the pipeline needs to be able to tell them apart.

---

## 19. Deterministic structural validation rejects malformed agent responses before they reach pipeline logic

Each of Synthesis, Evidence, and Critic now validates the shape of its own LLM response before returning it — rejecting missing fields, wrong types, invalid enum values (e.g. an Evidence status outside `supported`/`partially_supported`/`unsupported`), and, for Critic, flags referencing a `claim_id` that doesn't exist in the draft.

Each agent's malformed-response coverage was tested against a set of deliberately broken response shapes (9 cases each for Evidence and Critic), confirming every malformed case is rejected with a clear `ValueError` rather than silently propagating bad data downstream.

**Key takeaway:** Structural validation belongs at the agent boundary, not downstream in the pipeline — catching a malformed response at the source makes the failure easier to diagnose than letting it surface as a confusing error several steps later.

---

## 20. A partial-resolution bug in the revision loop was found and fixed

The pipeline's two terminal branches (accept, and retry-cap reached) originally updated every row in the run's revision log in one blanket pass:

```python
if critic_result["decision"] == "accept":
    for row in revision_rows:
        row["resolved"] = True
        ...
if revision_number == 2:
    for row in revision_rows:
        row["resolved"] = False
        row["final_status"] = "shipped_with_flag"
```

This is correct for the accept branch, but wrong for the retry-cap branch: it marks **every** row in the run as `shipped_with_flag`, including claims that were genuinely fixed at an earlier revision and never flagged again. In a run where `claim_001` resolves after revision 1 but `claim_002` never resolves, the old code would mislabel `claim_001` as unresolved too — corrupting not just that one row, but the run-level `flags_remaining` count derived from it, which is exactly the number the Phase 5 frontend's "X of Y claims revised" stat depends on.

**Why existing tests missed this:** every pipeline/revision test prior to this fix (`test_pipeline_revision_manual`, `test_pipeline_real_revision_manual`, `test_pipeline_ship_flags_manual`, `test_revision_handoff_manual`) used exactly one `claim_id` per run. A single-claim scenario cannot expose a bug that only manifests when different claims have different outcomes in the same run.

**Fix:** row resolution is now tracked per-claim at each iteration — a row is marked `resolved`/`revised` as soon as its `claim_id` stops appearing in a subsequent Critic pass, and only rows whose `claim_id` is still present in the *final* flagged set are marked `shipped_with_flag` when the retry cap is reached.

A new regression test (`test_pipeline_partial_resolution_manual.py`) exercises exactly this scenario: two claims flagged initially, one resolves after revision 1, the other remains flagged through the cap. The test confirms `claim_001`'s row is `resolved: true, final_status: "revised"` and `claim_002`'s rows are `shipped_with_flag`, with `flags_remaining == 1` — the correct count, not the `2` the old bug would have produced.

**Known limitation of the fix's coverage:** a three-claim scenario where two different claims resolve at two different revision numbers was checked by manual code inspection, not by an automated test. The fix's logic generalizes correctly on inspection, but this is a weaker claim than test-verified coverage, and is noted here rather than implied as fully covered.

**Key takeaway:** A bug can hide indefinitely behind a test suite that only ever exercises the simplest version of a scenario. Multi-entity partial-outcome cases are exactly where blanket-update logic breaks, and are worth testing explicitly rather than assuming single-entity tests generalize.

---

## 21. Guard coverage was extended: implicit comparative claims and semantic action validation

Two gaps identified during the Phase 4 audit were closed:

**Implicit comparative detection (Agent 6).** The original comparative guard only matched explicit comparative language ("outperforms," "better than," etc.). It missed the exact motivating case from item 2 — two models' results stated side by side with different percentages and no comparative keyword at all (e.g. "a Transformer achieving 86% accuracy versus a CNN achieving 76%"). A quantitative pattern was added to detect two or more model-plus-percentage mentions in a single claim, closing this gap without weakening the guard's core requirement — a claim still only counts as supported if a **single cited comparison row** independently states the comparative relationship, so a synthesized cross-row comparison still correctly fails.

**Semantic `allowed_action` validation (Agent 7).** Critic's structural validation previously confirmed `allowed_action` was one of `rewrite`/`weaken`/`remove`, but not that the chosen action made sense given Evidence's verdict — nothing stopped Critic from choosing `weaken` for a claim Evidence marked fully `unsupported` with zero evidence, when only `remove` is defensible. A semantic check was added directly inside `CriticAgent.evaluate()`, rejecting an `unsupported` claim paired with any `allowed_action` other than `remove`, immediately after parsing Critic's own response — before it can propagate into revision instructions.

| Validation                                          |     Result |
| ----------------------------------------------------- | ---------: |
| Implicit comparative claim (no keyword) now detected | **Passed** |
| Explicit-keyword comparative detection unaffected     | **Passed** |
| `unsupported` + non-`remove` action rejected          | **Passed** |
| Valid Critic responses unaffected                     | **Passed** |

**Key takeaway:** Structural validation (does the response have the right shape) and semantic validation (does the response make sense given the evidence) are different checks. Both are needed — the first catches malformed output, the second catches internally-consistent-but-wrong output.

---

## 22. Synthesis revision preserves the original draft state

A focused regression test was added for `SynthesisAgent.revise()` to verify that applying a revision does not mutate the original draft object.

The test creates a deep copy of the original draft, performs a revision using a deterministic fake LLM response, and then verifies that:

* the original draft remains unchanged,
* the revised draft preserves the original `draft_id`,
* the revised draft preserves the original `research_question`,
* and the revision produces exactly one LLM call.

### Validation

| Validation                                   |     Result |
| -------------------------------------------- | ---------: |
| Original draft remains unchanged             | **Passed** |
| `draft_id` preserved after revision          | **Passed** |
| `research_question` preserved after revision | **Passed** |
| Revision call count                          | **Passed** |

The regression is covered by:

`test_synthesis_revise_idempotence_manual.py`

This test verifies the non-mutation and contract-preservation behavior of `revise()`. It does **not** claim mathematical idempotence of repeated LLM generations, since separate LLM calls are not expected to produce byte-identical outputs.

**Key takeaway:** Revision should produce a new validated draft state without mutating the previous draft, while preserving the identifiers and research context needed to track the revision correctly.


---

# Overall Findings

## 23. The main engineering lesson: generation and verification should be separate

Across the experiments, the same pattern appeared repeatedly:

**LLM generation can produce useful research claims, but plausibility is not enough to establish factual support.**

The pipeline therefore separates responsibilities:

| Agent         | Main responsibility                       |
| -------------- | ------------------------------------------ |
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

## 24. Evidence verification needs both semantic and structural checks

The validation experiments showed that semantic verification alone is insufficient for certain claim types.

Different classes of claims require different structural checks:

| Claim type                  | Additional validation                                       |
| ----------------------------- | ------------------------------------------------------------- |
| Standard factual claim      | Validate cited comparison evidence                          |
| Disagreement claim          | Require disagreement-marked evidence                        |
| Explicit comparative claim  | Require explicit comparative relationship in cited evidence |
| Implicit comparative claim  | Require quantitative multi-entity pattern detection, same evidentiary bar as explicit |
| Revised claim               | Re-run Evidence and Critic against the full current draft   |
| Malformed/failed API response | Reject via structural validation or retry before reaching pipeline logic |

This makes the Evidence Agent more than an LLM-based plausibility checker. It combines model-based verification with deterministic constraints derived from the structured comparison schema.

**Key takeaway:** The strongest verification behavior came from combining LLM reasoning with deterministic validation rules targeted at known failure modes.

---

## 25. Current system-level validation summary

The major validation results obtained so far are:

| Validation                                                              |          Result | Type         |
| --------------------------------------------------------------------------- | ---------------: | ------------ |
| Initial retrieval corpus                                                | **58 papers**    | Real         |
| Filtered canonical corpus                                               | **22 papers**    | Real         |
| Frozen comparison rows                                                  | **34**           | Real         |
| Historical canonical Phase 2 claims                                     | **7**            | Real         |
| Historical canonical Phase 2 supported claims                           | **7 / 7**        | Real         |
| Controlled revision test                                                | **1 revision**   | Controlled   |
| Incorrect value in revision test                                        | **99.99%**       | Controlled   |
| Verified value after revision                                           | **87.32%**       | Controlled   |
| Maximum revisions allowed                                               | **2**            | Controlled   |
| Third revision attempted                                                | **No**           | Controlled   |
| Synthetic cross-row comparative claim                                   | **Rejected**     | Synthetic    |
| Comparative guard regression                                            | **Passed**       | Controlled   |
| Disagreement negative guard                                             | **Passed**       | Synthetic    |
| Corrected disagreement analysis findings                                | **0**            | Experimental |
| Corrected experimental comparison rows                                  | **29**           | Experimental |
| Frozen disagreement guard (historical claim-007, current code)          | **Passed**       | Controlled   |
| **Fresh live end-to-end run**                                           | **Completed**    | **Real**     |
| **Organically-generated disagreement overclaim caught**                 | **Yes**          | **Real**     |
| **Revision result (live run)**                                          | **`revised_and_accepted`** | **Real** |
| LLM transient retry test                                                | **Passed**       | Controlled   |
| LLM exhausted-retry test                                                 | **Passed**       | Controlled   |
| LLM non-retryable failure test                                          | **Passed**       | Controlled   |
| LLM retry-boundary (success on final attempt)                           | **Passed**       | Controlled   |
| Malformed JSON → `LLMResponseParseError`                                | **Passed**       | Controlled   |
| Structural validation (Synthesis/Evidence/Critic, 9 malformed cases each) | **Passed**      | Controlled   |
| Partial-resolution regression (2-claim staggered outcome)               | **Passed**       | Controlled   |
| Implicit comparative detection                                          | **Passed**       | Controlled   |
| Semantic `allowed_action` rejection                                     | **Passed**       | Controlled   |
| Synthesis `revise()` non-mutation / ID preservation                     | **Passed**       | Controlled   |

---

## 26. What these experiments demonstrate

The current experiments demonstrate that the system can:

* reduce domain noise before downstream processing,
* maintain a frozen evidence baseline,
* generate structured research claims,
* validate claims against the original comparison data,
* detect disagreement claims that lack structurally marked disagreement evidence,
* detect unsupported synthesized comparative relationships, both explicit and implicit,
* detect and correct a controlled factual mismatch,
* issue targeted revision instructions,
* re-run verification after revision,
* record the complete revision history accurately even when different claims in the same run have different outcomes,
* retry transient API failures with bounded backoff,
* reject malformed or semantically unsafe agent output at the source,
* and terminate safely when repeated revisions fail.

The system is therefore not relying on a single LLM call to produce the final research result.

Instead, the current design uses a pipeline in which **generation, evidence verification, criticism, and revision are separate stages with explicit handoffs and deterministic checks where appropriate.**

---

## 27. Paper-to-evidence conversion rate

Of the 22 canonical papers in the frozen baseline, 20 contributed evidence to at least one comparison row. The remaining 2 papers passed the domain-filtering stage (Agent 2's EEG relevance check) but did not contribute an extractable comparison finding during Analysis.

This is not treated as a retrieval failure — both papers were legitimately on-topic and correctly retained by the domain filter. It is instead a useful observation about the conversion rate from retrieved-and-filtered papers to structured comparison evidence: not every retained paper's abstract yields a finding that fits the locked comparison schema.

**Key takeaway:** Passing the domain filter and contributing to the final comparison output are two different bars. Tracking the gap between them is a reasonable input for Phase 5 reporting on corpus utilization.

---

## Current Limitations

These findings should not be interpreted as proof that the system produces universally correct research reports.

The current validation has several limitations:

1. ~~The revision test uses a controlled injected error rather than an organically discovered error from an unrestricted research run.~~ **Partially resolved:** the fresh live end-to-end run (item 16) caught and corrected an organically-generated overclaim (an unprompted disagreement claim citing single-source rows), not an injected one. The earlier controlled test (AMDET/99.99%) remains useful as a precise, reproducible mechanics check, but is no longer the only evidence of the loop working on real failures.
2. The canonical Phase 2 acceptance test used a relatively small frozen comparison dataset of **34 rows**.
3. Retrieval is currently based on the **arXiv API**, so the corpus does not represent the entire published literature.
4. The EEG domain filter is rule-based and may still allow irrelevant papers or exclude relevant papers.
5. The current tests establish pipeline behavior and verification mechanics, but not yet the overall scientific superiority of Transformer-based approaches over CNN/RNN approaches.
6. The current disagreement validation establishes the **structural enforcement mechanism**, and this has now been confirmed both by regression testing against the historical failure case (item 15) and by a live end-to-end run (item 16). The frozen baseline still does not provide sufficient evidence to establish a genuine cross-publication disagreement, and the corrected disagreement analysis currently produces no validated disagreement findings — the guard's job is to prevent such a claim from shipping unflagged, which it now does.
7. The comparative guard addresses a specific failure mode: it prevents a claim from being supported solely by combining separate rows that do not explicitly state the claimed relationship. It does not prove that every possible multi-row inference is scientifically valid.
8. API failure handling, retry/backoff, and malformed-response handling for Agents 5–7 (Synthesis, Evidence, Critic) is now implemented and covered by deterministic tests (see items 17–21). Agent 2 (Retrieval) API-failure and rate-limit robustness remains a separate, not-yet-independently-validated item on Ayush's side of Phase 4.
9. System-level evaluation against external research or human-verified baselines has not yet been completed.
10. The frozen baseline is a **historical validation fixture**. Later retrieval and analysis improvements should be evaluated as separate experiments rather than silently replacing the baseline used for Phase 2/3 validation.
11. The partial-resolution fix (item 20) is verified by test for a 2-claim staggered-outcome scenario and confirmed correct for a 3+-claim scenario by manual code inspection only, not by an automated test.
12. The implicit-comparative regex pattern (item 21) uses a lazy 100-character window between a model keyword and a percentage value, which could in principle match across two unrelated sentences in an unusually dense claim. Not observed in practice, but not structurally impossible.

These limitations define the next stage of evaluation rather than invalidating the current pipeline tests.