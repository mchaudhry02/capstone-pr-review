# Quality Rubric: PR Review Pipeline

Used to score every pipeline run against a PR (real or seeded-bug) during
evaluation. Each run is scored 0-2 on each dimension. A run "passes" if it
scores at least 8/10 total AND scores a 2 on Bug Detection whenever a
seeded bug is present in the input.

| Dimension | 0 (Fail) | 1 (Partial) | 2 (Pass) |
|---|---|---|---|
| **Bug Detection** | Misses a known seeded bug entirely | Notices something is off but doesn't correctly identify the issue | Correctly identifies the seeded issue and its location |
| **Risk Flagging** | Fails to flag a high-risk change (secrets, security logic, dropped public API) | Flags it but with wrong severity or unclear reasoning | Flags it with correct severity and clear reasoning tied to the actual diff |
| **False Positive Control** | Flags multiple non-issues on a clean PR as blocking | Flags one minor non-issue, doesn't block | No false flags on clean PRs |
| **Grounding** | Review comments reference code/behavior not actually in the diff | Mostly grounded, one vague/unsupported claim | Every claim in the review traces to a specific line or existing test |
| **Release Note Quality** | Note is missing, wrong, or requires full rewrite | Note is usable but needs noticeable editing | Note is accurate and usable with light or no editing |

## Scoring Thresholds
- **Pass**: >=8/10 total, and 2/2 on Bug Detection for any input containing
  a seeded bug
- **Partial (needs human review)**: 5-7/10
- **Fail**: <5/10, or a 0 on Bug Detection for a seeded-bug input

## How This Feeds the Eval Harness (Workstream 3-4)
- Deterministic checks: does the flagged line number match the seeded
  bug's actual location? Does the existing test suite fail the way
  `ground-truth.md` predicts?
- Rubric-based scoring: the table above, applied by a human or a
  calibrated scoring subagent, to each run in the holdout set
- Calibration log: any time a prompt, routing rule, or tool grant changes
  because a run scored poorly here, that change and its reasoning gets
  logged in `docs/iteration-log.md` / the calibration log