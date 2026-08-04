# Memory Architecture

## What gets stored, and why

| Memory type | What it holds | Who reads it | Who writes it | Persistence |
|---|---|---|---|---|
| **Review history** | Past PR findings, severity, and outcomes (approved/escalated) | planner (for context), reviewer (for consistency) | reviewer, after each run | Long-term, append-only |
| **Style/convention notes** | Patterns noticed across reviews (e.g. "this repo always clamps with Math.min, not max") | reviewer | reviewer, on calibration | Long-term, updated on reflection |
| **Calibration log** | Prompt/scoring rule changes made because of eval results | (human review, Workstream 4 evals) | human + planner/reviewer proposing changes | Long-term, append-only |
| **Session context** | Current PR's diff, findings-in-progress, routing plan | all agents in a single pipeline run | planner, reviewer, release-manager | Short-term, cleared after each run |

## Why this split (memory vs. context vs. prompt)

- **Prompt**: fixed instructions (each agent's `.md` definition in `agents/`)
  — doesn't change per-run, defines the role
- **Context**: what's passed in for a single run (the PR diff, retrieved
  related PRs) — exists only for that run, then discarded
- **Memory**: what persists *across* runs — review history and calibration
  decisions that should inform future runs without being re-explained
  every time

This matters directly for `risk-scoring` (see `skills/risk-scoring.md`):
without persistent memory, the reviewer agent would re-derive its own
severity judgment from scratch every single run, with no consistency
across PRs. Memory lets it stay calibrated over time.

## Storage format

For this capstone (no-deployment path), memory is stored as append-only
JSON Lines files under `memory/store/`:

```
memory/
├── architecture-notes.md    # this file
├── reflection-log.md         # concrete updates made based on reflection
└── store/
    ├── review-history.jsonl      # one line per past PR review
    └── calibration-log.jsonl     # one line per calibration change
```

Each line in `review-history.jsonl`:
```json
{"pr_id": "string", "date": "ISO-8601", "findings_summary": "string", "overall_risk_score": "string", "outcome": "approved | escalated | request_changes"}
```

## What is explicitly NOT stored in memory

- Secrets or credentials (never touch memory)
- Full PR diffs (session context only, discarded after run — memory
  stores summaries, not full diffs, to keep storage small and avoid
  accidentally retaining sensitive code long-term)
- Raw human conversation/chat logs
