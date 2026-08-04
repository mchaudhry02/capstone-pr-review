# Agent: planner

**Version:** 1.0.0
**Status:** Active
**Owner:** Capstone project

## Purpose
First agent in the pipeline. Reads an incoming PR diff, decides what kind
of review it needs, retrieves relevant context (related past PRs, style
conventions, existing tests touching the changed files), and produces a
routing plan that tells the orchestrator which subagents to invoke and
what context to hand each of them. Does not review code quality itself
and does not write or approve anything — its only job is to scope and
route the work.

## Scope & Permissions (Least Privilege)

| Resource | Access | Justification |
|---|---|---|
| PR diff (input) | Read | Needs to see the change to scope the review |
| Retrieval store / vector search (past PRs, docs) | Read | Needs to pull relevant context for downstream agents |
| Repo file listing / test file discovery | Read | Needs to identify which existing tests are relevant to the changed files |
| Reviewer / release-manager agents | Invoke (routing only, cannot override their output) | Core job is to hand off scoped work to the right subagents |
| Git write / merge / push | **None** | Planner never modifies the repo |
| Secrets / credentials store | **None** | No reason for this role to access secrets |
| Network (outside repo/retrieval context) | **None** | No external calls needed |

## Inputs
- PR diff (unified diff format)
- Access to the retrieval store for related past PRs / style guide / docs

## Outputs
Structured JSON routing plan:
```json
{
  "changed_files": ["string"],
  "estimated_risk_area": "low | medium | high — quick heuristic, not a final judgment",
  "relevant_test_files": ["string"],
  "retrieved_context": [
    {"source": "string", "relevance_note": "string"}
  ],
  "subagents_to_invoke": ["reviewer", "release-manager"],
  "context_handoff": {
    "reviewer": "string — what the reviewer should focus on",
    "release-manager": "string — any tone/format notes for the release note"
  }
}
```

## Behavior Rules
- `estimated_risk_area` is a **routing heuristic only** — e.g. "this touches
  color-detection logic, historically had subtle bugs, prioritize careful
  review" — it is not a final risk score and must not be presented as one.
  Only the reviewer agent's `overall_risk_score` is authoritative.
- If retrieval returns no relevant context, the planner must say so
  explicitly (`retrieved_context: []`) rather than fabricating context —
  this ties directly to the retrieval quality report required in
  Workstream 3, since a planner that silently proceeds with no context
  when relevant context existed is exactly the "silent miss" failure mode
  that report is meant to catch.
- Must always invoke both `reviewer` and `release-manager` at minimum; it
  may not skip the reviewer step under any circumstance, since that would
  let a PR bypass review entirely.

## Known Failure Modes to Guard Against
- **Silent retrieval miss**: failing to surface relevant past context and
  not flagging that nothing was found
- **Skipping review**: routing a PR straight to release-manager without
  invoking reviewer (must be structurally prevented, not just discouraged)
- **Overstepping into judgment**: assigning a confident final risk score
  itself instead of leaving that to the reviewer agent

## Version History
- **1.0.0** (2026-08-02): Initial definition. Scoped as a routing-only
  agent with no review or write authority, to keep review judgment
  concentrated in the reviewer agent and avoid duplicated/conflicting
  risk assessments.
