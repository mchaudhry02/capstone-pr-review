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
| Orchestration diagram | **Done** — `docs/orchestration-diagram.md` |
| Routing-and-tool-grant map | **Done** — `docs/orchestration-diagram.md`, enforced in `mcp/mcp_servers.json` + both MCP servers' `TOOL_GRANTS` |
| MCP configuration | **Done** — `mcp/storage_server.py`, `mcp/retrieval_server.py`, `mcp/mcp_servers.json`, documented in `docs/mcp-configuration.md` |
| Ground-truth retrieval set | Done — 6 queries in `data/seeded bugs/ground-truth.md`'s "Retrieval Ground Truth Set", including 1 negative/false-positive case |
| Retrieval quality report | Partially done — smoke test in `docs/mcp-configuration.md` (5/6 hit, 1 documented open limitation); still needs a wider query set for a formal report — GAP |
| Evaluation harness | Not started — GAP |

## Module 4 (Governance, CI/CD, ADRs, conversion)
| Artifact | Status |
|---|---|
| Governance policy | Not started — GAP |
| Role-to-tool access matrix | Not started — GAP |
| CI/CD guardrails | Not started — GAP |
| Audit log template | Not started — GAP |
| Deterministic conversion + ADR | Not started — GAP |

## Immediate Next Actions (in priority order)
1. Finish README with a 15-minute fork-and-run path (Workstream 2)
2. Define and version the first agent + 2 skills (Workstream 2)
3. Move into Workstream 3: orchestrator + subagents