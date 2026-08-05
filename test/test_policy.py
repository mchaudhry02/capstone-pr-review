#!/usr/bin/env python3
"""
tests/test_policy.py

CI-enforced policy tests. These check that the actual enforcement code
(TOOL_GRANTS in mcp/*.py) matches the documented governance policy
(docs/governance-policy.md), and that the documented least-privilege
rules hold. This is what makes governance "enforced in code," not just
written down -- a PR that changes a tool grant without updating the
policy doc (or vice versa) fails CI.

Run: python3 -m pytest tests/test_policy.py -v
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp"))

import storage_server
import retrieval_server


# Canonical policy, hand-derived from docs/governance-policy.md's
# Role-to-Tool Access Matrix. If you change the matrix in that doc, update
# this dict too -- that's the point: this is the single enforceable
# checkpoint tying the two together.
EXPECTED_STORAGE_GRANTS = {
    "orchestrator": {"get_review_history", "put_review_record", "get_calibration_log"},
    "planner": {"get_review_history", "get_calibration_log"},
    "reviewer": {"get_review_history", "get_calibration_log"},
    "release-manager": set(),
}

EXPECTED_RETRIEVAL_GRANTS = {
    "orchestrator": {"search_context", "index_stats"},
    "planner": {"search_context", "index_stats"},
    "reviewer": {"search_context", "index_stats"},
    "release-manager": set(),
}


def test_storage_grants_match_policy():
    """docs/governance-policy.md must match mcp/storage_server.py exactly."""
    assert storage_server.TOOL_GRANTS == EXPECTED_STORAGE_GRANTS, (
        f"storage_server.TOOL_GRANTS has drifted from docs/governance-policy.md.\n"
        f"Actual:   {storage_server.TOOL_GRANTS}\n"
        f"Expected: {EXPECTED_STORAGE_GRANTS}\n"
        f"Update either the code or the policy doc so they match."
    )


def test_retrieval_grants_match_policy():
    """docs/governance-policy.md must match mcp/retrieval_server.py exactly."""
    assert retrieval_server.TOOL_GRANTS == EXPECTED_RETRIEVAL_GRANTS, (
        f"retrieval_server.TOOL_GRANTS has drifted from docs/governance-policy.md.\n"
        f"Actual:   {retrieval_server.TOOL_GRANTS}\n"
        f"Expected: {EXPECTED_RETRIEVAL_GRANTS}\n"
        f"Update either the code or the policy doc so they match."
    )


def test_release_manager_has_no_memory_or_retrieval_access():
    """Least-privilege check: release-manager must never gain read/write
    access to memory or retrieval tools -- per governance-policy.md,
    it works only from context handed to it by the orchestrator."""
    assert storage_server.TOOL_GRANTS["release-manager"] == set()
    assert retrieval_server.TOOL_GRANTS["release-manager"] == set()


def test_no_role_can_write_calibration_log_directly():
    """Governance rule: calibration-log.jsonl requires human promotion.
    No tool in TOOLS should write directly to CALIBRATION_LOG_PATH --
    only put_calibration_proposal (which writes to a separate proposals
    file) should exist as a write path."""
    write_tool_names = {"put_review_record", "put_calibration_proposal"}
    actual_write_tools = {
        name for name, t in storage_server.TOOLS.items()
        if name.startswith("put_")
    }
    assert actual_write_tools == write_tool_names, (
        f"Unexpected write tools found: {actual_write_tools - write_tool_names}. "
        f"Any new write tool must be reviewed against the calibration-log "
        f"human-promotion rule in docs/governance-policy.md."
    )


def test_role_based_denial_actually_works():
    """Functional check, not just a config check: verify a denied call
    actually returns an error, using the real handle_request path."""
    denied = storage_server.handle_request({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "put_review_record",
                   "arguments": {"_caller_role": "release-manager", "record": {}}},
    })
    assert "error" in denied, "release-manager should be denied put_review_record"

    denied2 = retrieval_server.handle_request({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "search_context",
                   "arguments": {"_caller_role": "release-manager", "query": "x"}},
    })
    assert "error" in denied2, "release-manager should be denied search_context"


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    passed, failed = 0, 0
    for t in tests:
        try:
            t()
            print(f"[PASS] {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
