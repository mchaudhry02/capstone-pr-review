# Retrieval Quality Report

Tests whether the MCP-backed retrieval store actually surfaces the right
context (and doesn't over-match irrelevant content), using the 6 test
cases defined in `data/seeded-bugs/ground-truth.md` under "Retrieval
Ground Truth Set."

## How this was run

Run via `python3 mcp/retrieval_server.py --selftest` — real TF-IDF
retrieval against 8 indexed doc-chunks from 5 PRs
(`index_stats`: `total_indexed_docs: 8, unique_prs: 5, seeded_bug_docs: 6,
relevance_threshold: 0.08`). This is real output from the actual server,
not hand-crafted.

## Results

| # | Query | Expected result | Top results returned | Hit / Miss | Notes |
|---|---|---|---|---|---|
| 1 | "past PRs touching FORCE_COLOR clamping logic" | `pr-688` | `[688, 688, 688, 688]` | **HIT** | Real + seeded-bug variants of pr-688 each have multiple indexed file-chunks, so it dominates results — expected, not a problem |
| 2 | "changes to ansi-styles exports" | `pr-569` | `[569]` | **HIT** | Clean single match |
| 3 | "German locale month name matching patterns" | `pr-4179` | `[4179]` | **HIT** | Clean single match |
| 4 | "terminal type detection additions (xterm variants)" | `pr-653` | `[653, 688]` | **HIT** | Expected result present; `pr-688` also appears — both PRs touch color/terminal detection code, so some topical overlap is plausible, not clearly wrong |
| 5 | "known bug classes not caught by existing tests" | `pr-569` | `[]` | **MISS** | Query is conceptual ("bug classes," "not caught by tests") rather than about specific code — no vocabulary overlap with the indexed diff content, so the relevance floor correctly suppressed a weak match instead of forcing one |
| 6 (negative) | "changes to CONTRIBUTING.md wording" | `pr-3728` only | `[3728, 688]` | **MISS (false positive)** | `pr-3728` correctly found, but `pr-688` incorrectly returned too — confirmed false positive |

## Summary Metrics

- **Recall (queries 1-5):** 4 / 5 expected results surfaced (query 5 missed entirely)
- **Precision (query 6):** **Confirmed false positive** — `pr-688` returned alongside the correct `pr-3728` result
- **False positive rate:** 1 confirmed false positive out of 6 queries (query 6); query 4's overlap is arguable but not clearly wrong

## Root Cause Analysis

**Query 5 miss:** A genuine retrieval limitation, not a bug. TF-IDF
matches vocabulary, not concepts — "known bug classes not caught by
existing tests" has no lexical overlap with `pr-569`'s actual diff
content. The relevance threshold (0.08) correctly suppressed a weak/noisy
match rather than forcing a bad one, matching `retrieval_server.py`'s
explicit "never fabricates context" design goal — the honest outcome
here is a miss, not a wrong guess.

**Query 6 false positive:** `pr-688`'s content doesn't obviously relate to
`CONTRIBUTING.md`, but shares enough incidental vocabulary to clear the
0.08 relevance threshold. This suggests the threshold may be slightly too
permissive for precision-sensitive queries, or that TF-IDF alone isn't
sufficient without a secondary relevance check.

## Known Limitations

- Small test set (6 queries) — sufficient to catch obvious silent misses,
  not a statistically rigorous retrieval benchmark
- Test set was built from the same PRs used elsewhere in this project
  (ground-truth bugs, baseline review) — intentional, keeps evidence
  traceable to one small, well-understood dataset, but means retrieval
  quality on genuinely novel/unseen PRs isn't directly tested here
- TF-IDF is lexical (keyword) matching, not semantic — it cannot match a
  conceptual query like query 5 to content that doesn't share vocabulary,
  even where a human would consider them related

## Status
**Complete.** 4/6 hit, 1 confirmed miss (query 5 — conceptual/lexical
mismatch), 1 confirmed false positive (query 6). Real evidence from the
actual retrieval server, not a hand-crafted example. Logged as a
candidate calibration change (see `memory/store/calibration-proposals.jsonl`).