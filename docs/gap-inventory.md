# Workstream 1: Gap Inventory

Status of required artifacts as of completing Workstream 1.

## Module 1 (Sandbox, PRD, rubric, baseline)
| Artifact | Status |
|---|---|
| Containerized agent harness | Started (Dockerfile, docker-compose.yml, .env.example, .dockerignore) |
| PRD | Done (`docs/prd.md`) |
| Quality rubric with thresholds | Done (`docs/quality-rubric.md`) |
| Baseline measurements | Plan written (`docs/baseline-metrics.md`); **actual baseline run not yet performed — GAP** |
| Iteration log | Started (`docs/iteration-log.md`) |

## Module 2 (Agents, skills, memory, reflection)
| Artifact | Status |
|---|---|
| Versioned agent definitions | Not started — GAP |
| Versioned skills (2+) | Not started — GAP |
| Persistent memory layout | Not started — GAP |
| Reflection log | Not started — GAP |

## Module 3 (Orchestration, MCP, retrieval, evals)
| Artifact | Status |
|---|---|
| Orchestration diagram | Not started — GAP |
| Routing-and-tool-grant map | Not started — GAP |
| MCP configuration | Not started — GAP |
| Ground-truth retrieval set | Partially done — 3 seeded-bug PRs with documented expected findings (`data/seeded-bugs/ground-truth.md`); need 1-2 more, plus this needs to be reframed/extended for retrieval-specific testing (not just bug detection) |
| Retrieval quality report | Not started — GAP |
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
1. Run the manual baseline pass using `docs/baseline-metrics.md` plan —
   closes the last Workstream 1 gap
2. Finish README with a 15-minute fork-and-run path (Workstream 2)
3. Define and version the first agent + 2 skills (Workstream 2)
4. Move into Workstream 3: orchestrator + subagents