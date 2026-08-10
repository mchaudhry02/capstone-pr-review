# ADR-004: Two Separate MCP Servers, Local Stdio Transport

**Status:** Accepted
**Date:** 2026-08-04

## Context

The pipeline needed MCP-backed persistent storage and vector retrieval,
per Workstream 3's requirements. A decision was needed on how many
servers to run, and how agents would connect to them.

## Decision

Run two separate local MCP servers over stdio JSON-RPC:
`pr-review-storage` (memory read/write) and `pr-review-retrieval`
(TF-IDF search). Each server independently enforces its own
`TOOL_GRANTS` role-based allow-list on every call, rather than trusting
a single shared gatekeeper.

## Rejected Alternatives

**Alternative 1: One combined MCP server for both storage and
retrieval.** Rejected because storage and retrieval have meaningfully
different data classifications (storage is "internal" — the pipeline's
own judgment data; retrieval is "public" — sourced from public PR diffs,
per `docs/governance-policy.md`'s classification table). Combining them
into one server would make it harder to reason about — and easier to
accidentally misconfigure — which classification applies to which tool.

**Alternative 2: Use the official `mcp` Python SDK instead of a
hand-rolled JSON-RPC implementation.** This was the original intent, but
rejected in practice — evidence: the project's container has no network
access to install packages from PyPI at the point these servers needed
to run, documented directly in `mcp/storage_server.py`'s "PROTOCOL NOTE."
The hand-rolled implementation matches the SDK's exact request/response
shape (`initialize`/`tools/list`/`tools/call` over newline-delimited
JSON-RPC), so swapping to the real SDK later requires no change to tool
names, schemas, or permission boundaries — only the transport layer.

**Alternative 3: Trust a single orchestrator-level permission check
instead of having each MCP server independently enforce `TOOL_GRANTS`.**
Rejected on defense-in-depth grounds: if the orchestrator's own
permission check were ever bypassed or misconfigured, a single point of
enforcement would mean no boundary at all. Each server checking its own
`_caller_role` argument means the boundary holds even if the calling
code is wrong — confirmed directly by the tool-evolution drill
(`docs/tool-evolution-drill.md`), where a real permission regression was
caught precisely because the server itself, not just documentation,
enforces the check.

## Evidence

`docs/tool-evolution-drill.md` — the drill only worked as a meaningful
test because permission enforcement lives in the server code itself,
not in a document or a single trusted caller.

## Consequences

**Positive:** independently testable, independently enforced boundaries;
`tests/test_policy.py` can verify each server's `TOOL_GRANTS` separately.

**Negative:** two servers to run and keep in sync with the governance
policy doc, rather than one — mitigated by the CI policy test catching
drift automatically (Section 8/9 of the architecture write-up).

## Open Risks

The hand-rolled JSON-RPC implementation has not been tested against a
real MCP client beyond this project's own `orchestrator.py` and manual
subprocess calls; swapping to the official SDK in a networked environment
would be the natural next validation step.
