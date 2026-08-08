# Tool-Evolution Drill: Revoked Permission

## What was attempted

Simulated a realistic accidental regression: a developer removes
`reviewer`'s `get_calibration_log` grant from `mcp/storage_server.py`'s
`TOOL_GRANTS` dict (e.g., during an unrelated refactor) without updating
`docs/governance-policy.md` to match.

## What broke

**1. The CI-enforced policy test caught the drift immediately:**
```
[FAIL] test_storage_grants_match_policy: storage_server.TOOL_GRANTS has drifted from docs/governance-policy.md.
Actual:   {..., 'reviewer': {'get_review_history'}, ...}
Expected: {..., 'reviewer': {'get_calibration_log', 'get_review_history'}, ...}
Update either the code or the policy doc so they match.

4 passed, 1 failed
```
This is a real pytest-style run against the actual modified code — not a
hypothetical. In CI (`.github/workflows/policy-checks.yml`), this failure
would block the PR from merging.

**2. Real downstream breakage confirmed:** calling
`orchestrator.call_mcp_tool('storage_server.py', 'get_calibration_log', ..., 'reviewer')`
after the change correctly raised:
```
PermissionError: MCP denial: role 'reviewer' is not granted tool
'get_calibration_log' (see TOOL_GRANTS)
```
This confirms the regression isn't just a policy-doc mismatch — it would
have genuinely broken the reviewer agent's ability to read calibration
history mid-run, silently degrading review consistency (the exact
baseline weakness `skills/risk-scoring.md` was built to fix).

## What the eval/policy harness caught

- `tests/test_policy.py`'s `test_storage_grants_match_policy` — direct,
  specific failure message naming exactly which role and tool grant
  diverged, not just a generic "something's wrong"
- The other 4 policy tests continued passing, correctly scoping the
  failure to only the affected check rather than cascading

## Fix

Reverted `TOOL_GRANTS["reviewer"]` to include `get_calibration_log` again.

## Final result

```
[PASS] test_storage_grants_match_policy
[PASS] test_retrieval_grants_match_policy
[PASS] test_release_manager_has_no_memory_or_retrieval_access
[PASS] test_no_role_can_write_calibration_log_directly
[PASS] test_role_based_denial_actually_works

5 passed, 0 failed
```
And confirmed functionally: `reviewer` can once again call
`get_calibration_log` successfully.

## Takeaway

This is exactly the "governance stopping a regression" evidence the
capstone's final walkthrough video needs to show — not a deliberate
malicious overreach attempt, but the more realistic scenario of an
accidental permission drift during normal development, caught
automatically before it could reach production.
