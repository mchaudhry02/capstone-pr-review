#!/usr/bin/env bash
# fetch-prs.sh
# Pulls merged PR metadata + diffs from a GitHub repo for the capstone dataset.
#
# Usage:
#   ./fetch-prs.sh                     # uses defaults below
#   ./fetch-prs.sh owner/repo 25       # custom repo + count
#
# Requires: GitHub CLI (gh) installed and logged in (gh auth login)

set -euo pipefail

REPO="${1:-chalk/chalk}"
COUNT="${2:-25}"
OUTDIR="data"

echo "Repo:  $REPO"
echo "Count: $COUNT merged PRs"
echo "Output folder: $OUTDIR/"
echo ""

mkdir -p "$OUTDIR"

# 1. Save PR metadata (number, title, url, merge date) as JSON
echo "Fetching PR list..."
gh pr list --repo "$REPO" --state merged --limit "$COUNT" \
  --json number,title,url,mergedAt \
  > "$OUTDIR/pr-list.json"

echo "Saved PR list to $OUTDIR/pr-list.json"
echo ""

# 2. Pull the number for a real diff of each PR
echo "Fetching individual PR diffs..."
# Extract just the PR numbers from the JSON we just saved
PR_NUMBERS=$(grep -o '"number": *[0-9]*' "$OUTDIR/pr-list.json" | grep -o '[0-9]*')

for pr in $PR_NUMBERS; do
  echo "  - PR #$pr"
  gh pr diff "$pr" --repo "$REPO" > "$OUTDIR/pr-$pr.diff" || echo "    (failed to fetch PR #$pr, skipping)"
done

echo ""
echo "Done. Pulled $(echo "$PR_NUMBERS" | wc -w) PR diffs into $OUTDIR/"
echo "Next: pick 3-5 of these and create seeded-bug copies for your eval ground truth."
