# Running the Reviewer Agent via Claude.ai (No API Key Required)

This project's LLM reasoning steps (`reviewer`, `release-manager`) can be
run manually through Claude.ai instead of `orchestrator.py`'s automated
API path. This avoids needing a billed `ANTHROPIC_API_KEY`, and produces
genuinely real agent output — Claude actually performs the reasoning,
nothing is fabricated or hand-crafted to fit an expected answer.

This is the actual approach used for this project's full holdout-set
evaluation (see `evals/sample-runs/`).

## Step 1: Copy the reviewer prompt template

Go to https://claude.ai, start a new chat, and paste this, filling in
your actual diff at the bottom:

```
You are acting as the reviewer agent defined in agents/reviewer.md from
my capstone project. Read the following PR diff and produce a review.

Your output must be ONLY valid JSON matching this exact schema:
{
  "findings": [
    {
      "file": "path/to/file",
      "line_or_hunk": "line number or hunk description",
      "issue": "grounded description tied to the specific code",
      "severity": "low | medium | high | critical",
      "recommended_action": "approve | request_changes | escalate_to_human"
    }
  ]
}

Rules:
- Every finding must reference a specific file and line from the diff below -- never a vague or general claim.
- If the diff is clean with no real issues, return {"findings": []}.
- Do not invent problems that aren't actually in the diff.
- Do not include any text outside the JSON object.

Diff to review:

[PASTE YOUR DIFF HERE]
```

## Step 2: Save Claude's response

Copy the JSON Claude returns and save it to a file, e.g.:
```bash
evals/sample-runs/pr-XXXX-real-output.json
```

## Step 3: Run it through the real deterministic scoring code

```bash
python3 -c "
import json, sys
sys.path.insert(0, 'skills')
from risk_scoring import score

data = json.load(open('evals/sample-runs/pr-XXXX-real-output.json'))
scoring = score(data['findings'])
full_output = {**data, **scoring}
print(json.dumps(full_output, indent=2))
json.dump(full_output, open('evals/sample-runs/pr-XXXX-real-output.json', 'w'), indent=2)
"
```

## Step 4: Verify with the real eval script

For a seeded-bug PR:
```bash
python3 evals/run_eval.py pr-XXXX evals/sample-runs/pr-XXXX-real-output.json data/seeded-bugs/pr-XXXX-SEEDED-BUG.diff --expected-file path/to/file
```

For a clean PR:
```bash
python3 evals/run_eval.py pr-XXXX evals/sample-runs/pr-XXXX-real-output.json data/pr-XXXX.diff --clean
```

## Step 5 (optional): Get a release note too

Same pattern, second prompt in the same Claude.ai chat (so it has the
reviewer's findings as context):

```
You are acting as the release-manager agent defined in
agents/release-manager.md. Using the diff and your findings above,
draft a one-line release note. If overall_recommendation was
escalate_to_human, make sure the note does not imply the change is safe.

Return ONLY the release note text, nothing else.
```

## Why this counts as real evidence

Every finding Claude produces this way is genuine reasoning against the
actual diff — the same LLM, the same judgment task `agents/reviewer.md`
specifies, just invoked through the chat interface instead of the raw
API. The only thing this approach doesn't give you is automated,
programmatic timing/token-cost data — see `docs/impact-study.md`'s
"Honest limitations" section, which already documents this trade-off.

## What already exists using this method

The full holdout set (`pr-4179`, `pr-653`, `pr-3728`) was already
evaluated this way — see `evals/sample-runs/` for the saved outputs and
`docs/impact-study.md` Section 4 for the results.
