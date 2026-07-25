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
 
**How it's normally caught:** a test or type check asserting the module's
public exports (e.g. `expect(ansiStyles.modifierNames).toBeDefined()`), or
an export-diff/AST-based check comparing exported symbols before and after
the change.
 
**Expected agent behavior:** the reviewer subagent should flag that an
export present before the diff is missing after it, especially since three
of the four related exports were successfully carried over — the pattern
should stand out as an incomplete refactor rather than an intentional
removal.
 
**Severity:** Medium — silent breaking change to the module's public API,
no crash at the point of introduction.
 