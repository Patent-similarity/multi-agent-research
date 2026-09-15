"""
Agent 1 — Planner

Job: take the LOCKED research question + the LOCKED 5-way decomposition
(phase0/decomposition.json) and produce 1-3 concrete arXiv search_terms per
sub-question, matching phase0/schemas/planner_to_retrieval.json exactly.

What this agent does NOT do:
- It does NOT invent sub-questions. The 5 IDs and their `question` text are
  locked in decomposition.json. Planner only adds `search_terms`.
- It does NOT decide dedup, retrieval count, or date filtering — that's
  Agent 2 (Retrieval)'s job, guided by retrieval_spec.md.

Run:
    python agent1_planner.py
Output:
    phase1/output/planner_output.json  (validated against planner_to_retrieval.json)
"""
import json
import os
import re
from pathlib import Path

from google import genai
from google.genai import types
from dotenv import load_dotenv

from validate import validate_or_raise

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent
PHASE0 = REPO_ROOT / "phase0"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# gemini-2.5-flash was retired for new users (per Google's own 404 message).
# Model names/free-tier limits change fast on Google's side — check
# https://aistudio.google.com if this stops working again.
MODEL = "gemini-3.6-flash"


def load_locked_research_question() -> str:
    """Extract the locked question from the (possibly multi-line) blockquote
    in research_question.md. Grabs the first contiguous run of '>' lines."""
    text = (PHASE0 / "research_question.md").read_text(encoding="utf-8")
    lines = text.splitlines()

    quote_lines = []
    in_quote = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(">"):
            in_quote = True
            quote_lines.append(stripped.lstrip(">").strip())
        elif in_quote:
            break  # first contiguous blockquote block ended

    question = " ".join(quote_lines).replace("**", "").strip()
    if not question:
        raise ValueError("Could not extract locked research question from research_question.md")
    return question


def load_decomposition() -> list[dict]:
    data = json.loads((PHASE0 / "decomposition.json").read_text(encoding="utf-8"))
    return data["sub_questions"]


def load_retrieval_spec_text() -> str:
    """Passed to the LLM as grounding context for what concepts belong to each sub-question."""
    return (PHASE0 / "retrieval_spec.md").read_text(encoding="utf-8")


def build_prompt(research_question: str, sub_questions: list[dict], spec_text: str) -> str:
    sub_q_block = "\n".join(f"- id: {sq['id']}\n  question: {sq['question']}" for sq in sub_questions)
    return f"""You are the Planner agent in a locked research pipeline. Your ONLY job is
to generate 1-3 concrete arXiv search query strings (`search_terms`) for each
of the five FIXED sub-questions below. Do not add, remove, reorder, or rename
sub-questions. Do not restate the sub-question text as a search term — write
actual arXiv-style search strings (short concept phrases, not full sentences).

LOCKED RESEARCH QUESTION:
{research_question}

FIXED SUB-QUESTIONS (id + question, do not modify):
{sub_q_block}

RETRIEVAL SPEC (concept sets to ground your search_terms in — use these, don't invent unrelated concepts):
{spec_text}

Respond with ONLY a JSON object matching this exact shape, no markdown fences, no preamble:
{{
  "research_question": "<the locked research question, verbatim>",
  "sub_questions": [
    {{"id": "approaches", "question": "<verbatim from above>", "search_terms": ["...", "..."]}},
    ... (all 5, in the same order as above)
  ]
}}
"""


def strip_code_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def call_planner_llm(prompt: str) -> dict:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.3,
            max_output_tokens=2000,
            # Ask Gemini to return raw JSON directly — removes most of the
            # markdown-fence-stripping fragility you'd otherwise deal with.
            response_mime_type="application/json",
        ),
    )
    raw_text = response.text
    cleaned = strip_code_fences(raw_text)
    return json.loads(cleaned)


def run() -> dict:
    research_question = load_locked_research_question()
    sub_questions = load_decomposition()
    spec_text = load_retrieval_spec_text()

    prompt = build_prompt(research_question, sub_questions, spec_text)

    payload = None
    last_error = None
    for attempt in range(2):  # one retry if the LLM returns malformed/invalid JSON
        try:
            payload = call_planner_llm(prompt)
            validate_or_raise(payload, "planner_to_retrieval.json")
            break
        except Exception as e:  # noqa: BLE001 — deliberately broad, we retry once then surface
            last_error = e
            payload = None
            continue

    if payload is None:
        raise RuntimeError(f"Planner failed after retry. Last error: {last_error}")

    out_path = OUTPUT_DIR / "planner_output.json"
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Planner output written to {out_path}")
    print(json.dumps(payload, indent=2))
    return payload


if __name__ == "__main__":
    run()