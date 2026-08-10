# ADR-006: Least-Privilege Defaults with Human-Gated Calibration Promotion

**Status:** Accepted
**Date:** 2026-08-05

## Context

The project needed a governance model that is actually enforced, not
just documented — per the capstone rubric's explicit requirement that "a
policy document alone is not enough." A decision was needed on default
access levels per role, and specifically on how the calibration log
(which records changes made because of eval evidence) gets written to,
since that log is itself a record of the system modifying its own
behavior.

## Decision

Every role defaults to zero access; grants are added only with specific
justification (see `docs/governance-policy.md`'s "Justification-to-Widen
Process"). Critically, no agent tool writes directly to
`calibration-log.jsonl` — agents may only call `put_calibration_proposal`,
which writes to a separate proposals file. A human must promote an
accepted proposal into the real calibration log.

## Rejected Alternatives

**Alternative 1: Grant broad default access and restrict only where a
problem is found.** Rejected as the opposite of least-privilege — this
would mean every new tool or capability is accessible by default until
someone notices it shouldn't be, rather than inaccessible by default
until justified. The capstone's own governance requirements call for
least-privilege defaults explicitly.

**Alternative 2: Let any agent write directly to the calibration log
when it determines a change is justified.** Rejected specifically
because the calibration log is a record of the system changing its own
future behavior (routing rules, prompts, tool grants) — allowing an
agent to both decide a change is warranted *and* commit that change
unilaterally removes the human check on self-modification entirely. The
`put_calibration_proposal` / human-promotion split keeps a human in the
loop for exactly this class of decision, matching the escalation
principle already applied elsewhere (e.g., `skills/risk-scoring.md`'s
rule that critical findings escalate to a human rather than
self-resolving).

**Alternative 3: Enforce least-privilege only via documentation and code
review, without a CI-testable check.** Rejected once the tool-evolution
drill was actually run — evidence: `docs/tool-evolution-drill.md` shows
a real, specific permission regression that a documentation-only policy
would not have caught until it reached production. `tests/test_policy.py`
running in CI (`.github/workflows/policy-checks.yml`) catches this class
of drift before merge, which a purely human-review-based process cannot
guarantee.

## Evidence

`docs/tool-evolution-drill.md` — direct evidence that CI-enforced policy
checks catch what documentation-only governance would have missed;
`memory/store/calibration-proposals.jsonl`'s real logged proposal
(a retrieval-threshold suggestion from `docs/retrieval-quality-report.md`'s
findings), showing the propose-then-promote flow working as designed.

## Consequences

**Positive:** self-modification of the system's own behavior always
passes through a human checkpoint; the CI test suite catches accidental
drift, not just deliberate attacks.

**Negative:** every new legitimate capability requires an explicit
grant-widening step rather than working by default — a minor friction
cost traded for the safety guarantee.

## Open Risks

The human-promotion step for calibration proposals is not yet exercised
at any real scale (only one proposal has been logged so far) — its
practicality under a higher volume of proposals is untested.
