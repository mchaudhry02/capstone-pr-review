#!/usr/bin/env python3
"""
pr-review-storage MCP server

Exposes the pipeline's persistent memory (memory/store/*.jsonl) as an
MCP-style tool server over stdio JSON-RPC 2.0, so agents access memory
through a scoped tool contract instead of raw filesystem access.

PROTOCOL NOTE: this container has no network access, so the official
`mcp` Python SDK (which is installed via pip from PyPI) can't be
installed here. This server implements the same request/response shape
the SDK would give you (initialize / tools/list / tools/call over
newline-delimited JSON-RPC 2.0 on stdin/stdout) using only the standard
library. In a networked environment, swap this for:
    pip install mcp
    from mcp.server.fastmcp import FastMCP
and re-register the same tool functions below under that SDK — the
tool names, schemas, and permission boundaries do not need to change.

Run standalone for a smoke test:
    python3 mcp/storage_server.py --selftest
"""

import json
import sys
import os
import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE_DIR = os.path.join(BASE_DIR, "memory", "store")
REVIEW_HISTORY_PATH = os.path.join(STORE_DIR, "review-history.jsonl")
CALIBRATION_LOG_PATH = os.path.join(STORE_DIR, "calibration-log.jsonl")
# Proposals, not direct writes -- see governance note on calibration-log below.
CALIBRATION_PROPOSALS_PATH = os.path.join(STORE_DIR, "calibration-proposals.jsonl")

# ---------------------------------------------------------------------------
# Schema definitions
# ---------------------------------------------------------------------------
# These mirror memory/architecture-notes.md exactly. Every record written
# through this server is validated against these schemas before being
# appended -- malformed records are rejected rather than silently stored,
# so the audit trail (Workstream 4) stays trustworthy.

REVIEW_RECORD_SCHEMA = {
    "type": "object",
    "required": ["pr_id", "date", "findings_summary", "overall_risk_score", "outcome"],
    "properties": {
        "pr_id": {"type": "string"},
        "date": {"type": "string", "format": "ISO-8601"},
        "findings_summary": {"type": "string"},
        "overall_risk_score": {"enum": ["low", "medium", "high", "critical"]},
        "outcome": {"enum": ["approved", "escalated", "request_changes"]},
    },
    "classification": "internal",
    # internal = derived from public PR diffs but treated as the pipeline's
    # own audit/judgment data, not republished as-is; never contains secrets
    # or raw diffs (see architecture-notes.md "What is explicitly NOT stored").
}

CALIBRATION_RECORD_SCHEMA = {
    "type": "object",
    "required": ["date", "change", "reason", "evidence_source"],
    "properties": {
        "date": {"type": "string", "format": "ISO-8601"},
        "change": {"type": "string"},
        "reason": {"type": "string"},
        "evidence_source": {"type": "string"},  # file path -- traceability anchor
    },
    "classification": "internal",
}

CALIBRATION_PROPOSAL_SCHEMA = dict(CALIBRATION_RECORD_SCHEMA)
CALIBRATION_PROPOSAL_SCHEMA["required"] = CALIBRATION_RECORD_SCHEMA["required"] + ["proposed_by"]

# ---------------------------------------------------------------------------
# Tool grant boundaries (mirrors docs/orchestration-diagram.md's
# Routing-and-Tool-Grant Map -- this is the file that map says gets "wired
# into actual MCP server configuration" in Workstream 3/4).
#
#   orchestrator : read review-history, WRITE review-history
#   planner      : read review-history (context only)
#   reviewer     : read review-history (consistency); produces the record
#                  content, but does NOT call put_review_record directly --
#                  it hands findings to the orchestrator, which is the only
#                  role with write access. This resolves a wording mismatch
#                  between architecture-notes.md ("reviewer... writes") and
#                  the orchestration diagram's tool-grant table (orchestrator
#                  writes) in favor of the diagram, since that table is the
#                  declared authoritative Workstream 3 artifact.
#   release-manager: no memory access beyond what's handed to it in context
#
# calibration-log.jsonl is NOT directly writable by any agent. Agents may
# only *propose* a calibration change (put_calibration_proposal), which is
# appended to calibration-proposals.jsonl. A human promotes an accepted
# proposal into calibration-log.jsonl out of band. This keeps the audit
# trail human-approved by construction rather than by policy alone --
# the enforceable version of least privilege the diagram asks for.
# ---------------------------------------------------------------------------

TOOL_GRANTS = {
    "orchestrator": {"get_review_history", "put_review_record", "get_calibration_log"},
    "planner": {"get_review_history", "get_calibration_log"},
    "reviewer": {"get_review_history", "get_calibration_log"},
    "release-manager": set(),  # no memory-store tools; works only from handed-in context
}


def _read_jsonl(path):
    if not os.path.exists(path):
        return []
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                sys.stderr.write(f"[storage_server] WARNING: skipping malformed line {line_num} in {path}: {e}\n")
    return records


def _append_jsonl(path, record):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _validate(record, schema):
    missing = [k for k in schema["required"] if k not in record]
    if missing:
        return f"missing required fields: {missing}"
    for key, spec in schema["properties"].items():
        if key not in record:
            continue
        if "enum" in spec and record[key] not in spec["enum"]:
            return f"field '{key}' must be one of {spec['enum']}, got {record[key]!r}"
        if spec.get("type") == "string" and not isinstance(record[key], str):
            return f"field '{key}' must be a string"
    return None


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def tool_get_review_history(args):
    """Read review history. Optional filter by pr_id, optional limit.
    Citation/traceability: every record's pr_id maps 1:1 to a diff file
    under data/pr-{pr_id}.diff or data/seeded bugs/pr-{pr_id}-SEEDED-BUG.diff,
    so any caller can trace a memory record back to source."""
    records = _read_jsonl(REVIEW_HISTORY_PATH)
    pr_id = args.get("pr_id")
    if pr_id:
        records = [r for r in records if r.get("pr_id") == pr_id]
    limit = args.get("limit")
    if isinstance(limit, int):
        records = records[-limit:]
    return {"records": records, "count": len(records), "source": os.path.relpath(REVIEW_HISTORY_PATH, BASE_DIR)}


def tool_put_review_record(args):
    record = args.get("record")
    if not isinstance(record, dict):
        return {"ok": False, "error": "'record' must be an object"}
    err = _validate(record, REVIEW_RECORD_SCHEMA)
    if err:
        return {"ok": False, "error": err}
    _append_jsonl(REVIEW_HISTORY_PATH, record)
    return {"ok": True, "stored": record}


def tool_get_calibration_log(args):
    records = _read_jsonl(CALIBRATION_LOG_PATH)
    limit = args.get("limit")
    if isinstance(limit, int):
        records = records[-limit:]
    return {"records": records, "count": len(records), "source": os.path.relpath(CALIBRATION_LOG_PATH, BASE_DIR)}


def tool_put_calibration_proposal(args):
    """Agents propose calibration changes; only a human promotes a proposal
    into calibration-log.jsonl. This tool never touches calibration-log.jsonl
    directly -- see the governance note above TOOL_GRANTS."""
    record = args.get("record")
    if not isinstance(record, dict):
        return {"ok": False, "error": "'record' must be an object"}
    record.setdefault("date", datetime.date.today().isoformat())
    err = _validate(record, CALIBRATION_PROPOSAL_SCHEMA)
    if err:
        return {"ok": False, "error": err}
    _append_jsonl(CALIBRATION_PROPOSALS_PATH, record)
    return {"ok": True, "stored": record, "note": "proposal logged; requires human promotion into calibration-log.jsonl"}


TOOLS = {
    "get_review_history": {
        "fn": tool_get_review_history,
        "description": "Read past PR review outcomes. Read access: orchestrator, planner, reviewer.",
        "input_schema": {"type": "object", "properties": {
            "pr_id": {"type": "string", "description": "optional filter"},
            "limit": {"type": "integer", "description": "optional, most-recent N"},
        }},
        "output_classification": "internal",
    },
    "put_review_record": {
        "fn": tool_put_review_record,
        "description": "Append a completed review outcome to persistent memory. Write access: orchestrator only.",
        "input_schema": {"type": "object", "required": ["record"], "properties": {
            "record": REVIEW_RECORD_SCHEMA,
        }},
        "output_classification": "internal",
    },
    "get_calibration_log": {
        "fn": tool_get_calibration_log,
        "description": "Read the log of prompt/routing/tool-grant changes made because of eval evidence. Read access: orchestrator, planner, reviewer.",
        "input_schema": {"type": "object", "properties": {
            "limit": {"type": "integer", "description": "optional, most-recent N"},
        }},
        "output_classification": "internal",
    },
    "put_calibration_proposal": {
        "fn": tool_put_calibration_proposal,
        "description": "Propose a calibration change for human review (does not write calibration-log.jsonl directly).",
        "input_schema": {"type": "object", "required": ["record"], "properties": {
            "record": CALIBRATION_PROPOSAL_SCHEMA,
        }},
        "output_classification": "internal",
    },
}


def handle_request(req):
    method = req.get("method")
    req_id = req.get("id")
    params = req.get("params", {}) or {}

    if method == "initialize":
        result = {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": "pr-review-storage", "version": "1.0.0"},
            "capabilities": {"tools": {}},
        }
    elif method == "tools/list":
        result = {"tools": [
            {"name": name, "description": t["description"], "inputSchema": t["input_schema"]}
            for name, t in TOOLS.items()
        ]}
    elif method == "tools/call":
        name = params.get("name")
        args = params.get("arguments", {}) or {}
        caller_role = args.pop("_caller_role", None)  # optional, for allow-list enforcement
        if name not in TOOLS:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"unknown tool: {name}"}}
        if caller_role is not None:
            allowed = TOOL_GRANTS.get(caller_role, set())
            if name not in allowed:
                return {"jsonrpc": "2.0", "id": req_id, "error": {
                    "code": -32000,
                    "message": f"role '{caller_role}' is not granted tool '{name}' (see TOOL_GRANTS)",
                }}
        result = TOOLS[name]["fn"](args)
    elif method == "shutdown":
        result = {"ok": True}
    else:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"unknown method: {method}"}}

    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        resp = handle_request(req)
        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()


def _selftest():
    print("== storage_server self-test ==")
    r = tool_get_review_history({})
    print(f"get_review_history -> {r['count']} records from {r['source']}")
    bad = tool_put_review_record({"record": {"pr_id": "x"}})
    assert bad["ok"] is False
    print(f"put_review_record (invalid) correctly rejected: {bad['error']}")
    ok = tool_put_review_record({"record": {
        "pr_id": "smoketest-000", "date": datetime.date.today().isoformat(),
        "findings_summary": "self-test record, safe to ignore",
        "overall_risk_score": "low", "outcome": "approved",
    }})
    assert ok["ok"] is True
    print("put_review_record (valid) accepted")
    r2 = tool_get_review_history({"pr_id": "smoketest-000"})
    assert r2["count"] == 1
    print("get_review_history filter round-trip OK")
    prop = tool_put_calibration_proposal({"record": {
        "change": "self-test proposal", "reason": "smoke test", "evidence_source": "mcp/storage_server.py",
        "proposed_by": "selftest",
    }})
    assert prop["ok"] is True
    print("put_calibration_proposal accepted (writes proposals file, not calibration-log.jsonl)")
    denied = handle_request({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                              "params": {"name": "put_review_record",
                                         "arguments": {"_caller_role": "release-manager", "record": {}}}})
    assert "error" in denied
    print(f"role-based denial works: {denied['error']['message']}")
    print("All self-tests passed.")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        main()
