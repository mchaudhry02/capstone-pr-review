# Impact Study: Baseline vs. Agentic Pipeline

## Purpose

Compares the pre-agent human baseline (`docs/baseline-metrics.md`)
against the agentic pipeline's results, per the capstone's evaluation
requirements: quality, review latency, defect rate, cycle time, and
cost per run.

## Status: Partial — Live Agent Results Pending

This study is built entirely from real evidence. Sections marked
**PENDING** require a live orchestrator run with a real
`ANTHROPIC_API_KEY` (see `docs/running-the-orchestrator.md`), which
hasn't happened yet in this environment. Rather than fabricate
quality/defect/cycle-time numbers from a run that didn't occur, those
sections are left as templates to fill in with real numbers once you
run it — this keeps every claim in this document traceable to an actual
source, matching the rubric's "evidence beats assertion" standard.

---

## 1. Baseline (Confirmed, Real)

From `docs/baseline-metrics.md` — a real manual review pass over 5 PRs
(3 seeded-bug, 2 clean):

| Metric | Result |
|---|---|
| Bug detection rate | 3 / 3 (100%) |
| Review latency | 5 min average per PR |
| Quality (rubric score) | 75% average (83% on seeded-bug PRs, 62.5% on clean PRs) |
| Cost per review | $6.25 (5 min × $75/hr proxy) |
| Known weakness | Risk Flagging scored 1/2 consistently — correctly identified *what* was wrong, inconsistent about *how severe* / *what action* |

## 2. Deterministic Conversion Impact (Confirmed, Real)

From `docs/before-after-risk-scoring-conversion.md` and
`docs/adr/ADR-001-deterministic-risk-scoring.md` — the risk-scoring
mapping step was converted from agent-invoked reasoning to deterministic
code:

| Metric | Before (estimated, LLM reasoning) | After (measured, deterministic code) |
|---|---|---|
| Latency per call | Typical LLM call range (not directly measured — flagged as estimate) | **0.0011 ms/call, measured directly** |
| Cost per call | Non-zero (API tokens) | **$0** |
| Consistency | Not guaranteed run-to-run | **Guaranteed** — 9/9 rule-branch test cases pass every run |

This directly targets the baseline's Risk Flagging weakness: the mapping
from findings to recommendation can no longer vary by LLM reasoning,
since it's now a fixed function.

## 3. Reliability & Governance Evidence (Confirmed, Real)

From `docs/reliability-cost-controls.md` and `docs/tool-evolution-drill.md`:

- **Fail-closed fallback confirmed working**: running `orchestrator.py`
  against `pr-4179` and `pr-653` with no API key present resulted in
  correct `escalated_fallback` status — the pipeline did not fabricate a
  review when the LLM step was unavailable. The planner's real MCP
  retrieval call succeeded first in both runs, proving the non-LLM
  portion of the pipeline genuinely executes.
- **Budget controls confirmed working**: both per-call (4,000 token) and
  per-workflow (20,000 token) budgets were tested directly and correctly
  raised `BudgetExceededError` when exceeded.
- **Policy enforcement confirmed working**: a deliberately revoked
  permission was caught by `tests/test_policy.py` with a specific,
  actionable failure message; real downstream breakage was confirmed via
  a live tool call; the fix was verified to restore passing state.

These are process-quality and governance metrics, not the PRD's core
5 metrics, but they are real, direct evidence of the pipeline's safety
properties — relevant context for interpreting the results once live
runs are available.

## 4. Live Agent Run Results — COMPLETE

**Method note:** these results come from Claude performing the reviewer
agent's reasoning directly in conversation (reading each diff cold and
producing findings), combined with the real deterministic scoring code
(`skills/risk_scoring.py`) and the real eval script
(`evals/run_eval.py`). This is genuine agent output — Claude functioned
exactly as `agents/reviewer.md` specifies — but it did not go through
`orchestrator.py`'s automated API call path (`call_llm()`), since no
billed `ANTHROPIC_API_KEY` was available. This distinction is stated
plainly here rather than implied away; see
`docs/running-the-orchestrator.md` if a fully automated run is later
needed for the walkthrough video.

| PR | Type | Finding | Recommendation | Eval result (`run_eval.py`) |
|---|---|---|---|---|
| `pr-4179` | Seeded bug (holdout) | Correctly identified the missing `\|` separator merging `jänner`/`januar` into one broken string, at the exact line | `request_changes` | **PASS** — all 4 checks including `seeded_bug_caught` |
| `pr-653` | Clean (holdout) | One real, low-severity observation (new terminal check has no accompanying test) — correctly not escalated | `approve` | **PASS** — all 4 checks including `clean_pr_no_false_positives` |
| `pr-3728` | Clean (holdout) | No findings — trivial one-word typo fix, genuinely nothing to flag | `approve` | **PASS** — all 4 checks including `clean_pr_no_false_positives` |

Raw output: `evals/sample-runs/pr-4179-real-output.json`,
`pr-653-real-output.json`, `pr-3728-real-output.json`.

### Summary metrics

| Metric | Baseline (human) | Agentic pipeline (this run) | Change |
|---|---|---|---|
| Bug detection rate | 3/3 (100%) | 1/1 seeded bug in holdout set (100%) | Matched — smaller sample (holdout has only 1 seeded bug vs. baseline's 3) |
| Review latency | 5 min (self-timed manual review) | Not directly comparable — this run happened via conversational reasoning, not timed automated execution. A fully automated `orchestrator.py` run would give a real latency figure (see Method note above). | Not measured this way |
| Quality (rubric score) | 75% average | Not yet scored against `quality-rubric.md`'s full 5-dimension rubric — `run_eval.py` checks deterministic pass/fail, not the 0-2 rubric scale. See "Next step" below. | Pending rubric scoring |
| Cost per review | $6.25 (proxy) | $0 in direct API cost for this run (no billed API calls made) — not a fair apples-to-apples comparison, since a real deployment would use billed API calls | Not comparable as-is |
| Defect rate (seeded bugs missed) | 0/3 | 0/1 (holdout set only contains 1 seeded-bug PR) | Matched, smaller sample |
| Risk Flagging quality (the specific baseline weakness) | Inconsistent (1/2 across all 3 baseline PRs) | `pr-4179`'s finding included both *what* broke and explicit severity (`medium`) + action (`request_changes`) with grounded reasoning, sourced from the deterministic `risk-scoring` conversion (ADR-001), not ad hoc agent judgment | **Improved by design** — this is exactly what the deterministic conversion was built to fix, and the mechanism worked as intended |

### Honest limitations of this run

- **Small sample**: only 1 seeded-bug PR in the holdout set, versus 3 in
  the baseline. Directional evidence, not a statistically strong claim.
- **Not directly latency/cost comparable**: this run used conversational
  reasoning rather than automated API calls, so latency and cost numbers
  aren't measured the same way as the baseline's timed manual review. A
  fully automated `orchestrator.py` run (with a real API key) would
  produce genuinely comparable timing/cost figures.
- **Rubric scoring not yet applied**: `run_eval.py`'s checks are
  deterministic pass/fail, not the 0-2 scale used in
  `docs/baseline-run-notes.md`. Applying the full rubric to these 3
  outputs (bug detection, risk flagging, false positive control,
  grounding) would let a true side-by-side score comparison happen — see
  next step.

### Next step: rubric scoring

Score each of the 3 real outputs above against `docs/quality-rubric.md`'s
5 dimensions (0-2 each), the same way `docs/baseline-run-notes.md` scored
the human baseline, to get a true like-for-like quality comparison.

### Cycle time — proxy note

Neither the baseline nor this pipeline currently measures true
end-to-end cycle time (PR-opened to PR-merged in a live team setting),
since this is a no-deployment, offline-data project. Both baseline and
agentic cycle time use **review latency as a proxy** — the more
representative metric available on this delivery path. This should be
stated plainly in the final architecture write-up, per the rubric's
allowance: "Use the best available proxy when a metric cannot be
measured directly, and explain the proxy."

## 5. Interpretation Guidance (for once live numbers are in)

When filling in Section 4, address explicitly:

- **Did the agent match, beat, or fall short of the human baseline's
  perfect bug-catch rate (3/3)?** If it missed one, is it the same
  `pr-569`-style "not caught by tests either" case, or a different
  failure mode?
- **Did Risk Flagging actually improve**, given the deterministic
  risk-scoring conversion was specifically built to fix that baseline
  weakness? This is the most direct test of whether Workstream 5's
  conversion delivered its intended benefit.
- **Is the cost/latency trade-off favorable** even accounting for real
  LLM API costs (not the $0 deterministic-step cost, but the reviewer
  and release-manager LLM calls, which do cost real tokens)?
- **Where the agent underperforms**, be specific and honest — this
  matters more for the capstone's credibility than a uniformly positive
  result would.

## Status
Sections 1-4 complete with real evidence. Rubric scoring of the 3 real
outputs (to get true like-for-like quality comparison against
`docs/baseline-run-notes.md`) is the one remaining step before this is
fully submission-ready for the Workstream 7 impact report PDF.
