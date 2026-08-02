# Iteration Log

Chronological record of decisions, changes, and why they were made.
Update this every time something meaningfully changes (workflow choice,
rubric adjustment, subagent scope change, tool grant, etc.).

## [2026-08-02] Workflow selected
Chose PR Review + Release Notes pipeline over dependency triage, test
generation, ticket-to-implementation, docs refresh, and codebase retrieval.
Reasoning: natural multi-agent split (planner/implementer/reviewer/release
manager), clear objective checks (existing test suite + seeded bugs),
straightforward metrics mapping to all 5 required categories, and low
setup risk compared to heavier workflows like ticket-to-implementation.

## [2026-08-02] Delivery path selected
Chose job-seeker / no-deployment path using chalk/chalk and date-fns/date-fns
PR history as representative public datasets, to avoid approval overhead
on a first project of this scope.

## [2026-08-02] Ground-truth seeded-bug set built
Created 3 confirmed seeded bugs:
- pr-688 (chalk/chalk): Math.min -> Math.max swap in FORCE_COLOR clamping
  logic. Confirmed caught by existing test suite (`npx ava`).
- pr-569 (chalk/chalk): dropped `modifierNames` export during a refactor.
  Confirmed NOT caught by existing test suite (all 32 tests passed) —
  demonstrates a bug class only an agentic/human reviewer catches.
- pr-4179 (date-fns/date-fns): missing regex alternation pipe merging
  `jänner` and `januar` into one broken literal string. No dedicated test
  found covering this locale-matching logic.

Chose a mix of bug types (broken clamping, silent API removal, broken
regex alternation) deliberately, so the eval later demonstrates the
reviewer agent catches different classes of problems, not one repeated
pattern.

Retired: pr-579 (flipped comparison operator) was attempted but dropped
from the ground-truth set. The uploaded "seeded" version didn't clearly
match the intended edit, and the resulting test failure traced back to a
pre-existing gap in chalk's own test coverage unrelated to the intended
change, not to a change we could clearly attribute. Not usable as
defensible evidence.

## [2026-08-02] Containerized harness started
Initial Dockerfile + docker-compose.yml created with non-root user,
scoped volume mounts (data/ and workspace/ only), and credentials passed
via .env at runtime rather than baked into the image.

## [2026-08-02] Baseline run completed
Manual baseline review pass run over 5 PRs (3 seeded-bug, 2 clean).
Results: 3/3 bugs caught, 5 min avg review time, 75% avg quality score,
$6.25 avg cost per review (proxy). Key finding: Risk Flagging consistently
scored 1/2 across seeded-bug PRs — the human baseline correctly identified
issues but did not consistently state severity or recommended action.
This is the specific dimension the agentic pipeline should be measured
against improving. Full results in `docs/baseline-metrics.md`.