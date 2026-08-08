#!/usr/bin/env python3
"""
skills/risk_scoring.py

Deterministic implementation of skills/risk-scoring.md's scoring logic.
This REPLACES having an LLM agent apply these rules via reasoning on
every call -- the rules themselves have no ambiguity left to resolve,
so running them as code is faster, free, and always produces the same
output for the same input (see docs/adr/ADR-001-deterministic-risk-scoring.md
for the full before/after comparison and rationale).

The reviewer agent still generates `findings` (the judgment-heavy part:
reading a diff and deciding what's wrong and how severe it is). This
module only replaces the mechanical mapping from findings -> an overall
recommendation, which was always fully rule-based.
"""

from typing import Literal

Severity = Literal["low", "medium", "high", "critical"]
Recommendation = Literal["approve", "request_changes", "escalate_to_human"]

_SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def score(findings: list[dict]) -> dict:
    """
    findings: list of {"severity": "low"|"medium"|"high"|"critical", ...}
    Returns: {"overall_risk_score": ..., "overall_recommendation": ..., "reasoning": ...}

    Rules (unchanged from skills/risk-scoring.md):
      - Any critical finding  -> risk=critical, recommendation=escalate_to_human
      - Any high (no critical) -> risk=high, recommendation=escalate_to_human
      - Only medium/low        -> risk=highest present, recommendation=
            request_changes if any medium exists, else approve
      - No findings            -> risk=low, recommendation=approve
    """
    if not findings:
        return {
            "overall_risk_score": "low",
            "overall_recommendation": "approve",
            "reasoning": "No findings reported.",
        }

    severities = [f["severity"] for f in findings]
    highest = max(severities, key=lambda s: _SEVERITY_RANK[s])

    if highest == "critical":
        rec = "escalate_to_human"
    elif highest == "high":
        rec = "escalate_to_human"
    elif highest == "medium":
        rec = "request_changes"
    else:  # all low
        rec = "approve"

    return {
        "overall_risk_score": highest,
        "overall_recommendation": rec,
        "reasoning": f"Highest finding severity is '{highest}' "
                     f"({len(findings)} finding(s) total); "
                     f"mapped per skills/risk-scoring.md rules.",
    }


# ---------------------------------------------------------------------------
# Self-test -- covers every rule branch, run in CI (see
# .github/workflows/policy-checks.yml) so this can't silently drift from
# skills/risk-scoring.md without a test failing.
# ---------------------------------------------------------------------------

def _selftest():
    cases = [
        ([], "low", "approve"),
        ([{"severity": "low"}], "low", "approve"),
        ([{"severity": "low"}, {"severity": "low"}], "low", "approve"),
        ([{"severity": "medium"}], "medium", "request_changes"),
        ([{"severity": "low"}, {"severity": "medium"}], "medium", "request_changes"),
        ([{"severity": "high"}], "high", "escalate_to_human"),
        ([{"severity": "medium"}, {"severity": "high"}], "high", "escalate_to_human"),
        ([{"severity": "critical"}], "critical", "escalate_to_human"),
        ([{"severity": "low"}, {"severity": "critical"}], "critical", "escalate_to_human"),
    ]
    passed = 0
    for findings, expected_risk, expected_rec in cases:
        result = score(findings)
        ok = (result["overall_risk_score"] == expected_risk
              and result["overall_recommendation"] == expected_rec)
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] findings={findings} -> {result['overall_risk_score']}/{result['overall_recommendation']} "
              f"(expected {expected_risk}/{expected_rec})")
        passed += ok
    print(f"\n{passed}/{len(cases)} passed")
    return passed == len(cases)


if __name__ == "__main__":
    import sys
    sys.exit(0 if _selftest() else 1)
