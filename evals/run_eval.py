#!/usr/bin/env python3
"""
evals/run_eval.py

Runs Layer 1 deterministic checks (see evaluation-harness.md) against a
reviewer agent's structured JSON output for a given PR.

Usage:
    python run_eval.py <pr_id> <agent_output.json> <diff_file> [--seeded-bug-file line:col]

Example (seeded-bug PR):
    python run_eval.py pr-4179 output/pr-4179-result.json data/seeded-bugs/pr-4179-SEEDED-BUG.diff \
        --expected-file src/locale/de/_lib/match/index.ts

Example (clean PR):
    python run_eval.py pr-653 output/pr-653-result.json data/pr-653.diff --clean
"""

import json
import sys
import argparse
from pathlib import Path

REQUIRED_TOP_LEVEL_KEYS = {"findings", "overall_risk_score", "overall_recommendation"}
REQUIRED_FINDING_KEYS = {"file", "line_or_hunk", "issue", "severity", "recommended_action"}
VALID_SEVERITIES = {"low", "medium", "high", "critical"}
VALID_RECOMMENDATIONS = {"approve", "request_changes", "escalate_to_human"}


def check_schema_validity(output: dict) -> tuple[bool, str]:
    missing = REQUIRED_TOP_LEVEL_KEYS - output.keys()
    if missing:
        return False, f"Missing top-level keys: {missing}"
    for finding in output.get("findings", []):
        missing_f = REQUIRED_FINDING_KEYS - finding.keys()
        if missing_f:
            return False, f"Finding missing keys: {missing_f}"
        if finding.get("severity") not in VALID_SEVERITIES:
            return False, f"Invalid severity: {finding.get('severity')}"
    if output.get("overall_recommendation") not in VALID_RECOMMENDATIONS:
        return False, f"Invalid overall_recommendation: {output.get('overall_recommendation')}"
    return True, "OK"


def check_grounding(output: dict, diff_text: str) -> tuple[bool, str]:
    changed_files = [
        line.split(" b/")[-1].strip()
        for line in diff_text.splitlines()
        if line.startswith("diff --git")
    ]
    for finding in output.get("findings", []):
        if finding["file"] not in changed_files:
            return False, f"Finding references file not in diff: {finding['file']}"
    return True, "OK"


def check_seeded_bug_caught(output: dict, expected_file: str) -> tuple[bool, str]:
    for finding in output.get("findings", []):
        if finding["file"] == expected_file and finding["severity"] in ("medium", "high", "critical"):
            return True, f"Caught: {finding['issue']}"
    return False, f"No finding referencing expected file: {expected_file}"


def check_clean_pr_no_false_positives(output: dict) -> tuple[bool, str]:
    bad_findings = [f for f in output.get("findings", []) if f["severity"] in ("high", "critical")]
    if bad_findings:
        return False, f"False positive(s) on clean PR: {bad_findings}"
    return True, "OK"


def check_recommendation_consistency(output: dict) -> tuple[bool, str]:
    severities = [f["severity"] for f in output.get("findings", [])]
    rec = output.get("overall_recommendation")
    if "critical" in severities and rec != "escalate_to_human":
        return False, "Critical finding present but not escalated"
    if "high" in severities and rec != "escalate_to_human":
        return False, "High-severity finding present but not escalated"
    if not severities and rec != "approve":
        return False, "No findings but not approved"
    return True, "OK"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pr_id")
    parser.add_argument("agent_output", type=Path)
    parser.add_argument("diff_file", type=Path)
    parser.add_argument("--expected-file", help="File path the seeded bug is expected to be found in")
    parser.add_argument("--clean", action="store_true", help="Treat this PR as a clean/no-bug PR")
    args = parser.parse_args()

    output = json.loads(args.agent_output.read_text())
    diff_text = args.diff_file.read_text()

    results = {}
    results["schema_validity"] = check_schema_validity(output)
    results["grounding"] = check_grounding(output, diff_text)
    results["recommendation_consistency"] = check_recommendation_consistency(output)

    if args.clean:
        results["clean_pr_no_false_positives"] = check_clean_pr_no_false_positives(output)
    elif args.expected_file:
        results["seeded_bug_caught"] = check_seeded_bug_caught(output, args.expected_file)

    all_passed = all(passed for passed, _ in results.values())

    print(f"\n=== Eval Report: {args.pr_id} ===")
    for check_name, (passed, detail) in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {check_name}: {detail}")
    print(f"\nOverall: {'PASS' if all_passed else 'FAIL'}\n")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
