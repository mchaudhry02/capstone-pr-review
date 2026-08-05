# Holdout Set

## Why a holdout set matters

`skills/risk-scoring.md` was built directly from observations on `pr-688`,
`pr-569`, and `pr-4179` (the baseline review's Risk Flagging weakness).
If those same 3 PRs are also used to *evaluate* the reviewer agent, the
eval is grading the agent on the exact examples it was calibrated against
— not a fair test of whether it generalizes. A holdout set fixes this by
splitting data into what's used to build/tune the pipeline vs. what's
used to judge it afterward.

## Split

| Set | PRs | Used for |
|---|---|---|
| **Calibration set** | `pr-688`, `pr-569` | Building `skills/risk-scoring.md`, `agents/reviewer.md` failure-mode notes. These PRs directly informed agent/skill design and must NOT be used to claim eval success. |
| **Holdout set** | `pr-4179`, `pr-653` (clean), `pr-3728` (clean) | Eval-only. These were seeded/reviewed but their results were not used to change any agent or skill definition. Scores on these PRs are the actual evidence of whether the pipeline works, not just whether it memorized its own tuning examples. |

## Holdout Set Details

| PR | Type | Ground truth | Expected agent behavior |
|---|---|---|---|
| `pr-4179` | Seeded bug (missing regex alternation pipe) | See `data/seeded-bugs/ground-truth.md` | `overall_recommendation: request_changes` or `escalate_to_human`, finding grounded in the specific regex line |
| `pr-653` | Clean | N/A | `overall_recommendation: approve`, no false-positive findings |
| `pr-3728` | Clean | N/A | `overall_recommendation: approve`, no false-positive findings |

## Rule going forward

Any new PR added to the ground-truth set for the *purpose of fixing* a
weakness in an agent or skill goes into the **calibration set**, not the
holdout set. Only add to the holdout set when a PR was scored but its
results did NOT trigger a design change — that's what keeps it a fair
test. If you're ever unsure which bucket a PR belongs in, ask: "did I
change anything about how the agents work because of this PR's result?"
If yes, calibration set. If no, holdout set.

## Status
Holdout set defined. Awaiting the reviewer agent actually being run
(Workstream 3 build) to produce real, gradeable output against this set.
