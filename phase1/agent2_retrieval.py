import json
import time
import re
from pathlib import Path
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET

import requests

from validate import validate_or_raise


# ============================================================
# PATHS
# ============================================================

PHASE1_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PHASE1_DIR / "output"

PLANNER_OUTPUT = OUTPUT_DIR / "planner_output.json"
CHECKPOINT_FILE = OUTPUT_DIR / "retrieval_checkpoint.json"
CANONICAL_FILE = OUTPUT_DIR / "canonical_papers.json"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# CONFIGURATION
# ============================================================

RESULTS_PER_QUERY = 15

# arXiv API allows paginated results.
# We request slightly more than needed so we have room if
# some entries are malformed.
API_PAGE_SIZE = 25

# Be conservative with arXiv requests.
SECONDS_BETWEEN_QUERIES = 10.0
SECONDS_BETWEEN_PAPER_BATCHES = 3.0

REQUEST_TIMEOUT = 60

API_RETRIES = 3

# Retry waits are only used for actual request/server failures.
API_RETRY_WAIT = [120,300,600]


# ============================================================
# arXiv API
# ============================================================

ARXIV_API_URL = "https://export.arxiv.org/api/query"


# XML namespaces used by the Atom feed.
ATOM_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


# ============================================================
# HTTP SESSION
# ============================================================

SESSION = requests.Session()

SESSION.headers.update(
    {
        "User-Agent": (
            "AgenticResearchSystem/1.0 "
            "(academic research retrieval; "
            "contact: project-team)"
        ),
        "Accept": "application/atom+xml,application/xml,text/xml",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
    }
)


# ============================================================
# FALLBACK QUERIES
# ============================================================

# These are only used when the original query produces
# zero results or cannot be used successfully.
#
# IMPORTANT:
# A fallback is deliberately broader than the original query.
# ============================================================

FALLBACK_QUERIES = {
    "EEG emotion recognition transformer CNN RNN":
        "EEG emotion recognition",

    "EEG emotion recognition deep learning attention":
        "EEG emotion recognition deep learning",

    "EEG emotion recognition dataset benchmark":
        "EEG emotion dataset",

    "EEG emotion database DEAP SEED":
        "EEG emotion DEAP",

    "EEG emotion recognition architecture transformer":
        "EEG emotion transformer",

    "EEG emotion recognition hybrid CNN RNN model":
        "EEG emotion recognition CNN RNN",

    "EEG emotion recognition accuracy F1 score performance":
        "EEG emotion recognition accuracy",

    "EEG emotion recognition evaluation metrics":
        "EEG emotion recognition metrics",

    "EEG emotion recognition transformer CNN comparison":
        "EEG emotion transformer CNN",

    "EEG emotion recognition benchmark model limitations":
        "EEG emotion recognition benchmark",
}


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def normalize_arxiv_id(arxiv_id):
    """
    Normalize an arXiv ID.

    Examples:
        1706.03762
        1706.03762v2
        hep-th/9901001v3
    """

    if not arxiv_id:
        return ""

    arxiv_id = arxiv_id.strip()

    # Remove URL if one accidentally appears.
    arxiv_id = re.sub(
        r"^https?://arxiv\.org/(abs|pdf)/",
        "",
        arxiv_id,
        flags=re.IGNORECASE,
    )

    # Remove query/fragment.
    arxiv_id = arxiv_id.split("?")[0]
    arxiv_id = arxiv_id.split("#")[0]

    # Remove version suffix.
    arxiv_id = re.sub(
        r"v\d+$",
        "",
        arxiv_id,
        flags=re.IGNORECASE,
    )

    return arxiv_id


def clean_text(text):
    """
    Normalize whitespace.
    """

    if not text:
        return ""

    return re.sub(
        r"\s+",
        " ",
        text.strip(),
    )


def load_json(path, default=None):
    """
    Load JSON safely.
    """

    if not path.exists():
        return default

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def save_json(path, data):
    """
    Save JSON using UTF-8.
    """

    with open(
        path,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False,
        )


# ============================================================
# PARSE arXiv XML ENTRY
# ============================================================

def parse_arxiv_entry(entry):
    """
    Convert one Atom/arXiv XML entry into our standard
    paper metadata structure.
    """

    id_element = entry.find("atom:id", ATOM_NS)
    title_element = entry.find("atom:title", ATOM_NS)
    published_element = entry.find("atom:published", ATOM_NS)
    summary_element = entry.find("atom:summary", ATOM_NS)

    if id_element is None:
        return None

    raw_id = clean_text(id_element.text)

    # Example:
    # https://arxiv.org/abs/2401.12345v2
    arxiv_id = normalize_arxiv_id(raw_id)

    if not arxiv_id:
        return None

    title = ""
    if title_element is not None:
        title = clean_text(title_element.text)

    abstract = ""
    if summary_element is not None:
        abstract = clean_text(summary_element.text)

    published = ""
    if published_element is not None:
        published = clean_text(
            published_element.text
        )

    # Authors
    authors = []

    for author_element in entry.findall(
        "atom:author",
        ATOM_NS,
    ):
        name_element = author_element.find(
            "atom:name",
            ATOM_NS,
        )

        if name_element is not None:
            name = clean_text(name_element.text)

            if name:
                authors.append(name)

    # Published date is generally ISO format:
    # 2024-01-01T12:34:56Z
    #
    # Keep only YYYY-MM-DD for our JSON.
    if published:
        match = re.match(
            r"(\d{4}-\d{2}-\d{2})",
            published,
        )

        if match:
            published = match.group(1)

    paper = {
        "arxiv_id": arxiv_id,
        "title": title,
        "authors": authors,
        "published": published,
        "abstract": abstract,
        "arxiv_url": (
            f"https://arxiv.org/abs/{arxiv_id}"
        ),
    }

    if not paper["title"]:
        return None

    return paper


# ============================================================
# SEARCH arXiv API
# ============================================================

def search_arxiv_api(query):
    """
    Search arXiv using the structured Atom API.

    Returns:
        {
            "status": "success",
            "papers": [...]
        }

    OR:

        {
            "status": "zero_results",
            "papers": []
        }

    Raises RuntimeError only for actual request/API failures.
    """

    encoded_query = quote_plus(query)

    params = (
        f"?search_query=all:{encoded_query}"
        f"&start=0"
        f"&max_results={API_PAGE_SIZE}"
        f"&sortBy=relevance"
        f"&sortOrder=descending"
    )

    url = ARXIV_API_URL + params

    print()
    print("Searching arXiv API:")
    print(f"  Query: {query}")
    print(f"  URL: {url}")

    last_error = None

    for attempt in range(API_RETRIES):

        try:

            response = SESSION.get(
                url,
                timeout=REQUEST_TIMEOUT,
            )

            status_code = response.status_code

            print(
                f"  HTTP status: {status_code}"
            )

            # ------------------------------------------------
            # Actual HTTP/server failure
            # ------------------------------------------------

            if status_code != 200:

                raise RuntimeError(
                    f"HTTP {status_code}"
                )

            # ------------------------------------------------
            # Parse XML
            # ------------------------------------------------

            try:

                root = ET.fromstring(
                    response.content
                )

            except ET.ParseError as exc:

                raise RuntimeError(
                    "Could not parse arXiv XML response: "
                    f"{exc}"
                )

            # ------------------------------------------------
            # Extract entries
            # ------------------------------------------------

            entries = root.findall(
                "atom:entry",
                ATOM_NS,
            )

            # ------------------------------------------------
            # IMPORTANT:
            # 0 results is NOT a server error.
            # ------------------------------------------------

            if not entries:

                print(
                    "  arXiv returned 0 results."
                )

                return {
                    "status": "zero_results",
                    "papers": [],
                }

            papers = []

            seen_ids = set()

            for entry in entries:

                paper = parse_arxiv_entry(
                    entry
                )

                if paper is None:
                    continue

                arxiv_id = paper[
                    "arxiv_id"
                ]

                if arxiv_id in seen_ids:
                    continue

                seen_ids.add(arxiv_id)

                papers.append(paper)

                if len(papers) >= RESULTS_PER_QUERY:
                    break

            # ------------------------------------------------
            # Parsed successfully but all entries were invalid
            # ------------------------------------------------

            if not papers:

                print(
                    "  arXiv response parsed successfully "
                    "but contained no usable papers."
                )

                return {
                    "status": "zero_results",
                    "papers": [],
                }

            print(
                f"  Parsed usable papers: "
                f"{len(papers)}"
            )

            return {
                "status": "success",
                "papers": papers,
            }

        except Exception as exc:

            last_error = exc

            print(
                f"  API attempt "
                f"{attempt + 1}/{API_RETRIES} "
                f"failed: {exc}"
            )

            # Don't sleep after final attempt.
            if attempt < API_RETRIES - 1:

                wait_time = API_RETRY_WAIT[
                    min(
                        attempt,
                        len(API_RETRY_WAIT) - 1,
                    )
                ]

                print(
                    f"  Waiting "
                    f"{wait_time} seconds..."
                )

                time.sleep(
                    wait_time
                )

    raise RuntimeError(
        "Could not retrieve arXiv API results "
        f"for query:\n{query}\n"
        f"Last error: {last_error}"
    )


# ============================================================
# RUN ONE QUERY
# ============================================================

def run_single_query(query):
    """
    Run the original query.

    If it returns zero results, immediately try the configured
    fallback query.

    Actual HTTP/API failures still use retry/backoff.
    """

    result = search_arxiv_api(
        query
    )

    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    if result["status"] == "success":

        return result["papers"]

    # --------------------------------------------------------
    # ZERO RESULTS
    # --------------------------------------------------------

    if result["status"] == "zero_results":

        fallback = FALLBACK_QUERIES.get(
            query
        )

        if not fallback:

            print()
            print(
                "No fallback configured."
            )

            return []

        print()
        print(
            "Original query returned 0 results."
        )

        print(
            "Trying broader fallback immediately:"
        )

        print(
            f"  {fallback}"
        )

        fallback_result = search_arxiv_api(
            fallback
        )

        if (
            fallback_result["status"]
            == "success"
        ):

            return fallback_result[
                "papers"
            ]

        print()
        print(
            "Fallback query also returned "
            "0 results."
        )

        return []

    raise RuntimeError(
        "Unexpected arXiv search status."
    )


# ============================================================
# CHECKPOINT
# ============================================================

def load_checkpoint():

    checkpoint = load_json(
        CHECKPOINT_FILE,
        default={
            "completed_queries": {},
            "papers": {},
        },
    )

    if (
        "completed_queries"
        not in checkpoint
    ):
        checkpoint[
            "completed_queries"
        ] = {}

    if "papers" not in checkpoint:
        checkpoint["papers"] = {}

    return checkpoint


def save_checkpoint(checkpoint):

    save_json(
        CHECKPOINT_FILE,
        checkpoint,
    )


# ============================================================
# RETRIEVE ONE SUB-QUESTION
# ============================================================

def retrieve_sub_question(
    sub_question,
    checkpoint,
):

    sub_question_id = sub_question[
        "id"
    ]

    search_terms = sub_question[
        "search_terms"
    ]

    print()
    print("=" * 70)
    print(
        f"Retrieving for sub-question "
        f"'{sub_question_id}' ..."
    )
    print("=" * 70)

    all_papers = []

    for index, query in enumerate(
        search_terms,
        start=1,
    ):

        checkpoint_key = (
            f"{sub_question_id}::{index}"
        )

        # ====================================================
        # RESUME FROM CHECKPOINT
        # ====================================================

        if (
            checkpoint_key
            in checkpoint[
                "completed_queries"
            ]
        ):

            print()
            print(
                f"[CHECKPOINT] Skipping "
                f"completed query "
                f"{index}/{len(search_terms)}:"
            )

            print(
                f"  {query}"
            )

            cached_ids = (
                checkpoint[
                    "completed_queries"
                ][checkpoint_key]
                .get(
                    "paper_ids",
                    [],
                )
            )

            for arxiv_id in cached_ids:

                if (
                    arxiv_id
                    in checkpoint["papers"]
                ):

                    all_papers.append(
                        checkpoint[
                            "papers"
                        ][arxiv_id]
                    )

            continue

        # ====================================================
        # NEW QUERY
        # ====================================================

        print()
        print(
            f"Query {index}/"
            f"{len(search_terms)}:"
        )

        print(
            f"  {query}"
        )

        papers = run_single_query(
            query
        )

        paper_ids = []

        for paper in papers:

            arxiv_id = paper[
                "arxiv_id"
            ]

            paper_ids.append(
                arxiv_id
            )

            checkpoint[
                "papers"
            ][arxiv_id] = paper

            all_papers.append(
                paper
            )

        # ====================================================
        # SAVE CHECKPOINT IMMEDIATELY
        # ====================================================

        checkpoint[
            "completed_queries"
        ][checkpoint_key] = {
            "query": query,
            "paper_ids": paper_ids,
        }

        save_checkpoint(
            checkpoint
        )

        print()
        print(
            f"[CHECKPOINT] Saved query "
            f"{index}/{len(search_terms)}"
        )

        # ====================================================
        # WAIT BEFORE NEXT SEARCH QUERY
        # ====================================================

        if index < len(search_terms):

            print()
            print(
                f"Waiting "
                f"{SECONDS_BETWEEN_QUERIES} "
                f"seconds before next query..."
            )

            time.sleep(
                SECONDS_BETWEEN_QUERIES
            )

    # ========================================================
    # DEDUP WITHIN SUB-QUESTION
    # ========================================================

    unique_papers = []

    seen_ids = set()

    for paper in all_papers:

        arxiv_id = paper[
            "arxiv_id"
        ]

        if arxiv_id in seen_ids:
            continue

        seen_ids.add(
            arxiv_id
        )

        unique_papers.append(
            paper
        )

    # ========================================================
    # SAVE SUB-QUESTION OUTPUT
    # ========================================================

    output_payload = {
        "sub_question_id": sub_question_id,
        "question": sub_question[
            "question"
        ],
        "search_terms": search_terms,
        "papers": unique_papers,
        "raw_result_count": len(
            all_papers
        ),
        "unique_paper_count": len(
            unique_papers
        ),
    }

    output_file = (
        OUTPUT_DIR
        / f"retrieval_{sub_question_id}.json"
    )

    save_json(
        output_file,
        output_payload,
    )

    print()
    print(
        f"Saved: "
        f"{output_file.name}"
    )

    print(
        f"Raw results: "
        f"{len(all_papers)}"
    )

    print(
        f"Unique papers: "
        f"{len(unique_papers)}"
    )

    return unique_papers


# ============================================================
# GLOBAL CANONICAL DEDUPLICATION
# ============================================================

def build_canonical_papers(
    planner,
    checkpoint,
):

    canonical = {}

    # ========================================================
    # PROCESS EVERY SUB-QUESTION
    # ========================================================

    for sub_question in planner[
        "sub_questions"
    ]:

        sub_question_id = (
            sub_question["id"]
        )

        retrieval_file = (
            OUTPUT_DIR
            / f"retrieval_"
            f"{sub_question_id}.json"
        )

        if not retrieval_file.exists():
            continue

        payload = load_json(
            retrieval_file,
            default={},
        )

        for paper in payload.get(
            "papers",
            [],
        ):

            arxiv_id = paper[
                "arxiv_id"
            ]

            # =================================================
            # FIRST TIME SEEING THIS PAPER
            # =================================================

            if arxiv_id not in canonical:

                canonical[
                    arxiv_id
                ] = dict(paper)

                # FIXED BUG:
                # This belongs inside canonical[arxiv_id].
                canonical[
                    arxiv_id
                ][
                    "relevant_sub_questions"
                ] = [
                    sub_question_id
                ]

            # =================================================
            # PAPER ALREADY EXISTS
            # =================================================

            else:

                existing = canonical[
                    arxiv_id
                ]

                if (
                    "relevant_sub_questions"
                    not in existing
                ):

                    existing[
                        "relevant_sub_questions"
                    ] = []

                if (
                    sub_question_id
                    not in existing[
                        "relevant_sub_questions"
                    ]
                ):

                    existing[
                        "relevant_sub_questions"
                    ].append(
                        sub_question_id
                    )

    # ========================================================
    # CONVERT DICT → LIST
    # ========================================================

    canonical_papers = list(
        canonical.values()
    )

    # ========================================================
    # SAFETY CHECK
    # ========================================================

    for paper in canonical_papers:

        if not isinstance(
            paper,
            dict,
        ):

            raise RuntimeError(
                "Canonical deduplication produced "
                "a non-dictionary entry."
            )

        if "arxiv_id" not in paper:

            raise RuntimeError(
                "Canonical paper is missing "
                "'arxiv_id'."
            )

    # ========================================================
    # SORT
    # ========================================================

    canonical_papers.sort(
        key=lambda x: x[
            "arxiv_id"
        ]
    )

    # ========================================================
    # FINAL PAYLOAD
    # ========================================================

    payload = {
        "research_question": planner[
            "research_question"
        ],
        "paper_count": len(
            canonical_papers
        ),
        "papers": canonical_papers,
    }

    save_json(
        CANONICAL_FILE,
        payload,
    )

    print()
    print("=" * 70)
    print(
        "GLOBAL CANONICAL DEDUPLICATION"
    )
    print("=" * 70)

    print(
        f"Canonical papers: "
        f"{len(canonical_papers)}"
    )

    print(
        f"Saved: "
        f"{CANONICAL_FILE.name}"
    )

    return payload


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 70)
    print(
        "AGENT 2 - ARXIV RETRIEVAL"
    )
    print("=" * 70)

    # ========================================================
    # LOAD PLANNER OUTPUT
    # ========================================================

    planner = load_json(
        PLANNER_OUTPUT
    )

    if not planner:

        raise FileNotFoundError(
            "Planner output not found:\n"
            f"{PLANNER_OUTPUT}"
        )

    sub_questions = planner.get(
        "sub_questions",
        [],
    )

    if not sub_questions:

        raise RuntimeError(
            "No sub-questions found "
            "in planner_output.json"
        )

    print(
        f"Found "
        f"{len(sub_questions)} "
        f"sub-questions."
    )

    # ========================================================
    # LOAD CHECKPOINT
    # ========================================================

    checkpoint = load_checkpoint()

    print(
        "Checkpoint contains "
        f"{len(checkpoint['completed_queries'])} "
        "completed queries."
    )

    # ========================================================
    # RETRIEVE ALL SUB-QUESTIONS
    # ========================================================

    try:

        for sub_question in sub_questions:

            retrieve_sub_question(
                sub_question,
                checkpoint,
            )

    except Exception as exc:

        print()
        print("=" * 70)
        print(
            "AGENT 2 EXITED SAFELY"
        )
        print("=" * 70)

        print()
        print(
            f"Reason: {exc}"
        )

        print()
        print(
            "Your completed queries "
            "are preserved."
        )

        print(
            "Run Agent 2 again later "
            "to resume."
        )

        return

    # ========================================================
    # GLOBAL DEDUPLICATION
    # ========================================================

    canonical_payload = (
        build_canonical_papers(
            planner,
            checkpoint,
        )
    )

    # ========================================================
    # VALIDATION
    # ========================================================

    print()
    print("=" * 70)
    print(
        "VALIDATING AGENT 2 OUTPUT"
    )
    print("=" * 70)

    validate_or_raise(
        canonical_payload,
        "retrieval_to_analysis.json",
    )

    # ========================================================
    # COMPLETE
    # ========================================================

    print()
    print("=" * 70)
    print(
        "AGENT 2 COMPLETE"
    )
    print("=" * 70)

    print()
    print(
        "All sub-questions retrieved."
    )

    print(
        f"Canonical papers: "
        f"{canonical_payload['paper_count']}"
    )

    print(
        f"Output: "
        f"{CANONICAL_FILE}"
    )


if __name__ == "__main__":
    main()