# Verification Loop Contract — LOCKED

## Binary Critic Trigger

```
IF number_of_flags > 0
    decision = "revise"
ELSE
    decision = "accept"
```

**Any flagged claim triggers revision. There is no severity threshold.**

`flag_severity` (`major | minor`) is captured in the revision log and
critic flags for display/reporting purposes only. It does **not** affect
loop control — a "minor" flag triggers a full revision cycle exactly like
a "major" one. Do not build retry logic that branches on severity.

## Retry Contract

**Maximum revisions: 2.** There is no Revision 3.

```
DRAFT
  |
  v
EVIDENCE
  |
  v
CRITIC
  |
  +---- no flags ----> ACCEPT / SHIP
  |
  +---- flags --------> REVISION 1
                           |
                           v
                        EVIDENCE
                           |
                           v
                         CRITIC
                           |
                           +---- no flags ----> ACCEPT / SHIP
                           |
                           +---- flags --------> REVISION 2
                                                      |
                                                      v
                                                   EVIDENCE
                                                      |
                                                      v
                                                    CRITIC
                                                      |
                                                      +---- no flags ----> ACCEPT / SHIP
                                                      |
                                                      +---- flags --------> SHIP WITH FLAGS
```

After Revision 2 has been evaluated, if flags remain:

```
ship_with_flags = true
```

The system must never enter an infinite revision loop.

## Retry Scope — ⚠ NOT YET CONFIRMED, DEFAULT ASSUMPTION

**Default until explicitly confirmed:** each retry re-runs Evidence +
Critic against the **full current draft**, not just the previously-flagged
claims — a revision to one claim can introduce a new inconsistency
elsewhere in the report, so re-checking only the flagged subset risks
missing regressions.

This is the cheaper-to-build option to assume for Phase 1 mock work, but
it changes LLM call cost/latency per retry vs. a targeted re-check of only
flagged claims. **Confirm this explicitly before Phase 3**, since Phase 3
is where the real retry cycle gets built and this choice is expensive to
flip after.

Regardless of which is chosen: Synthesis should only rewrite the claims
named in `revision_instructions` — untouched claims must not be reworded
between revisions (this matters for the before/after diff in the revision
log staying meaningful).

## Ship-With-Flags Behavior

- Any claim still flagged after Revision 2's Critic pass ships in the
  final report as-is (not deleted, not silently softened further).
- That claim's revision-log row gets `final_status = "shipped_with_flag"`
  (see `revision_log_schema.json`).
- The frontend surfaces these under an "unresolved flags" view (Phase 5).

## Exit Criteria (Phase 0)

- [x] Binary trigger = any flag, no tolerance threshold.
- [x] Retry cap = 2 revisions, third attempt prohibited.
- [ ] Retry scope (full draft re-check vs. flagged-only) — default assumed, needs explicit confirmation before Phase 3.
- [x] Synthesis edits only flagged claims, regardless of retry scope chosen.
- [x] Ship-with-flags behavior defined and logged.
- [x] Severity captured but explicitly non-authoritative for loop control.
