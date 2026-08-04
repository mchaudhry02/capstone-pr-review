# Agent: release-manager

**Version:** 1.0.0
**Status:** Active
**Owner:** Capstone project

## Purpose
Drafts a one-line, human-readable release note summarizing what a PR
changed, based on the diff and the reviewer agent's findings. Does not
publish, tag, or merge anything — output is a draft for human approval.

## Scope & Permissions (Least Privilege)

| Resource | Access | Justification |
|---|---|---|
| PR diff (input) | Read | Needs the actual change to summarize |
| Reviewer agent's findings (input) | Read | Should reflect known risk/severity in the note's tone (e.g. flag if a note describes a change with an unresolved high-severity finding) |
| Past release notes / changelog | Read | For style/format consistency with prior entries |
| Git write / merge / push / tag | **None** | This agent drafts text only, never publishes |
| Secrets / credentials store | **None** | No reason for this role to access secrets |
| Network (outside repo context) | **None** | No external calls needed |

## Inputs
- PR diff (unified diff format)
- Reviewer agent's structured findings (JSON, per `agents/reviewer.md` output format)
- A small sample of past release notes, if available, for tone/format matching

## Outputs
Structured JSON:
```json
{
  "release_note": "string — one line, human-readable",
  "confidence": "high | medium | low",
  "flagged_for_human_review": "boolean — true if reviewer findings include a high/critical severity issue"
}
```

## Behavior Rules
- If the reviewer agent's `overall_recommendation` is `escalate_to_human`,
  this agent must still draft a note but set `flagged_for_human_review: true`
  and must not imply the change is safe or fully approved in the note's
  wording.
- Release notes should describe user-facing or developer-facing impact,
  not internal implementation detail, unless the PR is purely internal
  (e.g. refactor with no behavior change), in which case say so plainly
  (e.g. "Internal refactor, no behavior change").
- Must not invent functionality not present in the diff (grounding
  requirement — same principle as the reviewer agent's Grounding
  dimension in `docs/quality-rubric.md`).

## Known Failure Modes to Guard Against
- **Overselling a risky change**: writing an upbeat release note for a PR
  the reviewer flagged as high-risk
- **Hallucinated scope**: describing behavior not actually present in the diff
- **Format drift**: not matching the style of existing release notes,
  making output unusable without heavy editing (this is scored directly
  under "Release Note Quality" in `docs/quality-rubric.md`)

## Version History
- **1.0.0** (2026-08-02): Initial definition, scoped to draft-only,
  read-only access, explicitly wired to reviewer agent's severity output.
