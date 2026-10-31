# cs467-electron-triage

CS467 Assignment 3. An AI agent gives new `electron/electron` issues a first pass: a label, a
request for a repro, a link to an earlier report or a better channel. It can add allowed labels
and post one fixed-template comment. It cannot close, edit or unlabel anything. It runs only in
this sandbox on replayed issues and has never been used on Electron.

**Result.** On Codex, 21 of 25 real issues passed all three runs, error cost was .213 against .44
for simple rules, and all 15 attack runs passed. That meets the frozen thresholds for a supervised
trial. Claude, the configured live engine, has not run the final skill.

Start with [DESIGN.md](DESIGN.md).

## Where things are

| What | Where |
|---|---|
| Workflow and lock | [`issue-triage.md`](.github/workflows/issue-triage.md), [`.lock.yml`](.github/workflows/issue-triage.lock.yml); [Codex fallback](.github/workflows/issue-triage-codex.md) |
| Skill and scripts | [`.claude/skills/issue-triage/`](.claude/skills/issue-triage/SKILL.md) |
| Rules | [`AGENTS.md`](AGENTS.md), [`CONTRIBUTING.md`](CONTRIBUTING.md), [`CODEOWNERS`](.github/CODEOWNERS) |
| Need for automation | [`evals/need/`](evals/need/) |
| Cases, expected outcomes, outputs, logs | [`evals/golden/`](evals/golden/README.md); frozen in commit `4baa2cb` |
| Final result | [`results/codex-v2.md`](evals/golden/results/codex-v2.md) |
| Every failure | [`docs/FAILURES.md`](docs/FAILURES.md) |
| How the code works | [`docs/CODEBASE.md`](docs/CODEBASE.md) |
| Control tests | [`evals/golden/results/`](evals/golden/results/): `control-*.txt`, `network-egress.txt`, `control-forced/` |
| Drift check | [`drift-check.yml`](.github/workflows/drift-check.yml), [`docs/DRIFT_REVIEW.md`](docs/DRIFT_REVIEW.md) |

## Check it

Python 3.10 or later, standard library only, no login or key:

```bash
python3 -m unittest discover -s tests -v
python3 evals/tools/score.py --runs codex-v2
python3 evals/tools/skill_check.py --runs codex-v2
```

To inspect one case, read `input.json`, `expected.json` and `actual/codex-v2/run-1.json` in
`evals/golden/cases/e52255/`. Run anything else in a copy:
[evaluation guide](evals/golden/README.md#reproduce-the-analysis-offline).

Side experiments are on [`archive/full-evidence`](https://github.com/ceewaigit/cs467-electron-triage/tree/archive/full-evidence)
and [`archive/experiments`](https://github.com/ceewaigit/cs467-electron-triage/tree/archive/experiments/evals).
