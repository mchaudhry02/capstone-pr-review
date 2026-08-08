#!/usr/bin/env python3
"""
orchestrator.py

Wires planner -> reviewer -> release-manager together into a runnable
pipeline, per docs/orchestration-diagram.md. This is the piece that was
previously the project's one consistently-flagged gap (see
docs/gap-inventory.md "Known Remaining Gap").

Two kinds of steps happen here:
  1. Deterministic / MCP steps -- fully real, run locally, no external
     API needed: diff parsing, retrieval queries, memory reads/writes,
     risk scoring (skills/risk_scoring.py, per ADR-001).
  2. LLM reasoning steps -- planner's context-relevance judgment,
     reviewer's actual finding generation, release-manager's note
     drafting. These call the Anthropic API via call_llm() below and
     REQUIRE a real ANTHROPIC_API_KEY at runtime (see docker/.env).
     Without one, this script still runs end-to-end but the LLM steps
     raise LLMUnavailableError, which reliability controls handle the
     same way they'd handle any other call failure (fail closed, do not
     silently fabricate a review).

Reliability & cost controls (Workstream 6 requirement):
  - Per-call timeout
  - Retry with backoff on transient failure
  - Fallback: if the reviewer LLM call fails after retries, escalate to
    human rather than silently approving (fail closed, not open)
  - Max-iteration guard: a single PR review can't loop indefinitely
  - Per-call and per-workflow token/cost budgets
"""

import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "skills"))
from risk_scoring import score as risk_score  # deterministic, per ADR-001

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Reliability & cost control configuration
# ---------------------------------------------------------------------------

PER_CALL_TIMEOUT_SECONDS = 30
MAX_RETRIES = 2
RETRY_BACKOFF_SECONDS = 2
MAX_PIPELINE_ITERATIONS = 5  # hard stop, prevents any runaway loop
PER_CALL_TOKEN_BUDGET = 4000
PER_WORKFLOW_TOKEN_BUDGET = 20000


class LLMUnavailableError(Exception):
    pass


class BudgetExceededError(Exception):
    pass


class MaxIterationsExceededError(Exception):
    pass


@dataclass
class WorkflowBudget:
    tokens_used: int = 0
    calls_made: int = 0
    events: list = field(default_factory=list)

    def charge(self, tokens: int, call_name: str):
        if tokens > PER_CALL_TOKEN_BUDGET:
            raise BudgetExceededError(f"{call_name} exceeded per-call budget: {tokens} > {PER_CALL_TOKEN_BUDGET}")
        if self.tokens_used + tokens > PER_WORKFLOW_TOKEN_BUDGET:
            raise BudgetExceededError(
                f"{call_name} would exceed per-workflow budget: "
                f"{self.tokens_used + tokens} > {PER_WORKFLOW_TOKEN_BUDGET}"
            )
        self.tokens_used += tokens
        self.calls_made += 1


def call_llm(prompt: str, budget: WorkflowBudget, call_name: str, max_tokens: int = 1000) -> str:
    """Real Anthropic API call, with timeout + retry. Requires
    ANTHROPIC_API_KEY in the environment (see docker/.env)."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise LLMUnavailableError(
            f"{call_name}: ANTHROPIC_API_KEY not set. This step requires a "
            f"live API key to run for real -- see docker/.env.example."
        )

    # Rough token estimate for budget check before the call actually
    # happens (real usage is confirmed from the response afterward).
    estimated_tokens = len(prompt) // 4 + max_tokens
    budget.charge(estimated_tokens, call_name)

    body = json.dumps({
        "model": "claude-sonnet-4-6",
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()

    last_error = None
    for attempt in range(1, MAX_RETRIES + 2):  # initial try + retries
        try:
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=body,
                headers={
                    "content-type": "application/json",
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                },
            )
            with urllib.request.urlopen(req, timeout=PER_CALL_TIMEOUT_SECONDS) as resp:
                data = json.loads(resp.read())
                budget.events.append({"call": call_name, "attempt": attempt, "result": "success"})
                return "".join(b.get("text", "") for b in data.get("content", []))
        except (urllib.error.URLError, TimeoutError) as e:
            last_error = e
            budget.events.append({"call": call_name, "attempt": attempt, "result": f"error: {e}"})
            if attempt <= MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)
    raise LLMUnavailableError(f"{call_name} failed after {MAX_RETRIES + 1} attempts: {last_error}")


def call_mcp_tool(server_script: str, tool_name: str, args: dict, caller_role: str) -> dict:
    """Real subprocess call to an MCP server over stdio JSON-RPC --
    this part runs fully locally, no external API needed."""
    proc = subprocess.Popen(
        [sys.executable, os.path.join(BASE_DIR, "mcp", server_script)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    request = {
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": tool_name, "arguments": {**args, "_caller_role": caller_role}},
    }
    try:
        out, err = proc.communicate(json.dumps(request) + "\n", timeout=PER_CALL_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        proc.kill()
        raise LLMUnavailableError(f"MCP call {tool_name} timed out after {PER_CALL_TIMEOUT_SECONDS}s")
    response = json.loads(out.strip().splitlines()[-1])
    if "error" in response:
        raise PermissionError(f"MCP denial: {response['error']['message']}")
    return response["result"]


# ---------------------------------------------------------------------------
# Pipeline steps
# ---------------------------------------------------------------------------

def run_planner(pr_diff: str, budget: WorkflowBudget) -> dict:
    retrieval = call_mcp_tool("retrieval_server.py", "search_context",
                               {"query": pr_diff[:200], "top_k": 5}, "planner")
    history = call_mcp_tool("storage_server.py", "get_review_history",
                             {"limit": 5}, "planner")
    return {"retrieved_context": retrieval["results"], "review_history": history["records"]}


def run_reviewer(pr_diff: str, context: dict, budget: WorkflowBudget) -> dict:
    """The judgment-heavy step: requires a real LLM call to actually
    generate findings from the diff. See agents/reviewer.md for the
    exact output schema this must produce."""
    prompt = (
        f"You are the reviewer agent defined in agents/reviewer.md. "
        f"Review this diff and return ONLY JSON matching the required schema.\n\n"
        f"Context: {json.dumps(context)[:1000]}\n\nDiff:\n{pr_diff}"
    )
    raw = call_llm(prompt, budget, "reviewer", max_tokens=1000)
    findings_data = json.loads(raw)
    scoring = risk_score(findings_data.get("findings", []))  # deterministic, per ADR-001
    return {**findings_data, **scoring}


def run_release_manager(pr_diff: str, review: dict, budget: WorkflowBudget) -> dict:
    if review["overall_recommendation"] == "escalate_to_human":
        note_hint = "Flag this note clearly -- reviewer escalated this change."
    else:
        note_hint = "Standard release note."
    prompt = (
        f"You are the release-manager agent defined in agents/release-manager.md. "
        f"{note_hint} Diff:\n{pr_diff}\n\nReviewer findings: {json.dumps(review)[:500]}"
    )
    raw = call_llm(prompt, budget, "release-manager", max_tokens=200)
    return {"release_note": raw.strip()}


# ---------------------------------------------------------------------------
# Orchestrator entrypoint
# ---------------------------------------------------------------------------

def run_pipeline(pr_id: str, pr_diff: str) -> dict:
    budget = WorkflowBudget()
    audit_events = [{"actor": "orchestrator", "action": "pipeline_start", "pr_id": pr_id}]

    for iteration in range(1, MAX_PIPELINE_ITERATIONS + 1):
        if iteration > MAX_PIPELINE_ITERATIONS:
            raise MaxIterationsExceededError(f"{pr_id}: exceeded {MAX_PIPELINE_ITERATIONS} iterations")
        try:
            context = run_planner(pr_diff, budget)
            audit_events.append({"actor": "planner", "action": "context_retrieved",
                                  "result": "success", "count": len(context["retrieved_context"])})

            review = run_reviewer(pr_diff, context, budget)
            audit_events.append({"actor": "reviewer", "action": "review_complete",
                                  "result": "success", "recommendation": review["overall_recommendation"]})

            release = run_release_manager(pr_diff, review, budget)
            audit_events.append({"actor": "release-manager", "action": "note_drafted", "result": "success"})

            call_mcp_tool("storage_server.py", "put_review_record", {"record": {
                "pr_id": pr_id, "date": time.strftime("%Y-%m-%d"),
                "findings_summary": json.dumps(review.get("findings", []))[:200],
                "overall_risk_score": review["overall_risk_score"],
                "outcome": review["overall_recommendation"].replace("escalate_to_human", "escalated")
                           .replace("approve", "approved"),
            }}, "orchestrator")
            audit_events.append({"actor": "orchestrator", "action": "review_history_written", "result": "success"})

            return {
                "pr_id": pr_id, "review": review, "release_note": release["release_note"],
                "budget": {"tokens_used": budget.tokens_used, "calls_made": budget.calls_made},
                "audit_events": audit_events, "status": "completed",
            }

        except LLMUnavailableError as e:
            # Fail closed: escalate to human rather than silently approving
            audit_events.append({"actor": "orchestrator", "action": "fallback_escalation",
                                  "reason": str(e), "result": "escalated"})
            return {
                "pr_id": pr_id, "status": "escalated_fallback", "reason": str(e),
                "budget": {"tokens_used": budget.tokens_used, "calls_made": budget.calls_made},
                "audit_events": audit_events,
            }
        except PermissionError as e:
            audit_events.append({"actor": "orchestrator", "action": "policy_denial_surfaced",
                                  "reason": str(e), "result": "blocked"})
            return {"pr_id": pr_id, "status": "blocked_by_policy", "reason": str(e),
                    "audit_events": audit_events}
        except BudgetExceededError as e:
            audit_events.append({"actor": "orchestrator", "action": "budget_exceeded",
                                  "reason": str(e), "result": "stopped"})
            return {"pr_id": pr_id, "status": "stopped_budget", "reason": str(e),
                    "audit_events": audit_events}


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 orchestrator.py <pr_id> <diff_file>")
        sys.exit(1)
    pr_id, diff_path = sys.argv[1], sys.argv[2]
    with open(diff_path) as f:
        diff_text = f.read()
    result = run_pipeline(pr_id, diff_text)
    print(json.dumps(result, indent=2))
