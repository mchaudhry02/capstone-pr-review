# Reflection Log

Concrete updates made to agents, skills, or memory rules as a result of
observed results — not just a diary, each entry should tie to an actual
change made.

## 2026-08-02: Risk Flagging weakness -> new risk-scoring skill

**Observation:** Baseline manual review (`docs/baseline-metrics.md`)
scored 1/2 on Risk Flagging across all 3 seeded-bug PRs. Findings
correctly identified *what* was wrong but not consistently *how severe*
or *what action to take*.

**Change made:** Created `skills/risk-scoring.md` as a standalone,
rule-based skill with explicit severity -> recommendation mapping, rather
than leaving that judgment to free-form agent reasoning. Wired the
reviewer agent to call this skill for every finding.

**Expected effect:** Reviewer agent's `overall_recommendation` should be
consistent and explainable across runs, closing the specific gap the
baseline exposed.

## 2026-08-02: pr-569 not caught by tests -> memory should track this pattern

**Observation:** `pr-569`'s seeded bug (dropped `modifierNames` export)
was NOT caught by the existing chalk test suite (confirmed via `npx ava`
— all 32 tests passed). This is a class of bug (silent API/export
removal) that only a reviewing agent catches.

**Change made:** Added a note to `memory/architecture-notes.md`'s
style/convention memory type description, and flagged in
`agents/reviewer.md`'s "Known Failure Modes" section, that export/API
surface changes during refactors deserve extra scrutiny regardless of
whether tests pass, since this repo's test suite has a confirmed gap here.

**Expected effect:** Future reviews of refactor-shaped PRs in this repo
should specifically check "did every previously-exported symbol survive
the move," rather than trusting a passing test suite as sufficient
evidence of correctness.

## [Planned] Next reflection point
Once the reviewer agent is actually running (Workstream 3), compare its
real findings against `data/seeded-bugs/ground-truth.md` and log whether
it independently catches what the risk-scoring skill and failure-mode
notes were designed to help it catch. This entry will be filled in with
real results once that run happens.
