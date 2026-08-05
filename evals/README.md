# Sample Runs — IMPORTANT CONTEXT

The JSON files in this folder (`pr-4179-agent-output.json`,
`pr-653-agent-output.json`) are **hand-crafted example outputs**, written
to match the exact schema the reviewer agent is designed to produce
(`agents/reviewer.md`), used to prove the evaluation harness itself
(`evals/run_eval.py`) works correctly before the actual multi-agent
pipeline is built and wired end-to-end.

**They are NOT real agent-generated output.** Do not present these in the
final submission as evidence the reviewer agent works — they are evidence
the *eval harness* works. Once the orchestrator and reviewer agent are
actually running (later in Workstream 3), replace these with real
captured agent output and re-run `run_eval.py` against them, then update
`eval-results.jsonl` accordingly.

This distinction matters for the rubric's "evidence beats assertion"
standard — claiming these hand-crafted files as proof the agent works
would be a misleading assertion, not real run evidence.
