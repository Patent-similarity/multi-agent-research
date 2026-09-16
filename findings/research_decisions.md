# Research Decisions

## PHASE 1

---

### Decision 1 — Keep synthesis and verification separate

Synthesis generates the research draft, while Evidence independently checks
claims against the Comparison data and Critic evaluates the verification
results.

**Reason:** The initial Synthesis test showed that prompt instructions alone
do not guarantee factual grounding.

---

### Decision 2 — Use a shared Gemini client

Synthesis, Evidence, and Critic will use the shared `LLMClient` abstraction
rather than creating separate API clients.

**Reason:** The agents are logically separate but do not require separate
LLM clients or API keys.