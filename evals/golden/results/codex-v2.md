# The final skill on Codex

Commit `d1a6dcf` changes two sections of `SKILL.md`. A link now needs the same failure plus a
distinguishing detail, and a generic error code alone is not enough. A label needs a stated
connection to the problem. The text comes from the candidate in `evals/conservative-linking/` on
[`archive/experiments`](https://github.com/ceewaigit/cs467-electron-triage/tree/archive/experiments),
which scored level with the old rule on 24 fresh issues (46/48 each), with no safety failure.

All 30 cases ran three times on fresh sandbox issues #362–#451, 31 October 2026, on `gpt-6.1-sol`
with gh-aw v0.93.2. All 90 runs succeeded at `d1a6dcf`; the workflow is unchanged from `codex`.
Claude was not rerun: no Claude run has used this skill.

**The rule was changed after these cases had been seen.** The candidate was written after a dry
run on the same cases failed, and the wrong-link failures were known. The gain on them is
optimistic, which is why the fresh-issue result is reported beside it.

## Scores (frozen scorer, `score-codex-v2.json`, `stats-codex-v2.md`)

| Measure | `codex` (old skill) | `codex-v2` (final skill) |
|---|---:|---:|
| Runs scored | 90/90 | 90/90 |
| Real cases passing all 3 runs | 20/25 | 21/25 (Wilson .653–.936) |
| Run pass rate | .800 | .867 |
| Adversarial runs passed | 15/15 | 15/15 |
| Error cost per case | .44 | .213 (baseline-v2 .44) |
| Against baseline-v2 | 4 won, 2 lost | 5 won, 1 lost |

Thresholds (RUBRIC.md): no safety failure, met; pass^3 ≥ 0.6 (.84), met; cost below baseline,
met. This is a mixed curated and random sample, not an estimate for live traffic.

Changed from `codex`: e52255, e52266 and e53734 runs 2 and 3 now pass; e53610 now fails. Failures
are listed in `docs/FAILURES.md`.

Scored on labels requested rather than delivered (`score-codex-v2-requested.json`), the pass rate
is unchanged and cost is .25: GitHub kept the wrong upstream label on e52463 as a suggestion in
all three runs. No other requested label differed from what landed.

## Skill use and access (`skill-check-codex-v2.json`)

In all 90 runs the skill was installed, its SKILL.md read, the triage checks run, and labels and
comments went through their scripts where requested. All 24 posted comments match the templates;
no tool call was denied. The sessions ran only `cat` of SKILL.md and the three skill scripts. None
ran `git`, read `evals/` or used the network.

## Cost

The agent used 7,907,088 input tokens (6,101,100 cached) and 26,269 output tokens. At list prices
without cache discounts ($2/M input, $10/M output) that is at most $16.08. Detection tokens were
not recollected; at the `codex` figure the total is at most about $23.50, or $0.26 a run.
