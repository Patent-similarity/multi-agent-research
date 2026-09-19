# Research Findings

## PHASE 1

---

### Finding 1 — LLM grounding instructions are not sufficient on their own

During the initial Synthesis Agent test, Gemini generated placeholder
performance values such as `XX%` and `YY%` even though the prompt explicitly
prohibited invented performance values.

After strengthening the prompt, the behavior disappeared.

**Implication:** Synthesis should not be treated as the final factual
verification layer. Independent Evidence and Critic agents remain necessary.

---

### Finding 2 — A shared Gemini client can serve multiple logical agents

The Synthesis Agent successfully used the shared `GeminiClient` abstraction.
This supports using one Gemini client/API key across the Synthesis, Evidence,
and Critic agents while keeping them as separate logical agents.

Finding — LLM evidence verification can trust malformed comparison data.
During malformed-input testing, the Evidence Agent initially marked a 99% performance claim as supported even though the comparison row had no valid source evidence. Adding deterministic validation downgraded the claim to unsupported and removed the invalid evidence reference.

## Current Findings

### 1. LLM-generated synthesis can create comparative claims that are not explicitly stated in individual source claims

During synthesis testing, the model generated a comparative statement such as a Transformer achieving 86% versus a CNN achieving 76%, even though that exact comparison was not directly stated as a single source claim.

This shows that synthesis can derive relationships between comparison rows rather than simply restating source claims. Therefore, downstream Evidence and Critic verification is necessary to distinguish supported synthesis from unsupported inference.

### 2. Prompt-level grounding alone is not sufficient to guarantee factual synthesis

An early Synthesis test produced placeholder/invented performance information despite explicit instructions not to invent performance values. Strengthening the synthesis prompt reduced this behavior, but the test demonstrated that prompt instructions alone cannot be treated as a verification mechanism.

This supports the use of an independent Evidence → Critic verification stage before accepting the final report.


## Finding: Broad arXiv retrieval produced substantial domain noise

The initial arXiv retrieval queries produced papers that matched generic query terms but were not actually about EEG-based emotion recognition. Examples included EMERSK, SAFER, and EMOVOME, as well as unrelated papers such as DEAP-3600 (dark matter detector) and Seed-Coder (LLM research).

A hard post-retrieval domain filter was therefore added to Agent 2. A paper is retained only when:
- "EEG" or "electroencephalog..." appears in the title, or
- the EEG term appears at least twice in the abstract.

Agent 3 also applies an explicit domain check as a second layer of protection.

After regenerating the retrieval and analysis outputs, the canonical paper set decreased from **58 to 22 papers**. The specific false-positive case EMERSK was also confirmed to have zero occurrences in the regenerated `comparison_output.json`.

This demonstrates that keyword-based arXiv retrieval alone was insufficient for this research question and required domain-specific filtering before downstream analysis and comparison.