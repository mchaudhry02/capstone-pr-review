# PRD: Agentic PR Review & Release Notes Pipeline

## Problem Statement
Engineering teams spend significant time on manual PR review — catching bugs,
security issues, and style problems before merge — and on writing release
notes after merge. This review burden slows cycle time and is inconsistent:
reviewer attention varies PR to PR, and subtle regressions (off-by-one logic,
flipped comparisons, silently dropped exports) can pass review undetected.

## Stakeholder
Engineering manager / tech lead responsible for a repository who currently
bottlenecks on manual PR review and wants faster, more consistent review
coverage without lowering the bar on quality or safety.

## Delivery Path
Job-seeker / no-deployment. The pipeline runs against a representative
dataset of real, merged PRs pulled from a public open-source repository
(chalk/chalk), not live production traffic. In a real deployment, this
would instead trigger on live GitHub webhooks (PR opened / marked ready
for review) against the team's actual repository, with appropriately
scoped write access and real-time secrets from a vault rather than a local
`.env` file.

## Trigger
A pull request is opened or marked ready-for-review.
(Simulated here as: a PR diff file is placed in the pipeline's input folder.)

## Inputs
- PR diff (changed files, added/removed lines)
- Repository's existing automated test suite
- Style/lint configuration
- History of past merged/rejected PRs (used for retrieval context)

## Outputs
1. Structured review: inline comments + an overall risk score
2. Recommend / escalate-to-human decision
3. Draft release-note line summarizing the change

## Acceptance Criteria
- Catches 100% of the seeded ground-truth bug set (see `data/seeded-bugs/ground-truth.md`)
- Flags high-risk changes (security-relevant logic, hardcoded secrets,
  silently dropped public exports) for mandatory human escalation rather
  than auto-approving them
- False-positive rate on clean PRs stays low enough that a human reviewer
  would not need to override the agent on the majority of clean PRs
  (target: no more than 1 in 5 clean PRs flagged)
- Draft release notes are usable with light editing, not full rewrites

## Failure Modes
- **False approval**: agent misses a real bug or security issue and
  recommends merge anyway
- **Hallucinated fix**: agent suggests a code change that isn't grounded in
  the actual diff or repo conventions
- **Scope overreach**: a subagent attempts an action outside its granted
  permissions (e.g. the reviewer subagent, which should be read-only,
  attempts to merge a PR or access repository secrets)
- **Silent retrieval miss**: the retrieval tool fails to surface relevant
  past PR context and the pipeline doesn't surface that it happened

## What the Final Demo Must Show
- End-to-end run: PR diff in -> structured review + release note out
- Orchestrator delegating to subagents (planner, implementer, reviewer,
  release-manager)
- The reviewer agent catching at least one seeded bug from the ground-truth set
- Governance blocking a subagent attempting an out-of-scope action
- Baseline-vs-after metrics comparison

## Out of Scope
- Auto-merging PRs (all merges require human approval in this project)
- Modifying production credentials or live repository settings
- Real-time GitHub webhook integration (simulated via local diff files
  for this no-deployment path)