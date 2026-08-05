# Evaluation Harness

Combines two layers of checking, per the PRD/rubric requirements:

## Layer 1: Deterministic checks (automated, no judgment needed)

Run against the reviewer agent's structured JSON output
(`agents/reviewer.md` output format):

| Check | Pass condition |
|---|---|
| **Schema validity** | Output matches the required JSON shape (`findings`, `overall_risk_score`, `overall_recommendation`) |
| **Grounding check** | Every finding's `file` and `line_or_hunk` field actually exists in the input diff (not hallucinated) |
| **Seeded-bug catch** | For a PR with a known seeded bug (from `ground-truth.md`), at least one finding references the correct file/line of the actual seeded change |
| **Clean-PR false-positive check** | For a clean PR, no finding has `severity: high` or `critical` |
| **Recommendation consistency** | `overall_recommendation` matches the risk-scoring skill's rules (`skills/risk-scoring.md`) given the findings present — e.g. a `critical` finding must map to `escalate_to_human` |

These are yes/no, script-checkable — no human judgment required, and they
map directly to the "does not silently miss obvious results" requirement.

## Layer 2: Rubric-based scoring (human or calibrated-scorer judgment)

Apply `docs/quality-rubric.md`'s 5 dimensions to each run:
Bug Detection, Risk Flagging, False Positive Control, Grounding, Release
Note Quality — each scored 0-2, same scale used in
`docs/baseline-run-notes.md`, so agent results are directly comparable to
the human baseline.

## How a run is scored

1. Run the reviewer agent against a holdout-set PR
2. Run `evals/run_eval.py` — applies all Layer 1 deterministic checks automatically
3. Score Layer 2 manually (or via a calibrated scoring subagent later),
   using the same rubric table as the baseline
4. Combine into a single eval report row

## Pass/Fail Threshold

Same as `docs/quality-rubric.md`: >=8/10 total (or >=5/6 for seeded-bug
PRs missing the Release Note column, matching how baseline scores were
normalized) AND all deterministic checks pass AND, for seeded-bug PRs,
Bug Detection = 2/2.

## Output

Each eval run appends a row to `evals/eval-results.jsonl` and to
`memory/store/calibration-log.jsonl` if the result triggers any
prompt/skill/routing change (per the calibration log requirement).

## Status
Harness design complete. `evals/run_eval.py` implements Layer 1
deterministic checks and can run today against any properly-formatted
JSON output. Layer 2 scoring will be applied once the reviewer agent is
actually running end-to-end (pipeline build, later in Workstream 3).
