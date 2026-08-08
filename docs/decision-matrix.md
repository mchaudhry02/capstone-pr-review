# Agent-vs-Deterministic-vs-Human Decision Matrix

For each step in the PR review pipeline, this documents whether it
belongs to an LLM agent, deterministic code, or a human checkpoint, and
why.

| Step | Current owner | Should it be? | Reasoning |
|---|---|---|---|
| Parse diff into structured chunks | `diff-parsing` skill (agent-invoked) | **Deterministic** (already is, functionally) | Parsing a unified diff's syntax is pure text processing — no judgment involved. Already implemented as a scoped skill, not free-form agent reasoning. |
| Retrieve relevant past context | `planner` agent + `search_context` MCP tool | **Deterministic tool + agent judgment on query formulation** | The retrieval mechanics (TF-IDF search) are deterministic code (`mcp/retrieval_server.py`). Deciding *what query to issue* still benefits from agent judgment about what's relevant to a specific diff. |
| Identify what changed and why (intent) | `reviewer` agent | **Agent** | Requires reading code in context, inferring intent from comments/naming, and judging whether implementation matches stated intent — genuinely ambiguous, judgment-heavy work. |
| Map severity + findings to a recommendation | `risk-scoring` skill (previously agent-invoked) | **Deterministic — CONVERTED** | See conversion below. The mapping rules (`critical` finding -> `escalate_to_human`, etc.) are fully specified, don't require reading code, and were already written as an explicit if/else table in `skills/risk-scoring.md`. There was no actual ambiguity left for an agent to resolve here. |
| Draft release note wording | `release-manager` agent | **Agent** | Requires natural-language summarization and tone-matching to past notes — genuinely generative, not rule-based. |
| Final merge approval | Human (via escalation) | **Human** | Per governance policy, no agent role has git write/merge access. This is a hard boundary, not a judgment call. |
| Detect a policy/tool-grant violation attempt | MCP server `TOOL_GRANTS` check | **Deterministic** | A static permission lookup — must never be left to agent judgment, since that's exactly the overreach this control exists to prevent. |

## Summary

Of 7 pipeline steps, **3 are (or now are) deterministic code**, **2 are
agent judgment**, **1 is a hybrid** (deterministic tool + agent query
formulation), and **1 is a hard human checkpoint**. This is a healthier
mix than an "agent does everything" design — it keeps LLM judgment
reserved for the steps that actually need it (reading intent, drafting
prose) and pushes everything else to cheaper, faster, more predictable
code.
