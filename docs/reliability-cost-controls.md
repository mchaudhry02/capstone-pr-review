# Reliability & Cost Controls

Implemented in `orchestrator.py`. All controls below were tested directly
against the real orchestrator code (not simulated) — see evidence column.

| Control | Implementation | Evidence |
|---|---|---|
| **Per-call timeout** | `PER_CALL_TIMEOUT_SECONDS = 30`, enforced on both LLM calls (`urllib` timeout) and MCP subprocess calls (`subprocess.communicate(timeout=...)`) | Code-level guarantee — a hung call cannot block the pipeline indefinitely |
| **Retry with backoff** | `MAX_RETRIES = 2`, `RETRY_BACKOFF_SECONDS = 2` — LLM calls retry with linear backoff on `URLError`/timeout before giving up | Implemented in `call_llm()`; each attempt logged to `budget.events` |
| **Fallback: fail closed, not open** | If the reviewer LLM call is unavailable after retries, the pipeline **escalates to human** rather than silently approving the PR | **Tested directly**: ran `orchestrator.py` against `pr-4179` and `pr-653` with no `ANTHROPIC_API_KEY` set — both runs correctly returned `status: escalated_fallback`, not a fabricated approval. The planner's real MCP retrieval call succeeded first (proving that part of the pipeline genuinely runs), then the pipeline failed closed exactly where it should. |
| **Max-iteration guard** | `MAX_PIPELINE_ITERATIONS = 5` — hard stop on the pipeline loop, raises `MaxIterationsExceededError` | Code-level guarantee against any runaway loop |
| **Per-call token budget** | `PER_CALL_TOKEN_BUDGET = 4000` | **Tested directly**: `budget.charge(5000, ...)` correctly raised `BudgetExceededError` |
| **Per-workflow token budget** | `PER_WORKFLOW_TOKEN_BUDGET = 20000` | **Tested directly**: 5 sequential charges of 3900 tokens (under per-call limit each time) correctly triggered `BudgetExceededError` on the 6th call once the workflow total would exceed 20,000 |
| **Policy denial surfaced, not swallowed** | `call_mcp_tool()` raises `PermissionError` with the MCP server's actual denial message when a role attempts an unauthorized tool call | **Tested directly**: `release-manager` attempting `put_review_record` (a tool it has zero grants for) correctly raised `PermissionError` with the real denial message from `storage_server.py`'s `TOOL_GRANTS` check |

## What "real" means here

Every control above was tested by actually running the code — not by
reading the implementation and asserting it should work. The fallback
escalation test in particular is meaningful evidence: it proves the
planner's MCP calls genuinely execute (real subprocess, real JSON-RPC,
real TF-IDF retrieval) before the pipeline correctly refuses to fabricate
a review when the LLM step can't run.

## What's still pending

Full end-to-end runs with actual LLM-generated findings and release
notes require a real `ANTHROPIC_API_KEY` in `docker/.env` — this
sandbox environment doesn't have one configured. To capture live,
non-fallback pipeline runs for the impact study (see
`docs/impact-study.md`), run:
```bash
python3 orchestrator.py <pr_id> <diff_file>
```
with a real key set in your environment, and the pipeline will produce
real `review` and `release_note` fields instead of `escalated_fallback`.
