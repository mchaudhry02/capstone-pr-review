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
| Governance policy | Not started — GAP |
| Role-to-tool access matrix | Not started — GAP |
| CI/CD guardrails | Not started — GAP |
| Audit log template | Not started — GAP |
| Deterministic conversion + ADR | Not started — GAP |

## Known Remaining Gap in Module 3

Agent definitions (`agents/*.md`), skills, and MCP servers all exist and
are individually tested, but there is **no actual orchestrator code**
wiring them together into a runnable end-to-end pipeline yet — running
a real PR through planner -> reviewer -> release-manager automatically
is still to be built. This is why `evals/sample-runs/` outputs are
explicitly marked as hand-crafted rather than real agent output. Building
this end-to-end wiring is required before Workstream 6's production-like
integration run.

## Immediate Next Actions (in priority order)
1. Build the actual orchestrator (wires planner -> reviewer ->
   release-manager -> MCP tools together into a runnable pipeline)
2. Governance policy + role-to-tool access matrix, formalized from
   `docs/orchestration-diagram.md`'s existing map (Workstream 4)
3. CI/CD guardrails (Workstream 4)
4. Right-size each workflow step + deterministic conversion + ADR (Workstream 5)