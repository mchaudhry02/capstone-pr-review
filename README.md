# Agentic PR Review & Release Notes Pipeline

A forkable, governed, multi-agent pipeline that reviews pull requests,
catches issues human reviewers might miss, and drafts release notes —
built as a capstone project demonstrating safe, governed agentic
engineering.

## What this does

Given a PR diff, this pipeline:
1. Delegates to specialized subagents (planner, implementer, reviewer,
   release-manager) to analyze the change
2. Produces a structured review with a risk score
3. Flags high-risk changes (security issues, silently dropped exports,
   broken logic) for human escalation instead of auto-approving
4. Drafts a release-note line for the change

See `docs/prd.md` for the full problem statement, stakeholder, and
acceptance criteria.

## Status

This is an active capstone project. Workstreams 1-4 are substantively
complete: scoping and baseline (WS1), repo assembly with agents/skills/
memory (WS2), orchestration + MCP + retrieval + evals (WS3), and
governance policy + CI/CD guardrails (WS4) — including a policy test
suite that runs against the real MCP server code, not just documentation.
The one known gap: no orchestrator code yet wires the agents into a
runnable end-to-end pipeline (see `docs/gap-inventory.md`'s "Known
Remaining Gap"). See `docs/gap-inventory.md` for full status.

## Quick Start (fork-and-run in under 15 minutes)

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- [GitHub CLI](https://cli.github.com/) installed and authenticated (`gh auth login`)
- An Anthropic API key (or your chosen agent runtime's equivalent)

### 1. Clone this repo
```bash
git clone <this-repo-url>
cd capstone-pr-review
```

### 2. Set up your environment
```bash
cp docker/.env.example docker/.env
```
Open `docker/.env` and fill in your actual API key. **Never commit this file.**

### 3. Build and start the containerized harness
```bash
cd docker
docker compose build
docker compose up -d
```

### 4. Enter the container
```bash
docker exec -it pr-review-agent bash
```

### 5. Pull sample PR data (optional — sample data is already included)
```bash
./fetch-prs.sh chalk/chalk 25
```

### 6. Run the pipeline against a sample PR
```bash
# (Command will be added once the orchestrator is built in Workstream 3)
```

### 7. When done
```bash
exit
docker compose down
```

## Repository Structure

```
.
├── .github/
│   └── workflows/
│       └── policy-checks.yml   # CI: policy tests, eval checks, retrieval self-test on relevant PRs
├── .idea/                    # JetBrains IDE settings (gitignored)
├── agents/
│   ├── planner.md              # Routes PR to subagents, retrieves context, no review authority
│   ├── reviewer.md            # Read-only PR review agent, scores findings against quality-rubric.md
│   └── release-manager.md     # Draft-only release note agent, wired to reviewer's severity output
├── chalk/                    # Local clone of chalk/chalk, used to apply/test seeded bugs (gitignored)
├── data/
│   ├── pr-list.json          # Pulled PR metadata
│   ├── pr-*.diff              # Real PR diffs (clean samples)
│   └── seeded-bugs/
│       ├── ground-truth.md       # Documented seeded bugs and expected findings
│       └── pr-*-SEEDED-BUG.diff  # PR diffs with intentional bugs introduced
├── docker/
│   ├── Dockerfile           # Containerized agent harness
│   ├── docker-compose.yml   # Filesystem/network/credential boundaries
│   └── .env.example         # Template for required secrets (never commit .env)
├── docs/
│   ├── prd.md                       # Problem statement, stakeholder, acceptance criteria
│   ├── quality-rubric.md            # Scoring rubric with pass/fail thresholds
│   ├── baseline-metrics.md          # Pre-agent baseline results
│   ├── baseline-run-notes.md        # Raw baseline review data
│   ├── iteration-log.md             # Chronological decision log
│   ├── gap-inventory.md             # What's built vs. in progress
│   ├── orchestration-diagram.md     # Mermaid flowchart + routing-and-tool-grant map
│   ├── retrieval-quality-report.md  # Real results from the MCP retrieval server
│   ├── governance-policy.md         # Role-to-tool matrix, data classification, enforcement points
│   └── audit-log-template.md        # Schema + example for logging agent actions and policy denials
├── evals/
│   ├── holdout-set.md           # Calibration vs. holdout PR split
│   ├── evaluation-harness.md    # Deterministic checks + rubric scoring design
│   ├── run_eval.py              # Runnable deterministic-check script
│   ├── eval-results.jsonl       # Logged eval run results
│   └── sample-runs/             # Example agent outputs used to test the harness (not real agent output — see sample-runs/README.md)
├── mcp/
│   ├── storage_server.py       # Persistent memory MCP server (review history, calibration log)
│   └── retrieval_server.py     # TF-IDF retrieval MCP server over data/*.diff
├── memory/
│   ├── architecture-notes.md   # Memory vs. context vs. prompt design, storage format
│   ├── reflection-log.md       # Concrete updates made based on observed results
│   └── store/
│       ├── review-history.jsonl        # Past PR review outcomes
│       ├── calibration-log.jsonl       # Logged changes made because of evidence
│       └── calibration-proposals.jsonl # Agent-proposed changes awaiting human promotion
├── skills/
│   ├── diff-parsing.md         # Shared diff-parsing logic used by planner + reviewer
│   └── risk-scoring.md         # Deterministic severity/recommendation scoring, fixes baseline's Risk Flagging gap
├── tests/
│   └── test_policy.py          # Policy tests: checks TOOL_GRANTS matches governance-policy.md, verifies real denials work
├── workspace/                # Mounted working directory for the agent harness at runtime
├── .gitignore                 # Excludes secrets, IDE files, cloned repos (chalk/), node_modules, etc.
├── .mcp.json                  # MCP server registration (storage + retrieval)
├── fetch-prs.sh               # Pulls sample PR data from GitHub
└── README.md
```

**Note:** `.idea/`, `chalk/`, `docker/.env`, and other local-only files are
excluded via `.gitignore` — they exist on disk for local development but
are never committed. See `.gitignore` at the repo root for the full list.

## Delivery Path

This project uses the **job-seeker / no-deployment path**: it runs against
public, representative data (real merged PRs from chalk/chalk and
date-fns/date-fns) rather than live production traffic. In a real
deployment, this would instead trigger on live GitHub webhooks against a
team's actual repository, with scoped write access and secrets pulled
from a vault rather than a local `.env` file.

## Ground-Truth Evaluation Data

Three seeded bugs, each based on a real merged PR with one intentional
issue introduced, are documented in `data/seeded-bugs/ground-truth.md`:

- **pr-688**: A `Math.min`/`Math.max` swap breaking `FORCE_COLOR`
  clamping — confirmed caught by the existing test suite
- **pr-569**: A silently dropped `modifierNames` export — confirmed
  **not** caught by the existing test suite, demonstrating a bug class
  only a reviewing agent (or human) catches
- **pr-4179**: A missing regex alternation pipe breaking German
  month-name matching

## Baseline (Pre-Agent) Results

See `docs/baseline-metrics.md` for full results. Summary: manual review
caught 3/3 seeded bugs, averaging 5 minutes and a 75% quality score per
review, at an estimated $6.25 cost per review. The agentic pipeline's
results will be compared against this baseline once built.

## MCP Configuration & Retrieval Quality

Two local, stdio-based MCP servers back this pipeline (see `.mcp.json`):

- **`mcp/storage_server.py`** — persistent memory (review history,
  calibration log), with schema-validated writes and role-based tool
  grants enforced server-side. Calibration log changes require human
  promotion from a proposals file, not direct agent writes.
- **`mcp/retrieval_server.py`** — TF-IDF retrieval over indexed PR diffs,
  with an explicit relevance floor so it returns an empty result rather
  than fabricating a weak match.

See `docs/retrieval-quality-report.md` for full results: **4/6 ground-truth
retrieval queries hit**, with 1 confirmed miss (a conceptual query with no
lexical match — the relevance floor correctly returned nothing rather
than guessing) and 1 confirmed false positive (logged as a calibration
proposal in `memory/store/calibration-proposals.jsonl`).

## Governance & CI/CD

Least-privilege access is enforced, not just documented — see
`docs/governance-policy.md` for the full role-to-tool matrix, data
classification rules, and escalation/rollback procedures.

`tests/test_policy.py` programmatically checks that the actual
`TOOL_GRANTS` in both MCP servers match the documented policy, and
functionally verifies that an unauthorized tool call (e.g.
`release-manager` attempting to write to memory) is really denied, not
just theoretically disallowed. This runs in CI
(`.github/workflows/policy-checks.yml`) on any PR touching agents,
skills, MCP servers, or governance docs, blocking merges that introduce
policy drift or eval regressions.

## License

TBD