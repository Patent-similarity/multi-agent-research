"""
Agent 3 — Analysis

Job: for one sub-question's retrieved papers (retrieval_<id>.json), read
each paper's abstract and extract structured "findings" (claims) relevant
to that sub-question's question, matching
phase0/schemas/analysis_to_comparison.json exactly.

Hard invariants from the schema (do not relax these):
- A finding must NOT contain a reported_value unless the abstract itself
  actually states that number. No inferring/estimating performance figures.
- dataset/approach/architecture: null when missing, NEVER empty string.
- Every finding needs >=1 evidence entry with a real arxiv_id from the
  input papers and source_text that is an actual (short) quote/paraphrase
  grounding the claim — not invented.
- claim_id must be unique. We assign these programmatically after the LLM
  call rather than trusting the model to generate collision-free IDs.

We batch ALL papers for one sub-question into a single LLM call (not one
call per paper) — much friendlier to Gemini's free-tier rate limits, and
still gives the model enough context to catch cross-paper patterns like
the same dataset appearing in multiple studies.

Run:
    python agent3_analysis.py <sub_question_id>
    python agent3_analysis.py --all          # runs all 5 sequentially, paced

Reads:
    phase1/output/retrieval_<sub_question_id>.json
Writes:
    phase1/output/analysis_<sub_question_id>.json   (validated)
"""
import json
import os
import re
import sys
import time
from pathlib import Path

from google import genai
from google.genai import types
from dotenv import load_dotenv

from validate import validate_or_raise, check_no_empty_strings_where_null_expected

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent
PHASE0 = REPO_ROOT / "phase0"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

MODEL = "gemini-3.6-flash"
SUB_QUESTION_IDS = ["approaches", "datasets", "architectures", "metrics", "disagreements"]
SECONDS_BETWEEN_CALLS = 4.0  # pacing for free-tier rate limits when running --all


def strip_code_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def load_decomposition_question(sub_question_id: str) -> str:
    data = json.loads((PHASE0 / "decomposition.json").read_text(encoding="utf-8"))
    for sq in data["sub_questions"]:
        if sq["id"] == sub_question_id:
            return sq["question"]
    raise ValueError(f"Unknown sub_question_id: {sub_question_id}")


def build_prompt(sub_question_id: str, question_text: str, papers: list[dict]) -> str:
    papers_block = "\n\n".join(
        f"[Paper arxiv_id={p['arxiv_id']}]\n"
        f"Title: {p['title']}\n"
        f"Abstract: {p['abstract']}"
        for p in papers
    )
    return f"""You are the Analysis agent in a locked research pipeline. Extract
structured findings (claims) from the paper abstracts below that are
relevant to answering this sub-question:

SUB-QUESTION ({sub_question_id}): {question_text}

STRICT RULES:
1. Only extract claims actually supported by the abstract text given. Do
   not infer, guess, or fill in numbers/facts not present in the abstract.
2. If a claim mentions a numeric result (accuracy, F1, etc.), it MUST be a
   number that literally appears in that paper's abstract. If the abstract
   gives no numbers, reported_values must be an empty array — do not
   invent a plausible-sounding number.
3. Every finding needs at least one evidence entry: the arxiv_id of the
   source paper (must match one of the arxiv_ids given below, verbatim)
   and source_text (a short quote or close paraphrase from that abstract
   grounding the claim — a few words to one sentence, not the whole abstract).
4. dataset / approach / architecture: use null (JSON null) if the abstract
   doesn't specify it. NEVER use an empty string "" for missing values.
5. confidence: "high" if the abstract states this directly and
   unambiguously, "medium" if it's a reasonable reading but not fully
   explicit, "low" if it's a weak/indirect signal.
6. It's fine to extract 0 findings from a paper if its abstract has
   nothing relevant to this specific sub-question — don't force it.
7. Set claim_id to the string "PLACEHOLDER" for every finding — the
   calling code assigns real unique IDs afterward. Do not try to make
   claim_id unique yourself.

PAPERS:
{papers_block}

Respond with ONLY a JSON object, no markdown fences, no preamble, in this
exact shape:
{{
  "sub_question_id": "{sub_question_id}",
  "findings": [
    {{
      "claim_id": "PLACEHOLDER",
      "claim": "<concise claim text>",
      "evidence": [{{"arxiv_id": "<must match a paper above>", "source_text": "<short quote/paraphrase>"}}],
      "dataset": "<string or null>",
      "approach": "<string or null>",
      "architecture": "<string or null>",
      "metrics": ["<metric name>", ...],
      "reported_values": [{{"metric": "<name>", "value": "<value as it appears in the abstract>"}}],
      "confidence": "high" | "medium" | "low"
    }}
  ]
}}
"""


def call_analysis_llm(prompt: str) -> dict:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,  # low — this is extraction, not creative generation
            max_output_tokens=8000,  # 15 papers' worth of findings needs real headroom
            response_mime_type="application/json",
        ),
    )
    raw_text = response.text
    try:
        cleaned = strip_code_fences(raw_text)
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        # Surface the actual response instead of just "Expecting value" —
        # can't debug a parse failure without seeing what was actually returned.
        preview = raw_text[:500] if raw_text else "(empty response)"
        finish_reason = None
        try:
            finish_reason = response.candidates[0].finish_reason
        except Exception:
            pass
        raise ValueError(
            f"Gemini response wasn't valid JSON (finish_reason={finish_reason}). "
            f"Parse error: {e}\nFirst 500 chars of response:\n{preview}"
        ) from e


def assign_claim_ids(payload: dict, sub_question_id: str) -> dict:
    """Overwrite whatever claim_id the LLM produced with a deterministic,
    guaranteed-unique one. Never trust the model for uniqueness."""
    for i, finding in enumerate(payload.get("findings", []), start=1):
        finding["claim_id"] = f"{sub_question_id}-{i:03d}"
    return payload


def validate_evidence_arxiv_ids(payload: dict, valid_arxiv_ids: set[str]) -> list[str]:
    """Extra guardrail beyond jsonschema: catch the model citing an
    arxiv_id that wasn't actually in the input papers (hallucinated
    evidence source) — jsonschema can't check this, only we can."""
    problems = []
    for finding in payload.get("findings", []):
        for ev in finding.get("evidence", []):
            if ev.get("arxiv_id") not in valid_arxiv_ids:
                problems.append(
                    f"claim_id={finding.get('claim_id')}: evidence cites arxiv_id "
                    f"'{ev.get('arxiv_id')}' which is not among the input papers"
                )
    return problems


def run_for_sub_question(sub_question_id: str) -> dict:
    retrieval_path = OUTPUT_DIR / f"retrieval_{sub_question_id}.json"
    if not retrieval_path.exists():
        raise FileNotFoundError(
            f"{retrieval_path} not found. Run agent2_retrieval.py first "
            f"(or point this at a mock/reused retrieval file with that name)."
        )
    retrieval_data = json.loads(retrieval_path.read_text(encoding="utf-8"))
    papers = retrieval_data["papers"]
    valid_arxiv_ids = {p["arxiv_id"] for p in papers}

    question_text = load_decomposition_question(sub_question_id)
    prompt = build_prompt(sub_question_id, question_text, papers)

    payload = None
    last_error = None
    for attempt in range(2):
        try:
            payload = call_analysis_llm(prompt)
            payload = assign_claim_ids(payload, sub_question_id)

            hallucination_errors = validate_evidence_arxiv_ids(payload, valid_arxiv_ids)
            if hallucination_errors:
                raise ValueError(
                    "Evidence cites arxiv_ids not in the input set:\n  - "
                    + "\n  - ".join(hallucination_errors)
                )

            empty_string_errors = check_no_empty_strings_where_null_expected(
                payload.get("findings", []), ["dataset", "approach", "architecture"]
            )
            if empty_string_errors:
                raise ValueError(
                    "Found empty string where null was expected (schema alone won't "
                    "catch this — it's a load-bearing rule per Phase 0):\n  - "
                    + "\n  - ".join(empty_string_errors)
                )

            validate_or_raise(payload, "analysis_to_comparison.json")
            break
        except Exception as e:  # noqa: BLE001 — retry once, then surface
            last_error = e
            payload = None
            continue

    if payload is None:
        raise RuntimeError(f"Analysis failed for '{sub_question_id}' after retry. Last error: {last_error}")

    out_path = OUTPUT_DIR / f"analysis_{sub_question_id}.json"
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"  -> {len(payload['findings'])} findings extracted. Written to {out_path}")
    return payload


def run_all() -> None:
    for i, sub_question_id in enumerate(SUB_QUESTION_IDS):
        print(f"Analyzing sub-question '{sub_question_id}' ...")
        run_for_sub_question(sub_question_id)
        if i < len(SUB_QUESTION_IDS) - 1:
            time.sleep(SECONDS_BETWEEN_CALLS)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python agent3_analysis.py <sub_question_id>  OR  python agent3_analysis.py --all")
        sys.exit(1)

    arg = sys.argv[1]
    if arg == "--all":
        run_all()
    elif arg in SUB_QUESTION_IDS:
        print(f"Analyzing sub-question '{arg}' ...")
        run_for_sub_question(arg)
    else:
        print(f"Unknown sub_question_id '{arg}'. Must be one of {SUB_QUESTION_IDS} or --all")
        sys.exit(1)