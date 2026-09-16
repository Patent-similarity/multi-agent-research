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