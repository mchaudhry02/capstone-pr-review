# Baseline Metrics (Pre-Agent)

Measured before the multi-agent pipeline exists, using the same PR sample
set in `data/`. This is what Workstream 7's impact report compares against.
All metrics use the best available proxy where a direct measurement isn't
possible on a no-deployment path — proxies are noted explicitly.

## Sample
- Source: chalk/chalk, N merged PRs pulled via `fetch-prs.sh`
- Includes: original real PRs + the seeded-bug variant set
  (`data/seeded-bugs/`)

## Metrics to Record

| Metric | How measured (baseline / manual) | Proxy used? |
|---|---|---|
| **Review latency** | Time to manually read a diff, form an opinion, and write review comments, timed per PR (self-timed on a small sample, extrapolated) | Yes — self-timed manual review vs. real historical review time (not available on public repo without maintainer data) |
| **Defect rate** | # of seeded bugs (of known total) NOT caught during a manual pass over the same PRs, before building the agent | Direct measurement on seeded set; proxy for real-world defect escape rate |
| **Cycle time** | Time from "PR ready for review" to "review comments delivered," manual baseline | Self-timed proxy |
| **Cost per run** | Estimated engineer time per review x average loaded hourly rate | Proxy — real deployment would use actual reviewer salary data |
| **Quality** | Score using `quality-rubric.md` applied to the manual review process itself | Direct measurement using the same rubric as the agent will be scored on, for apples-to-apples comparison |

## Baseline Run Plan
1. Before building any agent logic, manually review a subset of PRs
   (including the seeded-bug set) as if doing a normal code review.
2. Time each review.
3. Score each manual review using `quality-rubric.md`.
4. Record whether the seeded bug was caught.
5. Store raw notes/timings in `docs/baseline-run-notes.md` (to be created
   during the actual baseline run).

# Baseline Metrics (Pre-Agent) — COMPLETED

Measured before the multi-agent pipeline exists, using a 5-PR sample:
3 seeded-bug PRs and 2 clean PRs, all from chalk/chalk. This is what
Workstream 7's impact report compares against. Metrics use the best
available proxy where a direct measurement isn't possible on a
no-deployment path — proxies are noted explicitly.

## Sample
- Source: chalk/chalk (pulled via `fetch-prs.sh`)
- Seeded-bug PRs: pr-688 (Math.min/max swap), pr-4179 (missing regex
  alternation pipe), pr-569 (dropped `modifierNames` export)
- Clean PRs: pr-653, pr-3728
- Full details: `data/seeded-bugs/ground-truth.md`
- Raw run data: `docs/baseline-run-notes.md`

## Results

| Metric | Result | Notes / Proxy |
|---|---|---|
| **Bug detection rate** | 3 / 3 (100%) | All seeded bugs caught in manual review |
| **Review latency** | 5 min average per PR | Self-timed manual review; real historical maintainer review time not available on a public repo |
| **Cycle time** | ~5 min per PR (same as review latency in this simplified baseline) | Proxy — no separate "wait for reviewer" step measured, since this was a single-reviewer solo pass |
| **Cost per run** | $6.25 per review | Proxy: 5 min x $75/hr assumed loaded hourly rate, converted to per-minute cost |
| **Quality (rubric score)** | 75% average | Seeded-bug PRs averaged 83% (5/6); clean PRs averaged 62.5% (avg of 50% and 75%) |
| **Defect rate** | 0% missed on this sample (3/3 caught) | Small sample (n=3 seeded bugs) — not statistically robust, but establishes a baseline floor |

## Key Qualitative Finding: Risk Flagging is the weak point

Across all 3 seeded-bug PRs, Risk Flagging scored 1/2 (not 2/2) consistently.
The manual review correctly identified *what* was broken but did not
consistently state *how severe* the issue was or what action to take
(approve / request changes / escalate). This is a concrete, specific
weakness in the human baseline that the agentic pipeline should be
measured against and expected to improve on.

## Known Limitations of This Baseline (Honest Disclosure)

- Small sample size (5 PRs total, 3 seeded bugs) — sufficient to establish
  a directional baseline, not a statistically rigorous one
- Single reviewer (no inter-reviewer variability captured)
- Cost proxy assumes a flat $75/hr rate, not a real team's actual loaded
  cost
- Release note quality was not measured in this baseline pass (the manual
  process did not include drafting release notes) — noted as an
  intentional gap; the agent pipeline will be scored on this dimension
  where the human baseline has no comparison point

## Status
Complete. This baseline will be compared against the agentic pipeline's
results on the same 5 PRs (plus additional holdout PRs) once the
multi-agent pipeline is built (Workstream 6-7).