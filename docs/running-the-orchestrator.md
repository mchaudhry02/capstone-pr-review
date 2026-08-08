# How to Run `orchestrator.py` for Real

This walks through running the actual multi-agent pipeline end-to-end
with a live API key, so you can capture real results for your impact
study — replacing the `escalated_fallback` results you'd get without a
key.

## Prerequisites

- Docker Desktop running (or just Python 3.12+ locally, either works for this)
- An Anthropic API key — get one at https://console.anthropic.com/ if you
  don't have one
- `scikit-learn` installed (`pip install scikit-learn --break-system-packages`)

## Step 1: Set your real API key

Open `docker/.env` (copy from `docker/.env.example` if you haven't
already) and set:
```
ANTHROPIC_API_KEY=sk-ant-your-real-key-here
```

If you're running this outside Docker (directly on your machine for
testing), export it in your terminal instead:
```bash
export ANTHROPIC_API_KEY=sk-ant-your-real-key-here
```

**Never commit this key.** `docker/.env` is already in `.gitignore`.

## Step 2: Run it against one PR

From your repo root:
```bash
python3 orchestrator.py pr-4179 data/seeded-bugs/pr-4179-SEEDED-BUG.diff
```

## Step 3: Read the output

With a real key, you should now see `"status": "completed"` instead of
`"status": "escalated_fallback"`, along with real fields:
```json
{
  "pr_id": "pr-4179",
  "review": {
    "findings": [
      {
        "file": "src/locale/de/_lib/match/index.ts",
        "line_or_hunk": "10",
        "issue": "example finding text",
        "severity": "medium",
        "recommended_action": "request_changes"
      }
    ],
    "overall_risk_score": "medium",
    "overall_recommendation": "request_changes"
  },
  "release_note": "example release note text",
  "budget": {"tokens_used": 850, "calls_made": 2},
  "audit_events": [
    {"actor": "orchestrator", "action": "pipeline_start", "pr_id": "pr-4179"}
  ],
  "status": "completed"
}
```

**Save this output** — redirect it to a file so you have it for evidence:
```bash
python3 orchestrator.py pr-4179 data/seeded-bugs/pr-4179-SEEDED-BUG.diff > evals/sample-runs/pr-4179-real-output.json
```

## Step 4: Run it against your full holdout set

Repeat for every PR in `evals/holdout-set.md`:
```bash
python3 orchestrator.py pr-4179 data/seeded-bugs/pr-4179-SEEDED-BUG.diff > evals/sample-runs/pr-4179-real-output.json
python3 orchestrator.py pr-653 data/pr-653.diff > evals/sample-runs/pr-653-real-output.json
python3 orchestrator.py pr-3728 data/pr-3728.diff > evals/sample-runs/pr-3728-real-output.json
```

## Step 5: Check the seeded bugs were actually caught

For each seeded-bug PR, open the saved output and check `review.findings`
against `data/seeded-bugs/ground-truth.md` — did the reviewer agent
independently find the same issue you seeded? This is the real version
of the check `evals/run_eval.py` already does against hand-crafted
samples — now you can run it against genuine agent output:
```bash
python3 evals/run_eval.py pr-4179 evals/sample-runs/pr-4179-real-output.json \
  data/seeded-bugs/pr-4179-SEEDED-BUG.diff \
  --expected-file src/locale/de/_lib/match/index.ts
```

Note: `run_eval.py` expects just the `review` object's JSON shape, so
you may need to extract that sub-object from the orchestrator's full
output first, e.g.:
```bash
python3 -c "import json; d=json.load(open('evals/sample-runs/pr-4179-real-output.json')); json.dump(d['review'], open('evals/sample-runs/pr-4179-review-only.json','w'))"
```

## Step 6: Record timing and cost for the impact study

Time each run so you can compare against your human baseline
(`docs/baseline-metrics.md`, which recorded ~5 min per review):
```bash
time python3 orchestrator.py pr-4179 data/seeded-bugs/pr-4179-SEEDED-BUG.diff
```

The `budget.tokens_used` field in the output gives you real token counts
— convert to cost using Anthropic's published per-token pricing for the
model used (`claude-sonnet-4-6` in `orchestrator.py`'s `call_llm()`).

## Step 7: Update your review history and calibration log

Each successful run automatically writes a record to
`memory/store/review-history.jsonl` via the `put_review_record` MCP
call — check it after running:
```bash
cat memory/store/review-history.jsonl
```
You should see new entries alongside the earlier sample ones from
Workstream 2.

## Once you have real results for all holdout PRs

Bring the numbers (timing, token cost, whether each seeded bug was
caught, quality rubric scores if you manually score the real findings)
back and we'll write the actual impact study comparing them against
`docs/baseline-metrics.md`'s human baseline — that's the last piece
Workstream 6 needs.

## If something goes wrong

- **`LLMUnavailableError` even with a key set** — double check the key is
  actually exported in the same terminal session you're running
  `orchestrator.py` from (`echo $ANTHROPIC_API_KEY` to verify)
- **`PermissionError`** — this means the MCP policy layer denied a call;
  check `docs/governance-policy.md`'s matrix, this should only happen if
  something is genuinely misconfigured
- **JSON parsing errors on the reviewer's output** — the LLM didn't
  return valid JSON matching `agents/reviewer.md`'s schema; you may need
  to tighten the prompt in `orchestrator.py`'s `run_reviewer()` function