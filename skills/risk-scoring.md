# Skill: risk-scoring

**Version:** 1.0.0
**Used by:** reviewer

## Purpose
Applies `docs/quality-rubric.md` consistently to a set of findings,
producing a single `overall_risk_score` and `overall_recommendation`
instead of leaving that judgment ad hoc per-run.

## Input
```json
{
  "findings": [
    {"issue": "string", "severity": "low | medium | high | critical"}
  ]
}
```

## Output
```json
{
  "overall_risk_score": "low | medium | high | critical",
  "overall_recommendation": "approve | request_changes | escalate_to_human",
  "reasoning": "string — grounded in the specific findings, not generic"
}
```

## Scoring Logic
- Any single `critical` finding -> `overall_risk_score: critical`,
  `overall_recommendation: escalate_to_human`
- Any single `high` finding, no `critical` -> `overall_risk_score: high`,
  `overall_recommendation: escalate_to_human`
- Only `medium`/`low` findings -> `overall_risk_score` matches the highest
  present, `overall_recommendation: request_changes` if any medium exists,
  else `approve`
- No findings -> `overall_risk_score: low`, `overall_recommendation: approve`

## Why this is a separate skill, not baked into one agent
This directly targets the baseline weakness found in
`docs/baseline-metrics.md`: manual review consistently scored 1/2 on Risk
Flagging because severity/action wasn't stated consistently. Making this
a standalone, deterministic-ish skill (not left to free-form agent
judgment) makes the reviewer agent's output consistent and auditable run
to run, rather than a source of drift.

## Version History
- 1.0.0 (2026-08-02): Initial version, rules derived directly from
  baseline review's known weak point.
