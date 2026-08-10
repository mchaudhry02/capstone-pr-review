# Seeded Bug Ground Truth

Tracks intentional issues introduced into copies of real PR diffs, used to
validate that the review pipeline actually catches obvious problems.

## pr-688-SEEDED-BUG.diff

**Repo / PR:** chalk/chalk, PR #688 (FORCE_COLOR handling rework)

**Original code (correct):**
```js
const level = Math.min(Number.parseInt(env.FORCE_COLOR, 10), 3);
```

**Seeded change:**
```js
const level = Math.max(Number.parseInt(env.FORCE_COLOR, 10), 3);
```

**What broke:** `Math.min` was changed to `Math.max`. The original code clamps
`FORCE_COLOR` to a maximum of 3 (`Math.min(value, 3)`). Swapping to `Math.max`
means any `FORCE_COLOR` value of 3 or higher passes through unclamped, and
values below 3 get forced up to 3 instead of clamped down — inverting the
intended behavior.

**Why it's subtle:** `Math.min`/`Math.max` typo-swaps are a common, realistic
class of bug — the line still runs without throwing, so it won't fail loudly.

**How it's normally caught:** The repo's own test suite already has a test
for this exact behavior:
```js
test('a `FORCE_COLOR` above 3 is clamped to 3', async t => {
	t.is(await detectLevel({FORCE_COLOR: '4', TERM: 'xterm-256color'}), '3');
});
```
`FORCE_COLOR=4` would no longer return `'3'` — it would return `'4'`,
failing this test.

**Expected agent behavior:** The reviewer subagent should flag the
`Math.min` → `Math.max` change as suspicious given the surrounding comment
("clamped to 3") and/or the existing test, and either block merge or
escalate to a human reviewer.

**Severity:** Medium — not a security issue, but a functional regression
that silently changes documented behavior (`FORCE_COLOR` claims of "clamped
to 3" in the README become false).

## pr-569-SEEDED-BUG.diff

**Repo / PR:** chalk/chalk, PR #569 (moved ansi-styles exports earlier in file)

**Original code (correct):** the refactor moves four exports from the
bottom of the file to just after `styles`:
```js
export const modifierNames = Object.keys(styles.modifier);
export const foregroundColorNames = Object.keys(styles.color);
export const backgroundColorNames = Object.keys(styles.bgColor);
export const colorNames = [...foregroundColorNames, ...backgroundColorNames];
```

**Seeded change:** `modifierNames` is removed from the old location (as
expected for the move) but never re-added at the new location — only
`foregroundColorNames`, `backgroundColorNames`, and `colorNames` are
restored. The export is silently dropped from the file entirely.

**What broke:** any code importing `modifierNames` from this module now
gets `undefined` instead of the expected array of modifier names (`bold`,
`dim`, `italic`, etc.), with no error at import time.

**Why it's subtle:** the file still parses and runs fine. Nothing throws
until something downstream actually tries to use `modifierNames` and fails
in an unrelated-looking way.

**How to normally catch it:** a test or type check asserting the module's
public exports (e.g. `expect(ansiStyles.modifierNames).toBeDefined()`), or
an export-diff/AST-based check comparing exported symbols before and after
the change. **Confirmed by actually running the existing test suite
(`npx ava`) with this bug applied: all 32 existing tests passed — the
current test suite does NOT check for `modifierNames` being exported, so
this bug is NOT caught by deterministic testing alone.** This is a key
finding: it demonstrates a class of bug that only a code-reviewing agent
(or a human) can catch, not automated tests, and is a concrete argument
for why the review pipeline adds value beyond existing CI checks.

**Expected agent behavior:** the reviewer subagent should flag that an
export present before the diff is missing after it, especially since three
of the four related exports were successfully carried over — the pattern
should stand out as an incomplete refactor rather than an intentional
removal.

**Severity:** Medium — silent breaking change to the module's public API,
no crash at the point of introduction.

## pr-579-SEEDED-BUG.diff — RETIRED

**Status: Retired, not part of the active ground-truth set.** The
uploaded seeded version could not be clearly confirmed to match the
intended edit, and the resulting test failure was traced back to a
pre-existing gap in chalk's own test coverage unrelated to any change we
could clearly attribute (confirmed via `gh pr diff 579 --name-only`,
which showed the real PR never touched the failing test file). Kept here
for record-keeping only — do not cite this entry as evidence in the
impact report or eval harness.

**Repo / PR:** chalk/chalk, PR #579 (rewrite of browser Chromium/color
detection, adds Deno support and level-based truecolor detection)

**Original code (correct):**
```js
if (brand && brand.version > 93) {
	return 3;
}
```

**Seeded change:**
```js
if (brand && brand.version < 93) {
	return 3;
}
```

**What broke:** the comparison operator was flipped from `>` to `<`. The
original intent is "modern Chromium (version 93+, when the User-Agent
Client Hints API added brand version data usable this way) gets truecolor
(level 3)." The seeded version inverts this: only *older* Chromium
versions under 93 get truecolor, and modern browsers instead fall through
to the weaker `level: 1` basic-color detection.

**Why it's subtle:** it's a single-character change (`>` to `<`) in a
numeric comparison. The code still runs without error — it just silently
under-detects color support in the majority of real-world (modern)
browsers, while behaving "correctly" for a shrinking minority of outdated
ones. Nothing about the output looks obviously wrong at a glance.

**How it's normally caught:** a unit test asserting expected `level` output
for a known modern Chromium version (e.g. `version: 120` should yield
`level: 3`), or a code reviewer cross-checking the comparison direction
against the surrounding comment/intent ("modern Chromium supports
truecolor").

**Expected agent behavior:** the reviewer subagent should flag the
comparison direction as suspicious relative to the stated purpose of the
change (detecting *modern* browser truecolor support), and either request
a test covering this branch or escalate for human confirmation.

**Severity:** Medium — functional regression, no crash, degrades a feature
(color support) rather than breaking the build.

## pr-4179-SEEDED-BUG.diff

**Repo / PR:** date-fns/date-fns, PR #4179 (adds `jänner` as an alternate
German month name for "January" in the locale month-matching regex)

**Original code (correct):**
```js
wide: /^(jänner|januar|februar|märz|april|mai|juni|juli|august|september|oktober|november|dezember)/i,
```

**Seeded change:**
```js
wide: /^(jännerjanuar|februar|märz|april|mai|juni|juli|august|september|oktober|november|dezember)/i,
```

**What broke:** the `|` (alternation pipe) between `jänner` and `januar`
was removed, merging them into a single literal string `jännerjanuar`.
The regex will no longer match either word individually — neither
"jänner" nor "januar" as written by a user will be recognized as January
in German date parsing.

**Why it's subtle:** the regex still compiles and runs without error. It's
a single missing character in a long, dense alternation list, which is
easy to lose during manual editing and easy to skim past in review since
the line is long and visually similar to the correct version.

**How it's normally caught:** a locale-parsing test asserting that both
"jänner" and "januar" correctly parse as month 1 (January) in German date
strings. If no such test exists for the newly-added "jänner" alternate,
this would be a case where existing tests may not catch it either — worth
confirming when run.

**Expected agent behavior:** the reviewer subagent should flag the missing
alternation separator, especially since the PR's stated purpose is
specifically to *add* a new alternate word — a reviewer comparing intent
("add jänner as an option") against the actual regex change should notice
the new word isn't actually separated from the existing one.

**Severity:** Medium — silently breaks German-locale date parsing for the
specific input this PR was meant to add support for, no crash.

---

# Retrieval Ground Truth Set

Separate from the bug-detection ground truth above, this set tests the
**planner agent's retrieval step**: given a new PR diff, does the
retrieval store (MCP-backed) actually surface the relevant prior context
it should, rather than silently missing it? This directly feeds the
retrieval quality report required in Workstream 3.

## How this works

Each row below is a query the planner would realistically issue against
the retrieval store when processing a new PR, paired with which
already-indexed item(s) *should* come back as relevant. When the
retrieval pipeline is built, running each query and checking whether the
expected result actually appears in the top results is the retrieval
quality report.

## Retrieval Test Cases

| # | Query (simulating planner's retrieval need) | Expected relevant result(s) | Why it's relevant |
|---|---|---|---|
| 1 | "past PRs touching FORCE_COLOR clamping logic" | `pr-688` (real + seeded) | Same function (`_supportsColor`), same clamping behavior — a new PR touching this area should surface this prior history |
| 2 | "changes to ansi-styles exports" | `pr-569` (real + seeded) | Any future PR touching `source/vendor/ansi-styles/index.js` exports should surface this precedent, since it's a confirmed area where a bug slipped past tests before |
| 3 | "German locale month name matching patterns" | `pr-4179` (real + seeded) | Any future PR touching `src/locale/de/_lib/match/index.ts` should surface this as related prior work |
| 4 | "terminal type detection additions (xterm variants)" | `pr-653` | A new PR adding another terminal type (e.g. a hypothetical `xterm-foo`) should retrieve this as a precedent/pattern to follow |
| 5 | "known bug classes not caught by existing tests" | `pr-569` specifically (confirmed untested) | This tests whether the retrieval store can surface "here's a bug class our test suite has a known gap for" — a more abstract but important retrieval case |

## Negative Test Case (checks for false retrieval, not just misses)

| # | Query | Expected result | Why |
|---|---|---|---|
| 6 | "changes to CONTRIBUTING.md wording" | pr-3728 (typo fix) should surface — **and nothing else should be pulled in as falsely relevant** (e.g. `pr-688`'s FORCE_COLOR logic should NOT appear here) | Confirms retrieval doesn't over-broadly match everything to everything; a retrieval system that returns irrelevant results on every query is as unreliable as one that misses obvious ones |

## Status

Ground-truth queries defined. Actual retrieval quality report (running
these queries against the real MCP-backed retrieval store once built and
recording hit/miss/false-positive results) is still pending — this is the
next concrete action once MCP configuration is in place.