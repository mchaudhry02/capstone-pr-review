# Baseline Run Notes (fill in while you do the manual review)

Instructions: For each PR below, open the diff, review it like a real code
reviewer would (read every changed line, decide if you'd approve it), and
time yourself using your phone's stopwatch — tap start before you open the
diff, tap stop the moment you finish writing your review notes for that PR.

Do NOT look at `ground-truth.md` while reviewing the seeded-bug PRs -
review them cold, the way a real reviewer would encounter them.
Check against `ground-truth.md` only AFTER you've written your review notes.

## Review Log

| PR      | Type                           | Duration | Did you catch the seeded bug? (Y/N/N-A) | Your review notes (1-2 lines)                                                                                                                                                                                                                                    |
|---------|--------------------------------|----------|-----------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| pr-688  | Seeded bug (Math.min/max swap) | 5        | Y                                       | I think the code is trying to do is finding the highest number in the set and set the color to the number.                                                                                                                                                       |
| pr-4179 | Seeded bug (Missing pipe)      | 5        | Y                                       | I think the code is trying to do is Removing the between jänner and januar merges them into one literal string that will never match either word correctly.                                                                                                      |
| pr-569  | Seeded bug (modifierNames)     | 5        | Y                                       | I think the code is trying to do is anything that tries to import { modifierNames } from this module afterward gets undefined instead of the real array (bold, dim, italic, etc.) — no crash, no error, just a silent break wherever that value gets used later. |
| pr-653  | Clean                          | 5        | N/A                                     | I think the code is trying to do add xterm-ghostty in the terminal detection.                                                                                                                                                                                    |
| pr-3728 | Clean                          | 5        | N/A                                     | I think the cide is trying to do is fixes a typo in contributing.md                                                                                                                                                                                              |

## After Reviewing: Self-Score Using quality-rubric.md

For each PR, score 0-2 on each dimension from `docs/quality-rubric.md`:

| PR      | Bug Detection | Risk Flagging         | False Positive Control | Grounding | Release Note* | Total /10 |
|---------|---------------|-----------------------|------------------------|-----------|---|-----------|
| pr-688  | 2             | 1                     | N/A                    | 2         | | 6         |
| pr-4179 | 2             | 1                     | N/A                    | 2         | | 6         |
| pr-569  | 2             | 1                     | N/A                    | 2         | | 6         |
| pr-653  | N/A           | N/A (no risk to flag) | 1                      | 1         | | 4         |
| pr-3728 | N/A           | N/A (no risk to flag) | 2                      | 1         | | 4         |

*Release note: did you also draft a one-line release note for each? If not,
skip this column for now and just note it as a known limitation of the
manual baseline (agents will do this, manual baseline may not have).

## Summary (fill in after all 5 are done)

- Bugs caught: 3 / 3
- Average review time per PR: 5 minutes
- Average quality score: 75%
- Estimated cost per review: (your average minutes) x (assumed loaded
  hourly rate, e.g. $75/hr) / 60: 6.25 per review