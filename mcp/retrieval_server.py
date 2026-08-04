#!/usr/bin/env python3
"""
pr-review-retrieval MCP server

Indexes every PR diff under data/ (real + seeded-bug variants) at the
per-file-hunk level and exposes a search_context tool, over the same
stdio JSON-RPC 2.0 shape as storage_server.py (see the PROTOCOL NOTE
in that file for why this isn't the official `mcp` SDK).

Design goals driven directly by agents/planner.md and
data/seeded bugs/ground-truth.md's "Retrieval Ground Truth Set":
  - Every result must be traceable back to a real source file
    (doc_id + source path), never a bare claim.
  - If nothing clears the relevance threshold, return results: []
    explicitly rather than forcing a low-quality match -- planner.md's
    "Silent retrieval miss" failure mode is exactly what this prevents.
  - Chunking is per changed-file-per-PR (not whole-diff), so citations
    point at the specific file, matching how a reviewer would actually
    want to follow up.

Run standalone for a smoke test against the 6 ground-truth retrieval
queries in data/seeded bugs/ground-truth.md:
    python3 mcp/retrieval_server.py --selftest
"""

import json
import sys
import os
import re
import glob

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
PR_LIST_PATH = os.path.join(DATA_DIR, "pr-list.json")

# Relevance floor. Below this cosine-similarity score, a candidate is
# treated as noise, not a result -- this is what makes "no relevant
# context" possible instead of always returning top-k regardless of quality.
RELEVANCE_THRESHOLD = 0.08

# ---------------------------------------------------------------------------
# Schema definitions
# ---------------------------------------------------------------------------

INDEXED_DOC_SCHEMA = {
    "type": "object",
    "properties": {
        "doc_id": {"type": "string", "description": "'{pr_id}#{file_path}', globally unique"},
        "pr_id": {"type": "string"},
        "file_path": {"type": "string"},
        "source": {"type": "string", "description": "repo-relative path to the source diff file -- traceability anchor"},
        "seeded_bug": {"type": "boolean"},
        "pr_title": {"type": "string", "description": "from data/pr-list.json when available"},
    },
    "classification": "public",
    # public = sourced entirely from merged, public PRs on chalk/chalk and
    # date-fns/date-fns; safe to log, cache, or include in eval reports.
}

SEARCH_RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "doc_id": {"type": "string"},
        "pr_id": {"type": "string"},
        "file_path": {"type": "string"},
        "snippet": {"type": "string", "description": "<=300 chars of the matched hunk, for grounding"},
        "relevance_score": {"type": "number"},
        "citation": {"type": "string", "description": "source file path, for traceability back to the actual diff"},
        "classification": {"type": "string", "enum": ["public"]},
    },
}

# ---------------------------------------------------------------------------
# Index build
# ---------------------------------------------------------------------------

_PR_ID_RE = re.compile(r"pr-(\d+)(-SEEDED-BUG)?\.diff$")


def _pr_metadata():
    if not os.path.exists(PR_LIST_PATH):
        return {}
    with open(PR_LIST_PATH, "r", encoding="utf-8") as f:
        items = json.load(f)
    return {str(item["number"]): item.get("title", "") for item in items}


def _split_by_file(diff_text):
    """Split a unified diff into (file_path, hunk_text) chunks on
    'diff --git a/x b/x' boundaries."""
    chunks = []
    parts = re.split(r"^diff --git a/(.+?) b/\1\n", diff_text, flags=re.MULTILINE)
    # re.split with a capturing group interleaves: [preamble, path1, body1, path2, body2, ...]
    if len(parts) <= 1:
        return [("(whole file)", diff_text)]
    for i in range(1, len(parts), 2):
        path = parts[i]
        body = parts[i + 1] if i + 1 < len(parts) else ""
        chunks.append((path, body))
    return chunks


def _load_index():
    pr_titles = _pr_metadata()
    docs = []  # list of dicts matching INDEXED_DOC_SCHEMA (+ "content" for indexing)
    diff_files = sorted(glob.glob(os.path.join(DATA_DIR, "*.diff"))) + \
        sorted(glob.glob(os.path.join(DATA_DIR, "seeded bugs", "*.diff")))
    seen = set()
    for path in diff_files:
        fname = os.path.basename(path)
        m = _PR_ID_RE.search(fname)
        if not m:
            continue
        pr_id, seeded = m.group(1), bool(m.group(2))
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        for file_path, body in _split_by_file(text):
            doc_id = f"pr-{pr_id}{'-SEEDED-BUG' if seeded else ''}#{file_path}"
            if doc_id in seen:
                continue
            seen.add(doc_id)
            docs.append({
                "doc_id": doc_id,
                "pr_id": pr_id,
                "file_path": file_path,
                "source": os.path.relpath(path, BASE_DIR),
                "seeded_bug": seeded,
                "pr_title": pr_titles.get(pr_id, ""),
                # PR title is weighted 3x: it's the clearest human-written
                # statement of intent, and a first retrieval pass (see
                # memory/store/calibration-log.jsonl, 2026-08-04 entry)
                # found title-blind indexing under-weighted intent relative
                # to incidental diff-body vocabulary.
                "content": f"{file_path} {(pr_titles.get(pr_id, '') + ' ') * 3}{body}",
            })
    if not docs:
        return docs, None, None
    vectorizer = TfidfVectorizer(stop_words="english", max_features=20000, sublinear_tf=True)
    matrix = vectorizer.fit_transform([d["content"] for d in docs])
    return docs, vectorizer, matrix


_DOCS, _VECTORIZER, _MATRIX = _load_index()

# ---------------------------------------------------------------------------
# Tool grants (see docs/orchestration-diagram.md's Routing-and-Tool-Grant Map)
#   planner  : query (primary retrieval consumer, per planner.md)
#   reviewer : query (reviewer.md also lists "Past PR history / retrieval
#              store: Read" directly, not only via planner hand-off)
#   release-manager: none -- works from handed-in context only
# ---------------------------------------------------------------------------

TOOL_GRANTS = {
    "orchestrator": {"search_context", "index_stats"},
    "planner": {"search_context", "index_stats"},
    "reviewer": {"search_context", "index_stats"},
    "release-manager": set(),
}


def tool_search_context(args):
    query = args.get("query", "")
    top_k = args.get("top_k", 5)
    if not query or _VECTORIZER is None:
        return {"query": query, "results": [], "total_indexed_docs": len(_DOCS)}

    q_vec = _VECTORIZER.transform([query])
    sims = cosine_similarity(q_vec, _MATRIX)[0]
    ranked = sorted(range(len(_DOCS)), key=lambda i: sims[i], reverse=True)

    results = []
    for i in ranked[:top_k]:
        score = float(sims[i])
        if score < RELEVANCE_THRESHOLD:
            break  # scores are sorted descending, so we can stop here
        doc = _DOCS[i]
        snippet = doc["content"][:300].replace("\n", " ")
        results.append({
            "doc_id": doc["doc_id"],
            "pr_id": doc["pr_id"],
            "file_path": doc["file_path"],
            "snippet": snippet,
            "relevance_score": round(score, 4),
            "citation": doc["source"],
            "classification": "public",
        })
    # Explicit empty list, never a fabricated fallback -- matches
    # planner.md's "must say so explicitly" behavior rule.
    return {"query": query, "results": results, "total_indexed_docs": len(_DOCS)}


def tool_index_stats(args):
    return {
        "total_indexed_docs": len(_DOCS),
        "unique_prs": len(set(d["pr_id"] for d in _DOCS)),
        "seeded_bug_docs": sum(1 for d in _DOCS if d["seeded_bug"]),
        "relevance_threshold": RELEVANCE_THRESHOLD,
    }


TOOLS = {
    "search_context": {
        "fn": tool_search_context,
        "description": "Query the PR-diff retrieval index. Returns [] explicitly when nothing clears the relevance threshold -- never fabricates context.",
        "input_schema": {"type": "object", "required": ["query"], "properties": {
            "query": {"type": "string"},
            "top_k": {"type": "integer", "default": 5},
        }},
        "output_classification": "public",
    },
    "index_stats": {
        "fn": tool_index_stats,
        "description": "Basic index health stats (doc count, PR count, threshold in use).",
        "input_schema": {"type": "object", "properties": {}},
        "output_classification": "public",
    },
}


def handle_request(req):
    method = req.get("method")
    req_id = req.get("id")
    params = req.get("params", {}) or {}

    if method == "initialize":
        result = {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": "pr-review-retrieval", "version": "1.0.0"},
            "capabilities": {"tools": {}},
        }
    elif method == "tools/list":
        result = {"tools": [
            {"name": name, "description": t["description"], "inputSchema": t["input_schema"]}
            for name, t in TOOLS.items()
        ]}
    elif method == "tools/call":
        name = params.get("name")
        args = params.get("arguments", {}) or {}
        caller_role = args.pop("_caller_role", None)
        if name not in TOOLS:
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"unknown tool: {name}"}}
        if caller_role is not None:
            allowed = TOOL_GRANTS.get(caller_role, set())
            if name not in allowed:
                return {"jsonrpc": "2.0", "id": req_id, "error": {
                    "code": -32000,
                    "message": f"role '{caller_role}' is not granted tool '{name}' (see TOOL_GRANTS)",
                }}
        result = TOOLS[name]["fn"](args)
    elif method == "shutdown":
        result = {"ok": True}
    else:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": f"unknown method: {method}"}}

    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        resp = handle_request(req)
        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()


# Ground-truth retrieval test cases, copied from
# data/seeded bugs/ground-truth.md "Retrieval Ground Truth Set" so this
# file stays self-checkable without a second source of truth to drift from.
_GROUND_TRUTH_QUERIES = [
    {"query": "past PRs touching FORCE_COLOR clamping logic", "expect_pr_id": "688"},
    {"query": "changes to ansi-styles exports", "expect_pr_id": "569"},
    {"query": "German locale month name matching patterns", "expect_pr_id": "4179"},
    {"query": "terminal type detection additions xterm variants", "expect_pr_id": "653"},
    {"query": "known bug classes not caught by existing tests modifierNames", "expect_pr_id": "569"},
    {"query": "changes to CONTRIBUTING.md wording", "expect_pr_id": "3728", "expect_not_pr_id": "688"},
]


def _selftest():
    print("== retrieval_server self-test ==")
    stats = tool_index_stats({})
    print(f"index_stats -> {stats}")
    assert stats["total_indexed_docs"] > 0, "index is empty -- check data/ path"

    hits, misses = 0, 0
    for case in _GROUND_TRUTH_QUERIES:
        r = tool_search_context({"query": case["query"], "top_k": 5})
        pr_ids = [res["pr_id"] for res in r["results"]]
        got_expected = case["expect_pr_id"] in pr_ids
        false_positive = case.get("expect_not_pr_id") and case["expect_not_pr_id"] in pr_ids
        status = "HIT" if got_expected and not false_positive else "MISS"
        hits += status == "HIT"
        misses += status == "MISS"
        print(f"[{status}] \"{case['query']}\" -> pr_ids={pr_ids} "
              f"(expected {case['expect_pr_id']}"
              f"{', NOT ' + case['expect_not_pr_id'] if case.get('expect_not_pr_id') else ''})")

    print(f"\n{hits}/{len(_GROUND_TRUTH_QUERIES)} ground-truth queries hit. "
          f"(This is a smoke test, not the full retrieval quality report --"
          f" see docs/mcp-configuration.md for what's still pending there.)")

    empty = tool_search_context({"query": "completely unrelated nonsense zzz quantum toaster"})
    print(f"\nOut-of-domain query -> results: {empty['results']} (should be [])")
    assert empty["results"] == []
    print("Empty-result behavior confirmed: no fabricated matches.")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        main()
