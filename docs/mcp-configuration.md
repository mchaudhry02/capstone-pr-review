# MCP Configuration

This documents the two MCP-backed tools required by Workstream 3: a
persistent-storage server and a vector-retrieval server. Together with
`docs/orchestration-diagram.md`'s Routing-and-Tool-Grant Map, this is the
artifact that map says gets "wired into actual MCP server configuration
and container permissions."

## Why a custom stdio harness instead of the official `mcp` SDK

The official Python SDK (`pip install mcp`) needs network access to
install. This project's dev environment for building/testing these
servers had no network egress, so `mcp/storage_server.py` and
`mcp/retrieval_server.py` implement the same request shape by hand:
JSON-RPC 2.0 over newline-delimited stdin/stdout, with `initialize`,
`tools/list`, and `tools/call` methods. Tool names, input/output schemas,
and permission boundaries are written so that swapping in the real SDK
later is a mechanical change (wrap the same functions in
`mcp.server.fastmcp.FastMCP`), not a redesign. In the containerized
harness (which does have network access at `docker build` time), this is
a deliberate choice to keep, not a workaround forced by the container —
it keeps both servers dependency-light (stdlib + scikit-learn only, no
API keys, no external service to be down during a demo).

Both servers run as local stdio subprocesses spawned by the agent runtime
inside `pr-review-agent` (see `mcp/mcp_servers.json`) — no additional
network egress beyond what the container already has.

## Servers

### `pr-review-storage` (`mcp/storage_server.py`)

Wraps `memory/store/*.jsonl` behind schema-validated tools instead of
letting agents touch the files directly.

| Tool | Purpose | Classification |
|---|---|---|
| `get_review_history` | Read past PR review outcomes, optional `pr_id` filter / `limit` | internal |
| `put_review_record` | Append a completed review outcome | internal |
| `get_calibration_log` | Read the log of evidence-driven changes | internal |
| `put_calibration_proposal` | Propose (not commit) a calibration change | internal |

**Schemas** (full definitions in the file itself, mirroring
`memory/architecture-notes.md` exactly):

```json
// review_record
{"pr_id": "string", "date": "ISO-8601", "findings_summary": "string",
 "overall_risk_score": "low|medium|high|critical",
 "outcome": "approved|escalated|request_changes"}

// calibration_record
{"date": "ISO-8601", "change": "string", "reason": "string",
 "evidence_source": "string (file path)"}
```

Records that don't validate are rejected, not silently stored — the
audit trail (Workstream 4) is only as trustworthy as what's allowed into
it.

**Classification:** both record types are tagged `internal`. They're
derived from public PR diffs, but they're the pipeline's own judgment/
audit data, not a republication of the source PRs — and per
`memory/architecture-notes.md`, memory never stores secrets or full
diffs, only summaries.

**Write-access governance boundary:** no agent has direct write access to
`calibration-log.jsonl`. Agents may only call `put_calibration_proposal`,
which appends to `calibration-proposals.jsonl`; a human promotes an
accepted proposal into the real log out of band. This resolves a gap the
original design left open — the routing map said the calibration log is
written by "human + planner/reviewer" without specifying how that's kept
safe — by making the human step structural, not just documented policy.

Similarly, `put_review_record` is granted to the **orchestrator only**,
not the reviewer agent, even though the reviewer produces the finding
content. This resolves a wording mismatch between
`memory/architecture-notes.md` ("reviewer... writes [review history]")
and `docs/orchestration-diagram.md`'s tool-grant table (orchestrator
writes memory) in favor of the diagram, since the diagram is the
declared authoritative Workstream 3 artifact — the reviewer hands
findings to the orchestrator, which is the only role that commits them.

### `pr-review-retrieval` (`mcp/retrieval_server.py`)

Indexes every diff under `data/*.diff` and `data/seeded bugs/*.diff` at
the per-changed-file level (288 chunks across 44 PRs as of this writing)
using TF-IDF + cosine similarity — local and offline, no embeddings API
required.

| Tool | Purpose | Classification |
|---|---|---|
| `search_context` | Query the index, returns top-k results above a relevance floor | public |
| `index_stats` | Doc/PR counts, current relevance threshold | public |

**Schema — search result:**

```json
{"doc_id": "pr-{id}#{file_path}", "pr_id": "string", "file_path": "string",
 "snippet": "string, <=300 chars", "relevance_score": "float",
 "citation": "string, source diff file path", "classification": "public"}
```

**Classification:** `public` — every indexed document comes from a
merged, public PR on `chalk/chalk` or `date-fns/date-fns`.

**Citation & traceability:** every result carries `doc_id` (unique,
`{pr_id}#{file_path}`) and `citation` (the actual `data/pr-*.diff` file
path on disk). A caller — or a reviewer checking the planner's work —
can always walk from a retrieval result back to the literal source diff.
This is what lets `agents/planner.md`'s `retrieved_context` output
(`source`, `relevance_note`) be independently verified rather than taken
on faith.

**Explicit-miss behavior:** results below `RELEVANCE_THRESHOLD` (0.08,
tuned against the ground-truth queries below) are dropped rather than
padded with low-quality matches. An out-of-domain query returns
`results: []`. This is a direct implementation of `agents/planner.md`'s
behavior rule: *"If retrieval returns no relevant context, the planner
must say so explicitly... rather than fabricating context."*

## Role-to-tool grants (enforced two ways)

`mcp/mcp_servers.json`'s `_role_tool_allowlist` documents the mapping;
each server also independently enforces the same mapping via an optional
`_caller_role` argument on every `tools/call` (see `TOOL_GRANTS` in both
`.py` files), so the boundary holds even if the client-side config is
bypassed. This mirrors `docs/orchestration-diagram.md`'s
Routing-and-Tool-Grant Map exactly:

| Role | Storage tools | Retrieval tools |
|---|---|---|
| orchestrator | read + write review history, read calibration log | search + stats |
| planner | read review history, read calibration log | search + stats |
| reviewer | read review history, read calibration log | search + stats |
| release-manager | none | none |

Full CI-enforced policy testing against this table is Workstream 4's
job; this file and the two servers are the configuration that work will
attach to.

## Retrieval quality — smoke test results (2026-08-04)

Running the 6 ground-truth queries from `data/seeded bugs/ground-truth.md`
against `pr-review-retrieval` (`python3 mcp/retrieval_server.py --selftest`):

| # | Query | Expected PR | Result | Notes |
|---|---|---|---|---|
| 1 | past PRs touching FORCE_COLOR clamping logic | 688 | **HIT** | |
| 2 | changes to ansi-styles exports | 569 | **HIT** | |
| 3 | German locale month name matching patterns | 4179 | **MISS** | see below |
| 4 | terminal type detection additions (xterm variants) | 653 | **HIT** | |
| 5 | known bug classes not caught by existing tests | 569 | **HIT** (after fix) | was a miss before title-weighting, see `memory/reflection-log.md` 2026-08-04 |
| 6 (negative) | changes to CONTRIBUTING.md wording | 3728, NOT 688 | **HIT** | correctly avoided false positive |

**5/6, plus a clean pass on the negative/false-positive test case.** This
is a smoke test, not the full Workstream 3 retrieval quality report — the
full report should widen the query set and formally track precision, not
just hit/miss on 6 hand-picked cases.

**Known open limitation (query #3):** the words in the query
("German", "month") never literally appear anywhere in the source PR's
title or diff — the PR title says `fix(de-AT): support parsing "Jänner"
with de-AT locale`, and the diff touches `src/locale/de/_lib/match/`.
This is a genuine vocabulary-mismatch problem that pure lexical (TF-IDF)
search cannot solve by re-weighting fields, since the missing terms
aren't present in the indexed text at all. Logged as an open item in
`memory/reflection-log.md` with two candidate fixes for Workstream 5
right-tool evaluation: a small deterministic locale-code/language-name
alias table, or swapping to embedding-based semantic search (would need
network/API access this offline harness didn't have).

## Running the servers yourself

```bash
# Inside the container (or locally with python3 + scikit-learn installed):
python3 mcp/storage_server.py --selftest
python3 mcp/retrieval_server.py --selftest

# As actual MCP servers (stdio, JSON-RPC 2.0, one request per line):
python3 mcp/retrieval_server.py <<< '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

## What's still open (Workstream 3/4)

- Widen the retrieval ground-truth set beyond 6 queries for a formal
  retrieval quality report (currently a gap-inventory item).
- Wire `mcp/mcp_servers.json`'s allow-list into an actual CI policy test
  (Workstream 4), not just server-side enforcement.
- Decide on and implement a fix for the query #3 vocabulary-mismatch gap
  (Workstream 5 right-tool decision — deterministic alias table vs.
  embeddings).
