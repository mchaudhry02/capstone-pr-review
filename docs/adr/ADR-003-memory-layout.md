# ADR-003: Memory Layout — Separate Review History, Calibration Log, and Session Context

**Status:** Accepted
**Date:** 2026-08-02

## Context

The pipeline needed persistent memory so the reviewer agent doesn't
re-derive judgment from scratch on every run, without conflating three
different kinds of state: what's fixed per-agent (prompt), what's
specific to one run (context), and what should persist and inform future
runs (memory).

## Decision

Split memory into three explicit types, each with a different
persistence lifetime and storage format:
- **Review history** (`memory/store/review-history.jsonl`) — append-only,
  long-term, one line per past PR review outcome
- **Calibration log** (`memory/store/calibration-log.jsonl`) — append-only,
  long-term, records prompt/skill/tool-grant changes made because of
  evidence
- **Session context** — short-term, exists only for the duration of one
  pipeline run (the current diff, in-progress findings), never persisted

## Rejected Alternatives

**Alternative 1: A single flat memory file for everything.** Rejected
because review outcomes and calibration decisions have different write
patterns and different audiences (review history is written by every
run; calibration log entries are rare and require human promotion — see
ADR-006). Mixing them would make it harder to enforce the write-access
distinction MCP's `TOOL_GRANTS` actually needs (see ADR-004).

**Alternative 2: A real database (SQLite) instead of JSON Lines files.**
Rejected as unnecessary complexity for this project's scale — evidence:
the entire review-history dataset produced during this project is a
handful of records (see `memory/store/review-history.jsonl`), well
within what a flat, human-readable, git-diffable file handles fine.
JSON Lines also makes every record individually appendable and readable
without a query layer, which matters for the audit-trail requirement.

**Alternative 3: Store full PR diffs in memory alongside the outcome.**
Rejected for both size and safety reasons — diffs can be large, and
persisting full source code in a long-lived memory store increases the
risk of accidentally retaining something sensitive. `memory/architecture-notes.md`
explicitly documents this as "What is explicitly NOT stored," storing
only summaries with a reference back to the source diff file instead.

## Evidence

`memory/architecture-notes.md`'s explicit table of what's stored by whom,
and the working `mcp/storage_server.py` schema validation, which rejects
any record missing required fields — this only works cleanly because
review history and calibration data have distinct, well-defined schemas.

## Consequences

**Positive:** clean separation makes the MCP tool-grant boundaries
(ADR-004) straightforward to reason about — different memory types can
have different read/write rules without special-casing.

**Negative:** three files instead of one adds a small amount of
bookkeeping overhead (e.g., needing to know which file a given fact
belongs in).

## Open Risks

At larger scale (many more PRs), flat JSON Lines files may need to move
to an indexed store for query performance — not a concern at this
project's current data volume, but worth flagging for a real deployment.
