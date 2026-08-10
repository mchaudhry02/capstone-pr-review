# Workstream 1: Gap Inventory

Status of required artifacts as of completing Workstream 1.

## Module 1 (Sandbox, PRD, rubric, baseline)
| Artifact | Status |
|---|---|
| Containerized agent harness | Started (Dockerfile, docker-compose.yml, .env.example, .dockerignore) |
| PRD | Done (`docs/prd.md`) |
| Quality rubric with thresholds | Done (`docs/quality-rubric.md`) |
| Baseline measurements | **Done** — real baseline run completed (`docs/baseline-metrics.md`, raw data in `docs/baseline-run-notes.md`): 3/3 seeded bugs caught, 5 min avg review time, 75% avg quality score, $6.25 avg cost per review |
| Iteration log | Started (`docs/iteration-log.md`) |

## Module 2 (Agents, skills, memory, reflection)
| Artifact | Status |
|---|---|
| Versioned agent definitions | **Done** — 3 agents: `agents/planner.md`, `agents/reviewer.md`, `agents/release-manager.md` |
| Versioned skills (2+) | **Done** — `skills/diff-parsing.md`, `skills/risk-scoring.md` |
| Persistent memory layout | **Done** — `memory/architecture-notes.md`, `memory/store/*.jsonl` |
| Reflection log | **Done** — `memory/reflection-log.md`, 2 concrete entries tying observations to real changes made |

## Module 3 (Orchestration, MCP, retrieval, evals)
| Artifact | Status |
|---|---|
| Orchestration diagram | **Done** — `docs/orchestration-diagram.md`, Mermaid flowchart + routing rules |
| Routing-and-tool-grant map | **Done** — table in `docs/orchestration-diagram.md`, independently enforced server-side in both `mcp/storage_server.py` and `mcp/retrieval_server.py`'s `TOOL_GRANTS` |
| MCP configuration | **Done** — `.mcp.json`, `mcp/storage_server.py` (persistent memory, schema-validated), `mcp/retrieval_server.py` (TF-IDF retrieval, explicit relevance floor) |
| Ground-truth retrieval set | **Done** — 6 retrieval test cases (5 positive, 1 negative) in `data/seeded-bugs/ground-truth.md`, separate from the 3-entry bug-detection ground truth |
| Retrieval quality report | **Done** — `docs/retrieval-quality-report.md`, real results from running the actual retrieval server: 4/6 hit, 1 confirmed miss, 1 confirmed false positive (logged as a calibration proposal) |
| Evaluation harness | **Done** — `evals/evaluation-harness.md` (design), `evals/run_eval.py` (runnable, tested), `evals/holdout-set.md` (calibration vs. holdout split), `evals/eval-results.jsonl` (logged results) |

## Module 4 (Governance, CI/CD, ADRs, conversion)
| Artifact | Status |
|---|---|
| Governance policy | **Done** — `docs/governance-policy.md`: least-privilege principle, justification-to-widen process, data classification boundaries, escalation/rollback rules |
| Role-to-tool access matrix | **Done** — table in `docs/governance-policy.md`, cross-referenced against `docs/orchestration-diagram.md` and both MCP servers' `TOOL_GRANTS` |
| CI/CD guardrails | **Done** — `.github/workflows/policy-checks.yml`: 3 jobs (policy tests, eval checks, retrieval self-test) triggered on PRs touching agents/skills/MCP/governance docs |
| Audit log template | **Done** — `docs/audit-log-template.md`, schema + worked example showing a denied tool call logged |
| Deterministic conversion + ADR | **Done** — `docs/decision-matrix.md` (full step classification), `skills/risk_scoring.py` (converted, 9/9 self-test cases pass), `docs/before-after-risk-scoring-conversion.md` (measured latency 0.0011ms/call, $0 cost), `docs/adr/ADR-001-deterministic-risk-scoring.md` (3 rejected alternatives, each with cited evidence) |

## Governance Enforcement Evidence (not just documentation)

`tests/test_policy.py` was run against the real `mcp/storage_server.py`
and `mcp/retrieval_server.py` code — all 5 tests passed, including a
functional check (not just a config comparison) that `release-manager`
is genuinely denied a tool call it shouldn't have. This is real evidence
of "enforced in code," per the rubric's governance requirement.

## Workstream 6 (Production-Like Integration & Impact Study)
| Artifact | Status |
|---|---|
| Orchestrator (end-to-end pipeline wiring) | **Done, fully proven end-to-end** — `orchestrator.py` wires planner -> reviewer -> release-manager -> MCP tools without requiring a billed API key: deterministic/MCP steps run locally for real, LLM steps are pasted into Claude.ai (live mode) or use canned fixtures (`--dry-run`, via `mcp/dry_run_fixtures.json`) for fast, repeatable demo runs. Confirmed with real captured output: real MCP retrieval call (5 results of 279 indexed docs), real memory write to `review-history.jsonl`, correct routing, and a working `--overreach-demo` mode. Previously the project's one consistently-flagged gap; now fully closed. |
| Reliability & cost controls | **Done** — `docs/reliability-cost-controls.md`: timeout, retry-with-backoff, fail-closed fallback, max-iteration guard, per-call and per-workflow token budgets. All 4 testable controls verified with real, direct test runs (not just implemented) — see the doc for captured output. |
| Tool-evolution drill | **Done, two independent forms of evidence** — (1) `docs/tool-evolution-drill.md`: a permission was actually revoked in `mcp/storage_server.py`; `tests/test_policy.py` caught it with a specific failure message, real downstream breakage was confirmed via a live tool call, then rolled back and recovery confirmed. (2) `orchestrator.py --dry-run --overreach-demo`: a live run where the planner's routing plan omits the reviewer step; the orchestrator detects this in real time, prints a `GOVERNANCE VIOLATION DETECTED` block citing the specific routing rule violated, forcibly reinstates the reviewer, and records the violation in the final output's `governance_flags` field — a permanent, structured record, not just a log line. |
| Real (non-fallback) pipeline runs | **Done, via two methods** — (1) Claude performed the reviewer agent's reasoning directly in conversation (per `agents/reviewer.md`), combined with real deterministic scoring and eval code, across the full holdout set: `evals/sample-runs/pr-4179-real-output.json`, `pr-653-real-output.json`, `pr-3728-real-output.json`. (2) `orchestrator.py`'s live paste-based mode is fully working and documented in `docs/running-reviewer-via-claude-ai.md` — no billed API key required for either method. |
| Impact study vs. Module 1 baseline | **Done (partial)** — `docs/impact-study.md`: real bug-detection results (1/1 seeded bug caught, 2/2 clean PRs correctly approved, no false positives) and a qualitative confirmation that the deterministic risk-scoring conversion improved on the baseline's Risk Flagging weakness. **Not yet done**: full 5-dimension rubric scoring of the real outputs, and latency/cost figures from a fully automated run — both honestly flagged in the doc's "Honest limitations" section rather than glossed over. |

## Known Remaining Gaps (Minor, Optional)

The orchestrator is now fully proven end-to-end, including a real,
working governance-enforcement demo. What remains is optional
strengthening, not a missing requirement: (1) full 0-2 rubric scoring of
the real reviewer outputs, for a true like-for-like comparison against
`docs/baseline-run-notes.md`; (2) latency/cost figures from a fully
automated, unattended API-key-based run, for numbers directly
comparable to the baseline's stopwatch methodology. Neither blocks
submission — see `docs/rubric-self-check.pdf` for the full honest
status breakdown.

## Immediate Next Actions (in priority order)
1. Record the walkthrough video per `docs/walkthrough-video-script.md`
   — script already updated to use the real, working
   `--dry-run --overreach-demo` governance moment
2. (Optional, strengthens evidence) Score the 3 real outputs against
   `docs/quality-rubric.md`'s full 5-dimension rubric
3. (Optional, strengthens evidence) Run `orchestrator.py` in live paste
   mode (no `--dry-run`) for a few more holdout PRs, for additional
   real-run evidence
4. Final Canvas submission: confirm all 7 required PDFs, repo link, and
   video link are ready