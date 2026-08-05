# Audit Log Template

Every pipeline run should produce an audit trail entry capturing what
happened, so a human reviewer can reconstruct exactly what agents did,
what was allowed/denied, and why — this is separate from
`memory/store/review-history.jsonl` (which records review *outcomes*);
the audit log records the *process*, including denials and failures that
never produced a final outcome.

## Schema

```json
{
  "run_id": "string — unique per pipeline execution",
  "pr_id": "string",
  "timestamp": "ISO-8601",
  "events": [
    {
      "actor": "orchestrator | planner | reviewer | release-manager | human",
      "action": "string — e.g. 'tool_call', 'policy_denial', 'escalation', 'human_approval', 'retry', 'rollback'",
      "detail": "string — what specifically happened",
      "tool_name": "string | null — populated for tool_call/policy_denial events",
      "result": "success | denied | error",
      "timestamp": "ISO-8601"
    }
  ],
  "final_outcome": "approved | request_changes | escalated | error"
}
```

## Example Entry

```json
{
  "run_id": "run-2026-08-05-001",
  "pr_id": "pr-4179",
  "timestamp": "2026-08-05T14:02:00Z",
  "events": [
    {"actor": "orchestrator", "action": "pipeline_start", "detail": "PR diff received", "tool_name": null, "result": "success", "timestamp": "2026-08-05T14:02:00Z"},
    {"actor": "planner", "action": "tool_call", "detail": "search_context query for related German locale PRs", "tool_name": "search_context", "result": "success", "timestamp": "2026-08-05T14:02:03Z"},
    {"actor": "reviewer", "action": "tool_call", "detail": "read past review history for this file path", "tool_name": "get_review_history", "result": "success", "timestamp": "2026-08-05T14:02:05Z"},
    {"actor": "release-manager", "action": "tool_call", "detail": "attempted search_context despite no grant", "tool_name": "search_context", "result": "denied", "timestamp": "2026-08-05T14:02:09Z"},
    {"actor": "orchestrator", "action": "policy_denial", "detail": "release-manager tool call blocked by TOOL_GRANTS, logged not silently dropped", "tool_name": "search_context", "result": "denied", "timestamp": "2026-08-05T14:02:09Z"},
    {"actor": "orchestrator", "action": "escalation", "detail": "reviewer found medium-severity issue, routed per risk-scoring.md rules", "tool_name": null, "result": "success", "timestamp": "2026-08-05T14:02:12Z"}
  ],
  "final_outcome": "request_changes"
}
```

## What must always be logged

- Every tool call, successful or denied (a denied call is exactly the
  "governance stopping an over-reaching agent" evidence the final
  walkthrough video needs to show)
- Every escalation to human review, and why
- Every retry or fallback triggered by reliability controls (Workstream 6)
- Every rollback, if a calibration change or deployment is reverted

## What must NOT be logged

- Full PR diffs (link to the source file instead — same rule as
  `memory/architecture-notes.md`'s "What is explicitly NOT stored")
- Secrets or credentials
- Raw human conversation content beyond a structured `human_approval` event

## Storage
Audit log entries append to `evals/audit-log.jsonl` (one JSON object per
run, matching the schema above) once the orchestrator is built and
producing real runs.

## Status
Template defined. Real audit log entries pending the orchestrator build
(same dependency noted in `docs/gap-inventory.md`'s "Known Remaining Gap").
