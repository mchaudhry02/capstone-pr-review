# ADR-001: Convert Risk-Scoring from Agent Skill to Deterministic Code

**Status:** Accepted
**Date:** 2026-08-05

## Context

`skills/risk-scoring.md` defines the mapping from a reviewer agent's
`findings` (severity per issue) to an `overall_risk_score` and
`overall_recommendation`. As originally designed, this was a "skill" the
reviewer agent would apply via its own reasoning on every run.

The baseline review (`docs/baseline-metrics.md`) found that manual human
review scored 1/2 on "Risk Flagging" across all 3 seeded-bug PRs — humans
correctly identified *what* was wrong but were inconsistent about stating
severity and recommended action. `skills/risk-scoring.md` was written
specifically to fix this by giving explicit rules. But leaving those
rules to be *applied* by an LLM agent's reasoning, rather than run as
code, risks reintroducing the same inconsistency the rules were meant to
eliminate — an agent could still reason its way to a slightly different
conclusion on a similar case, run to run.

Examining the actual rules in `skills/risk-scoring.md` revealed they are
a complete, unambiguous lookup table (any critical -> escalate; any high
-> escalate; only medium/low -> request_changes if medium present else
approve; none -> approve). There is no genuine judgment call left once
`findings` exist — the mapping itself is arithmetic (find the max
severity, look up the corresponding action).

## Decision

Convert the risk-scoring mapping from an agent-invoked skill into
deterministic Python code (`skills/risk_scoring.py`). The reviewer agent
still performs the actual judgment-heavy work (reading the diff, deciding
what's wrong, assigning a severity to each finding) — only the final
mechanical mapping step moves to code.

## Rejected Alternatives

**Alternative 1: Keep it as an agent-applied skill (status quo).**
Rejected because it doesn't structurally prevent the exact inconsistency
problem it was built to solve — evidence: `docs/baseline-metrics.md`
shows this is a real, measured weakness in this project's specific
domain (Risk Flagging scored 1/2 across all 3 seeded-bug baseline
reviews), and there was no mechanism to guarantee an LLM reliably applies
a fixed lookup table identically every time.

**Alternative 2: Use an ML classifier instead of a hand-written rule
table.** Rejected as unnecessary complexity — the rule table is small,
fully specified, and has no ambiguous cases requiring statistical
inference. Evidence: all 9 branch combinations in
`skills/risk_scoring.py`'s self-test are exhaustively covered by 4 simple
conditional branches; there's no pattern here that benefits from a
learned model over an explicit lookup.

**Alternative 3: Keep it agent-applied, but add a stricter prompt/example
set to improve consistency.** Considered as a middle ground, but rejected
because even a well-prompted LLM call remains non-deterministic in
principle (temperature, model version drift) and still costs real money
and latency per call for zero added judgment value — evidence: the
before/after comparison in
`docs/before-after-risk-scoring-conversion.md` shows the deterministic
version runs in ~0.001ms at $0 marginal cost versus a full LLM API call
for logic that doesn't need one.

## Evidence

- `docs/baseline-metrics.md` — baseline weakness that motivated the
  original rule-writing effort
- `docs/before-after-risk-scoring-conversion.md` — measured latency
  (0.0011 ms/call, real measurement) and cost ($0) for the deterministic
  version, plus qualitative predictability/maintainability/audit-clarity
  comparison
- `skills/risk_scoring.py`'s self-test — 9/9 rule-branch cases pass,
  directly runnable in CI without any LLM API dependency

## Consequences

**Positive:**
- Faster, free, and fully deterministic — same findings always produce
  the same recommendation
- Directly unit-testable in CI (`.github/workflows/policy-checks.yml` can
  run `skills/risk_scoring.py` as a pure Python check, no API mocking
  needed)
- Structurally cannot reintroduce the baseline's Risk Flagging
  inconsistency, since there's no LLM reasoning step left to vary

**Negative / Trade-offs:**
- Loses flexibility for a genuinely novel finding pattern that doesn't
  cleanly fit the existing severity categories — the code will apply the
  rule mechanically rather than exercising judgment on an edge case
- If the underlying rules ever need to become more nuanced (e.g.,
  weighting *combinations* of findings differently, not just the single
  highest severity), the deterministic function will need active
  maintenance rather than the agent "figuring it out"

## Open Risks

- This conversion assumes the reviewer agent's own `findings` (severity
  assignment per issue) remain agent-judgment, which is where the actual
  risk of misjudgment now concentrates. If the reviewer over- or
  under-rates a finding's severity, the deterministic mapping will
  faithfully carry that error through — this ADR does not address
  finding-level severity accuracy, only the mapping step downstream of it
- Not yet validated against real reviewer-agent output at scale (the
  orchestrator/pipeline isn't built yet — see `docs/gap-inventory.md`'s
  "Known Remaining Gap"). This ADR's evidence is based on the rule
  table's own logical completeness and a directly measured function
  benchmark, not a live pipeline comparison.
