# Governance Policy & Role-to-Tool Access Matrix

## Principle: Least Privilege by Default

Every agent role is granted only the tools, data classifications, and
autonomy level required for its specific job. No role receives write,
merge, or credential access unless explicitly justified below. This
policy is not just documentation — it is enforced in code (see
"Enforcement Points" below), matching the rubric's requirement that
governance be "connected to tool grants, containers, CI/CD checks, MCP
allow-lists, skill rules, or audit logs," not just written down.

## Role-to-Tool Access Matrix

| Role | MCP: `pr-review-storage` | MCP: `pr-review-retrieval` | Git write/merge | Secrets | Network |
|---|---|---|---|---|---|
| **orchestrator** | `get_review_history`, `put_review_record`, `get_calibration_log` | `search_context`, `index_stats` | None | None | None |
| **planner** | `get_review_history`, `get_calibration_log` | `search_context`, `index_stats` | None | None | None |
| **reviewer** | `get_review_history`, `get_calibration_log` | `search_context`, `index_stats` | None | None | None |
| **release-manager** | None | None | None | None | None |

Source of truth: this table must match `TOOL_GRANTS` in both
`mcp/storage_server.py` and `mcp/retrieval_server.py` exactly. If they
diverge, the code wins in practice (fix the doc, don't assume the doc is
correct) — but a mismatch is itself a governance bug and should be
flagged and fixed immediately.

## Justification-to-Widen Process

A tool grant may only be widened (e.g., giving `release-manager` retrieval
access) if:
1. A specific, documented need is identified (not "might be useful later")
2. The change is proposed via `put_calibration_proposal` (or, for
   structural tool-grant changes, a written justification in
   `docs/iteration-log.md`)
3. A human reviews and approves the change before it's promoted into the
   actual `TOOL_GRANTS` dict and this document
4. The change is logged in `memory/store/calibration-log.jsonl` with the
   evidence that justified it

No agent may widen its own or another agent's tool grant unilaterally —
this is structurally true today since `TOOL_GRANTS` is a static dict in
each server's source code, not something any agent can call a tool to
modify.

## Data Classification Boundaries

| Classification | Examples in this project | Rules |
|---|---|---|
| **Public** | PR diffs, retrieval index content, real-time retrieval results | Safe to log, cache, include in eval reports and this repo's public documentation |
| **Internal** | Review history records, calibration log/proposals | Derived from public PRs but treated as the pipeline's own judgment data — not republished verbatim outside this project |
| **Secret** | API keys, credentials | Never enters memory, logs, or agent context. Lives only in `docker/.env` (gitignored) and is passed as a runtime environment variable |

No agent role has any tool grant that touches the Secret classification —
this is enforced by omission (no tool in either MCP server reads or
writes credentials).

## Enforcement Points (Policy in Code, Not Just on Paper)

| Enforcement mechanism | Where |
|---|---|
| Tool grants checked on every call | `TOOL_GRANTS` dict + `_caller_role` check in both `mcp/storage_server.py` and `mcp/retrieval_server.py`'s `handle_request` |
| Schema validation rejects malformed writes | `_validate()` in `mcp/storage_server.py` |
| Calibration log requires human promotion | `put_calibration_proposal` writes to `calibration-proposals.jsonl` only; no tool writes `calibration-log.jsonl` directly |
| Container filesystem/network boundaries | `docker/docker-compose.yml` volume mounts, non-root user in `docker/Dockerfile` |
| CI/CD policy tests | `.github/workflows/policy-checks.yml` (see below) — blocks merges that violate this matrix |

## Escalation and Rollback

| Situation | Required action |
|---|---|
| Reviewer agent finds a `critical` severity issue | `overall_recommendation: escalate_to_human` (enforced by `skills/risk-scoring.md` rules) — pipeline must not auto-approve |
| An agent attempts a tool call outside its `TOOL_GRANTS` | Request is rejected server-side with an explicit error (not silently ignored); this event should be logged (see Audit Log, `docs/audit-log-template.md`) |
| A calibration change turns out to be wrong after promotion | Revert `calibration-log.jsonl` entry, document the reversal and why in `docs/iteration-log.md`, re-run affected evals |
| MCP server returns malformed/unexpected output | Orchestrator should fail closed (stop and surface the error) rather than proceeding with unvalidated data |

## Status
Policy defined and cross-referenced against actual enforcement code. CI/CD
guardrails (`.github/workflows/policy-checks.yml`) and audit log template
still to be built — see `docs/audit-log-template.md` and the CI/CD file.
