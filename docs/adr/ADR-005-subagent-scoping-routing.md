# ADR-005: Three-Agent Split with Mandatory Reviewer Routing

**Status:** Accepted
**Date:** 2026-08-02

## Context

The PRD identified five possible roles (planner, implementer, reviewer,
tester, release-manager). A decision was needed on how many subagents to
actually build for the capstone, how work would route between them, and
what would prevent a PR from bypassing review.

## Decision

Build three subagents — `planner`, `reviewer`, `release-manager` — with
a fixed routing rule enforced by the orchestrator: the planner always
runs first, must always hand off to the reviewer (this cannot be
skipped), and the release-manager only runs after the reviewer has
produced findings.

## Rejected Alternatives

**Alternative 1: Build all five PRD-listed roles (add implementer and
tester).** Rejected for this capstone's scope — the three built roles
already demonstrate a real orchestrator-and-subagents story (routing,
scoped tools, hand-off rules) without the added surface area of two more
roles whose value-add (writing fixes, running tests) is less central to
the core "catch problems, draft notes" workflow this project targets.

**Alternative 2: Let the planner decide dynamically whether to invoke
the reviewer, based on its own judgment of PR risk.** Rejected as a
governance risk — evidence: this is exactly the kind of decision that,
if left to agent judgment, could let a low-effort or miscalibrated
planner skip review on a PR that actually needed it. `agents/planner.md`
makes this explicit in its "Known Failure Modes" section ("Skipping
review... must be structurally prevented, not just discouraged"), and
`docs/orchestration-diagram.md`'s routing rules make this an
orchestrator-level rule, not a planner-level choice.

**Alternative 3: Let release-manager run independently of the reviewer,
drafting a note directly from the diff.** Rejected because a release
note written without knowing the reviewer's findings could describe a
change as safe when the reviewer flagged it as risky.
`agents/release-manager.md`'s behavior rules explicitly require reading
the reviewer's `overall_recommendation` and adjusting tone if escalated
— this is only possible if release-manager strictly runs after reviewer.

## Evidence

`docs/orchestration-diagram.md`'s routing rules section; `agents/planner.md`'s
explicit "must invoke reviewer" behavior rule, cross-referenced against
the orchestrator's actual control flow in `orchestrator.py`, which
always calls `run_reviewer()` before `run_release_manager()`.

## Consequences

**Positive:** the mandatory-review rule is a hard structural boundary,
not a soft convention — the same design pattern as the MCP permission
boundaries (ADR-004), applied at the routing level.

**Negative:** less flexible than a fully dynamic routing scheme — every
PR goes through the same fixed sequence, even ones a more adaptive
system might handle differently (e.g., trivially small documentation-only
changes still go through the full reviewer step).

## Open Risks

The fixed routing sequence hasn't been stress-tested against PRs that
might genuinely benefit from a different order (e.g., a PR so large it
should be split before review) — this is a known simplification for the
capstone's scope, not a claim that fixed routing is optimal for every
real-world case.
