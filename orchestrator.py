#!/usr/bin/env python3
"""
orchestrator.py -- runs the PR-review pipeline (planner -> reviewer ->
release-manager) WITHOUT an Anthropic API key and WITHOUT the Claude Code
CLI. Deterministic steps (loading the diff, calling the MCP servers,
enforcing the routing rules, writing memory) run locally in this script.
LLM steps print a ready-to-paste prompt; you paste it into the Claude.ai
chat window you're already using, paste the JSON response back into this
terminal, and the pipeline continues.

Usage:
    python3 orchestrator.py --pr data/pr-688.diff
    python3 orchestrator.py --pr data/pr-688.diff --dry-run          # no pasting, canned fixture responses
    python3 orchestrator.py --pr data/pr-688.diff --dry-run --overreach-demo  # governance-violation demo

Why this shape: docs/orchestration-diagram.md's Routing Rules say routing
decisions are "enforced by the orchestrator, not left to agent discretion."
That's true whether the agent is an API call, a CLI subagent, or -- as
here -- a human relaying text to and from a chat window. The orchestrator
is the only thing with tool access (MCP servers) and the only thing with
write access to memory, exactly as docs/orchestration-diagram.md's
Routing-and-Tool-Grant Map specifies, regardless of how the LLM step
itself is invoked.
"""

import argparse
import glob
import json
import os
import subprocess
import sys
import re
import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MCP_DIR = os.path.join(BASE_DIR, "mcp")
DATA_DIR = os.path.join(BASE_DIR, "data")
WORKSPACE_DIR = os.path.join(BASE_DIR, "workspace")
FIXTURES_PATH = os.path.join(BASE_DIR, "mcp", "dry_run_fixtures.json")

AGENTS_DIR = os.path.join(BASE_DIR, "agents")


# ---------------------------------------------------------------------------
# MCP calls (deterministic -- the only thing in this script that touches
# tools/memory; no subagent gets direct access, matching the tool-grant map)
# ---------------------------------------------------------------------------

def call_mcp_tool(server_filename, tool_name, arguments, caller_role, timeout=30):
    server_path = os.path.join(MCP_DIR, server_filename)
    req = {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
           "params": {"name": tool_name, "arguments": {**arguments, "_caller_role": caller_role}}}
    proc = subprocess.run(["python3", server_path], input=json.dumps(req) + "\n",
                           capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(f"{server_filename} exited {proc.returncode}: {proc.stderr.strip()}")
    line = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
    if not line:
        raise RuntimeError(f"{server_filename} produced no output. stderr: {proc.stderr.strip()}")
    resp = json.loads(line)
    if "error" in resp:
        raise RuntimeError(f"{server_filename}.{tool_name} error: {resp['error']}")
    return resp["result"]


def retrieval_query(query, top_k=5):
    return call_mcp_tool("retrieval_server.py", "search_context",
                          {"query": query, "top_k": top_k}, caller_role="orchestrator")


def write_review_record(record):
    return call_mcp_tool("storage_server.py", "put_review_record",
                          {"record": record}, caller_role="orchestrator")


def read_review_history(pr_id=None, limit=5):
    args = {"limit": limit}
    if pr_id:
        args["pr_id"] = pr_id
    return call_mcp_tool("storage_server.py", "get_review_history", args, caller_role="orchestrator")


# ---------------------------------------------------------------------------
# Diff parsing (reuse the same file-split logic conceptually described in
# skills/diff-parsing.md, just enough of it to hand agents structured input)
# ---------------------------------------------------------------------------

def split_diff_by_file(diff_text):
    files = re.findall(r"^diff --git a/(.+?) b/\1$", diff_text, flags=re.MULTILINE)
    return files


# ---------------------------------------------------------------------------
# Prompt builders -- each embeds the matching agents/*.md spec verbatim so
# the persona pasted into Claude.ai matches this repo's versioned agent
# definition exactly, not a paraphrase of it.
# ---------------------------------------------------------------------------

def _read_agent_spec(filename):
    with open(os.path.join(AGENTS_DIR, filename), "r", encoding="utf-8") as f:
        return f.read()


def build_planner_prompt(diff_text, changed_files, retrieved_context):
    spec = _read_agent_spec("planner.md")
    ctx_block = json.dumps(retrieved_context["results"], indent=2) if retrieved_context["results"] else "[] (retrieval index found nothing above the relevance threshold for this diff -- report this honestly, do not invent context)"
    return f"""You are the `planner` agent in a governed multi-agent PR-review pipeline. Follow this agent definition exactly:

{spec}

---
## Task input

Changed files in this PR: {json.dumps(changed_files)}

Pre-fetched retrieval results (the orchestrator queried the MCP-backed retrieval store on your behalf, since you're being run via chat paste rather than direct tool access -- treat this exactly as if you had called the retrieval tool yourself; note in `retrieved_context` if it's empty or not relevant):
{ctx_block}

PR diff:
```diff
{diff_text}
```

---
Respond with ONLY the JSON routing plan matching the Outputs schema above. No prose before or after, no markdown code fence -- raw JSON only, so it can be parsed directly."""


def build_reviewer_prompt(diff_text, routing_plan):
    spec = _read_agent_spec("reviewer.md")
    return f"""You are the `reviewer` agent in a governed multi-agent PR-review pipeline. Follow this agent definition exactly:

{spec}

---
## Task input

Context handed to you by the planner agent: {routing_plan.get("context_handoff", {}).get("reviewer", "(none provided)")}

Planner's routing heuristic (NOT authoritative -- your own `overall_risk_score` is the real judgment): {routing_plan.get("estimated_risk_area", "unknown")}

Relevant test files identified by the planner: {json.dumps(routing_plan.get("relevant_test_files", []))}

Retrieved context handed to you by the planner:
{json.dumps(routing_plan.get("retrieved_context", []), indent=2)}

PR diff:
```diff
{diff_text}
```

---
Respond with ONLY the JSON findings matching the Outputs schema above. No prose before or after, no markdown code fence -- raw JSON only, so it can be parsed directly."""


def build_release_manager_prompt(diff_text, reviewer_output, past_notes):
    spec = _read_agent_spec("release-manager.md")
    return f"""You are the `release-manager` agent in a governed multi-agent PR-review pipeline. Follow this agent definition exactly:

{spec}

---
## Task input

Reviewer agent's findings (this is ground truth for tone -- do not contradict it):
{json.dumps(reviewer_output, indent=2)}

Sample past release notes for style/format matching:
{json.dumps(past_notes, indent=2) if past_notes else "(none available yet -- this may be one of the first entries)"}

PR diff:
```diff
{diff_text}
```

---
Respond with ONLY the JSON output matching the Outputs schema above. No prose before or after, no markdown code fence -- raw JSON only, so it can be parsed directly."""


# ---------------------------------------------------------------------------
# Paste I/O
# ---------------------------------------------------------------------------

def print_prompt_for_pasting(label, prompt_text):
    print("\n" + "=" * 78)
    print(f" COPY EVERYTHING BELOW THIS LINE  --  paste into your Claude.ai chat  --  [{label}]")
    print("=" * 78)
    print(prompt_text)
    print("=" * 78)
    print(f" COPY EVERYTHING ABOVE THIS LINE  --  [{label}]")
    print("=" * 78)


def capture_pasted_response(label):
    print(f"\nPaste the {label}'s JSON response below.")
    print("When done, press Ctrl+D (Ctrl+Z then Enter on Windows) on its own line to submit.\n")
    lines = []
    try:
        while True:
            lines.append(input())
    except EOFError:
        pass
    return "\n".join(lines)


def extract_json(raw_text):
    """Best-effort JSON extraction: strips markdown fences, falls back to
    the outermost {...} span if the model added any stray prose."""
    text = raw_text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(text[start:end + 1])
    raise ValueError(f"Could not parse JSON from pasted response:\n{raw_text[:500]}")


def get_response(label, prompt_text, dry_run_key, fixtures):
    if fixtures is not None:
        print(f"\n[dry-run] Using canned fixture response for: {label}")
        return fixtures[dry_run_key]
    print_prompt_for_pasting(label, prompt_text)
    raw = capture_pasted_response(label)
    return extract_json(raw)


# ---------------------------------------------------------------------------
# Governance enforcement (docs/orchestration-diagram.md Routing Rules --
# these checks run regardless of dry-run/live mode, on real parsed output)
# ---------------------------------------------------------------------------

def enforce_reviewer_invocation(routing_plan):
    """Rule 2: planner must invoke reviewer -- not optional, cannot be
    skipped by the planner's own decision. If the planner (human-relayed
    or not) tries to route around it, the orchestrator forcibly reinstates
    it and logs the violation rather than silently complying."""
    invoked = routing_plan.get("subagents_to_invoke", [])
    if "reviewer" not in invoked:
        print("\n" + "!" * 78)
        print(" GOVERNANCE VIOLATION DETECTED")
        print(f" planner's routing plan omitted 'reviewer' from subagents_to_invoke: {invoked}")
        print(" This violates docs/orchestration-diagram.md Routing Rule #2")
        print(" (reviewer is mandatory and cannot be skipped by agent discretion).")
        print(" Orchestrator is forcibly reinstating 'reviewer' and continuing.")
        print("!" * 78 + "\n")
        routing_plan["subagents_to_invoke"] = list(set(invoked) | {"reviewer"})
        routing_plan.setdefault("_governance_flags", []).append(
            "planner attempted to skip reviewer -- forcibly reinstated by orchestrator"
        )
    return routing_plan


def validate_schema(obj, required_keys, label):
    missing = [k for k in required_keys if k not in obj]
    if missing:
        raise ValueError(f"{label} output is missing required keys: {missing}. Got: {json.dumps(obj)[:300]}")


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pr", required=True, help="Path to a PR diff file, e.g. data/pr-688.diff")
    ap.add_argument("--dry-run", action="store_true",
                     help="Skip pasting entirely; use canned fixture responses from mcp/dry_run_fixtures.json")
    ap.add_argument("--overreach-demo", action="store_true",
                     help="With --dry-run, use the fixture where the planner tries to skip reviewer, to demonstrate governance enforcement")
    ap.add_argument("--skip-write", action="store_true", help="Don't write the result to persistent memory")
    args = ap.parse_args()

    diff_path = args.pr if os.path.isabs(args.pr) else os.path.join(BASE_DIR, args.pr)
    if not os.path.exists(diff_path):
        print(f"error: no such file: {diff_path}", file=sys.stderr)
        sys.exit(1)
    with open(diff_path, "r", encoding="utf-8", errors="replace") as f:
        diff_text = f.read()

    pr_id_match = re.search(r"pr-(\d+)", os.path.basename(diff_path))
    pr_id = pr_id_match.group(1) if pr_id_match else os.path.basename(diff_path)

    fixtures = None
    if args.dry_run:
        with open(FIXTURES_PATH, "r", encoding="utf-8") as f:
            all_fixtures = json.load(f)
        fixtures = all_fixtures["overreach_demo"] if args.overreach_demo else all_fixtures["normal"]

    print(f"\n=== PR-Review Pipeline: pr-{pr_id} ===")
    print(f"Diff: {diff_path}")
    print(f"Mode: {'DRY-RUN (canned fixtures)' if args.dry_run else 'LIVE (paste into Claude.ai)'}"
          + (" [overreach demo]" if args.overreach_demo else ""))

    changed_files = split_diff_by_file(diff_text)
    print(f"\n[orchestrator] Parsed diff -> {len(changed_files)} changed file(s): {changed_files}")

    # --- Step 1: retrieval (deterministic, MCP-backed, done FOR the planner
    # since the planner here is a chat persona without direct tool access) ---
    query = " ".join(changed_files[:3]) or "PR review"
    print(f"[orchestrator] Querying pr-review-retrieval MCP server: {query!r}")
    retrieved = retrieval_query(query, top_k=5)
    print(f"[orchestrator] Retrieval returned {len(retrieved['results'])} result(s) "
          f"(of {retrieved['total_indexed_docs']} indexed docs)")

    # --- Step 2: planner ---
    planner_prompt = build_planner_prompt(diff_text, changed_files, retrieved)
    routing_plan = get_response("planner", planner_prompt, "planner", fixtures)
    validate_schema(routing_plan, ["subagents_to_invoke", "context_handoff"], "planner")
    routing_plan = enforce_reviewer_invocation(routing_plan)
    print(f"\n[orchestrator] Planner routing plan accepted. Invoking: {routing_plan['subagents_to_invoke']}")

    # --- Step 3: reviewer (mandatory, per Routing Rule #2) ---
    reviewer_prompt = build_reviewer_prompt(diff_text, routing_plan)
    reviewer_output = get_response("reviewer", reviewer_prompt, "reviewer", fixtures)
    validate_schema(reviewer_output, ["findings", "overall_risk_score", "overall_recommendation"], "reviewer")
    print(f"\n[orchestrator] Reviewer done. overall_risk_score={reviewer_output['overall_risk_score']}, "
          f"overall_recommendation={reviewer_output['overall_recommendation']}, "
          f"{len(reviewer_output['findings'])} finding(s)")

    # --- Step 4: release-manager (only runs after reviewer, per Routing Rule #3) ---
    past_history = read_review_history(limit=3)
    past_notes = [r.get("findings_summary") for r in past_history["records"]]
    rm_prompt = build_release_manager_prompt(diff_text, reviewer_output, past_notes)
    rm_output = get_response("release-manager", rm_prompt, "release_manager", fixtures)
    validate_schema(rm_output, ["release_note", "confidence", "flagged_for_human_review"], "release-manager")
    print(f"\n[orchestrator] Release note drafted: \"{rm_output['release_note']}\" "
          f"(flagged_for_human_review={rm_output['flagged_for_human_review']})")

    # --- Step 5: assemble final output + write memory (orchestrator-only, per tool-grant map) ---
    final_output = {
        "pr_id": pr_id,
        "changed_files": changed_files,
        "routing_plan": routing_plan,
        "review": reviewer_output,
        "release_note": rm_output,
        "governance_flags": routing_plan.get("_governance_flags", []),
    }

    if not args.skip_write:
        record = {
            "pr_id": f"pr-{pr_id}",
            "date": datetime.date.today().isoformat(),
            "findings_summary": "; ".join(f["issue"] for f in reviewer_output["findings"][:3]) or "No findings",
            "overall_risk_score": reviewer_output["overall_risk_score"],
            "outcome": reviewer_output["overall_recommendation"],
        }
        write_result = write_review_record(record)
        if write_result.get("ok"):
            print(f"\n[orchestrator] Wrote review record to persistent memory (review-history.jsonl)")
        else:
            print(f"\n[orchestrator] WARNING: failed to write memory record: {write_result.get('error')}")

    os.makedirs(WORKSPACE_DIR, exist_ok=True)
    out_path = os.path.join(WORKSPACE_DIR, f"pr-{pr_id}-result.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2)

    print(f"\n=== Final Output ===")
    print(json.dumps(final_output, indent=2))
    print(f"\nSaved to {os.path.relpath(out_path, BASE_DIR)}")


if __name__ == "__main__":
    main()