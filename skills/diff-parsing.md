# Skill: diff-parsing

**Version:** 1.0.0
**Used by:** planner, reviewer

## Purpose
Parses a raw unified diff into structured data: changed files, added/
removed line ranges, and the surrounding context lines needed to judge
intent (e.g. nearby comments).

## Input
Raw diff text.

## Output
```json
{
  "files": [
    {
      "path": "string",
      "added_lines": [{"line_number": "int", "content": "string"}],
      "removed_lines": [{"line_number": "int", "content": "string"}],
      "context_before": "string",
      "context_after": "string"
    }
  ]
}
```

## Why this is a separate skill, not baked into one agent
Both `planner` (to identify changed files/relevant tests) and `reviewer`
(to judge the actual change) need the diff parsed the same consistent
way. Keeping it as a shared skill avoids two different agents parsing
diffs slightly differently and disagreeing on what changed.

## Version History
- 1.0.0 (2026-08-02): Initial version.
