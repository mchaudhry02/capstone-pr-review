# ADR-002: Five-Dimension Quality Rubric Design

**Status:** Accepted
**Date:** 2026-08-02

## Context

The project needed a way to score any PR review (human or agent) against
consistent, comparable criteria — both for setting the Module 1 baseline
and for later evaluating the agentic pipeline against it. Without a
shared rubric, "the agent is better than a human" would be an
unfalsifiable claim.

## Decision

Adopt a 5-dimension rubric, each scored 0-2: Bug Detection, Risk
Flagging, False Positive Control, Grounding, and Release Note Quality.
Pass threshold set at >=8/10 total, with a hard requirement of 2/2 on
Bug Detection whenever a seeded bug is present in the input.

## Rejected Alternatives

**Alternative 1: A single overall 1-5 quality score.** Rejected because
a single number can't distinguish *why* a review scored poorly — a
review that misses a bug and a review that's vague but technically
correct would both just show "3/5," with no diagnostic value for
improving the pipeline.

**Alternative 2: Binary pass/fail per PR, no partial credit.** Rejected
as too coarse for a small ground-truth set — with only a handful of PRs
in the baseline sample, a binary scheme would produce too little signal
to compare baseline vs. agent meaningfully. The 0-2 scale per dimension
gives finer-grained comparison on a small sample.

**Alternative 3: Score only Bug Detection, since that's the core task.**
Rejected once the baseline run was actually completed — evidence:
`docs/baseline-run-notes.md` showed human reviewers caught 3/3 seeded
bugs (perfect Bug Detection) while still scoring only 1/2 on Risk
Flagging across every case. A rubric that only measured Bug Detection
would have completely missed this real, measured weakness, which later
became the direct motivation for the risk-scoring deterministic
conversion (ADR-001).

## Evidence

`docs/baseline-run-notes.md` — the rubric's multi-dimension design is
what allowed the Risk Flagging weakness to be measured and later fixed;
a coarser rubric would not have surfaced it.

## Consequences

**Positive:** dimension-level scoring gave a specific, actionable target
(Risk Flagging) rather than a vague "do better" signal, and directly
enabled ADR-001's deterministic conversion to be evidence-based rather
than speculative.

**Negative:** self-scoring by a single human reviewer (no second scorer)
means the baseline scores have some subjectivity; a larger project would
want inter-rater reliability checks.

## Open Risks

The rubric's thresholds (8/10 pass, 2/2 Bug Detection requirement) were
set by judgment, not derived from a larger calibration dataset — they
may need adjustment once more PRs are scored.
