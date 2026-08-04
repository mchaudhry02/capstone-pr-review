# Reflection Log

Concrete updates made to agents, skills, or memory rules as a result of
observed results — not just a diary, each entry should tie to an actual
change made.

## 2026-08-02: Risk Flagging weakness -> new risk-scoring skill

**Observation:** Baseline manual review (`docs/baseline-metrics.md`)
scored 1/2 on Risk Flagging across all 3 seeded-bug PRs. Findings
correctly identified *what* was wrong but not consistently *how severe*
or *what action to take*.

**Change made:** Created `skills/risk-scoring.md` as a standalone,
rule-based skill with explicit severity -> recommendation mapping, rather
than leaving that judgment to free-form agent reasoning. Wired the
reviewer agent to call this skill for every finding.

**Expected effect:** Reviewer agent's `overall_recommendation` should be
consistent and explainable across runs, closing the specific gap the
baseline exposed.

## 2026-08-02: pr-569 not caught by tests -> memory should track this pattern

**Observation:** `pr-569`'s seeded bug (dropped `modifierNames` export)
was NOT caught by the existing chalk test suite (confirmed via `npx ava`
— all 32 tests passed). This is a class of bug (silent API/export
removal) that only a reviewing agent catches.

**Change made:** Added a note to `memory/architecture-notes.md`'s
style/convention memory type description, and flagged in
`agents/reviewer.md`'s "Known Failure Modes" section, that export/API
surface changes during refactors deserve extra scrutiny regardless of
whether tests pass, since this repo's test suite has a confirmed gap here.

**Expected effect:** Future reviews of refactor-shaped PRs in this repo
should specifically check "did every previously-exported symbol survive
the move," rather than trusting a passing test suite as sufficient
evidence of correctness.

## 2026-08-04: Retrieval smoke test exposed a vocabulary-mismatch gap -> title-weighting fix

**Observation:** Once `mcp/retrieval_server.py` was built and run against
the 6 ground-truth retrieval queries in `data/seeded bugs/ground-truth.md`,
it scored 4/6 on first pass. Two misses: the "ansi-styles exports /
modifierNames" query ranked pr-569 below the relevance threshold because
generic diff-body vocabulary diluted the one specific matching term; the
"German locale month name" query missed pr-4179 entirely because the
query's words ("German", "month") never literally appear in the diff or
PR title (which says "de-AT" and "Jänner" instead).

**Change made:** Weighted PR title 3x relative to diff body in the TF-IDF
index and enabled sublinear TF scaling (see calibration-log.jsonl,
2026-08-04 entry). This is a principled fix, not query-specific tuning —
title is the clearest intent signal for any query, not just these two.

**Result:** Recovered the modifierNames miss (5/6 after the fix). The
pr-4179 miss remains — it's a genuine vocabulary-mismatch limitation of
lexical (TF-IDF) search, not something title-weighting can fix, since the
missing words never appear anywhere in the indexed text at all.

**Expected effect / open item:** In the real-deployment path this would
likely need either (a) a small domain-alias table (e.g. "de-AT" <->
"German", locale codes <-> language names) as a deterministic pre-processing
step, or (b) semantic embeddings instead of pure lexical TF-IDF — both are
right-tool candidates worth evaluating in Workstream 5. Documented as a
known limitation in `docs/mcp-configuration.md` rather than silently
left unaddressed.

## [Planned] Next reflection point
Once the reviewer agent is actually running (Workstream 3), compare its
real findings against `data/seeded-bugs/ground-truth.md` and log whether
it independently catches what the risk-scoring skill and failure-mode
notes were designed to help it catch. This entry will be filled in with
real results once that run happens.