# Corpus, Retrieval, and Deduplication — LOCKED

## Corpus

**arXiv API is the sole retrieval corpus for the project.**

No Semantic Scholar, Google Scholar, Crossref, PubMed, or general web
search results should enter the evidence pipeline.

## Query Strategy

Each fixed sub-question (see `decomposition.json`) receives a targeted
query built from a fixed concept set. Planner generates 1-3 concrete
`search_terms` per sub-question — not the sub-question text verbatim.

### approaches
EEG · emotion recognition · transformer / attention · CNN / convolutional ·
RNN / recurrent · deep learning

### datasets
EEG · emotion recognition · dataset / database / benchmark · named
datasets discovered during retrieval

### architectures
EEG · emotion recognition · architecture / model · transformer / CNN /
RNN / hybrid / attention

### metrics
EEG · emotion recognition · accuracy / F1 / precision / recall / AUC ·
evaluation

### disagreements
EEG · emotion recognition · transformer / CNN / RNN · comparison /
benchmark / performance / limitation

## Retrieval Rule

Retrieval is **sub-question-specific**. Each sub-question independently
queries the arXiv API and returns its own top-N results (fix N, e.g. 15
per query), optionally filtered by a date window if the question implies
recency.

Deduplication does **not** happen at this per-sub-question stage — it
happens once, globally, after all five sub-questions have retrieved.

> `retrieval_metadata.num_results_after_dedup` in the Retrieval -> Analysis
> payload (see `schemas/retrieval_to_analysis.json`) refers ONLY to
> deduplication within that sub-question's own raw result set (e.g.
> duplicate API records for the same arXiv ID returned by a single query).
> It does NOT reflect cross-sub-question dedup, since that can't be known
> until all five sub-questions have been retrieved. Cross-sub-question
> dedup happens downstream, once, over the canonical paper set, before
> Analysis runs.

The same paper may be retrieved for multiple sub-questions, but must
appear only once in the canonical paper set used by Analysis.

## Deduplication Ownership

**Ayush / Agents 1-4 own deduplication.**

Deduplication key:

```
arxiv_id
```

If multiple API records resolve to the same arXiv identifier, they
represent one paper. A paper relevant to `approaches` and `architectures`
should be analyzed once and referenced from both sub-questions.
