# cs467-electron-triage

CS467 Assignment 3. A GitHub Agentic Workflow gives new `electron/electron` issues a first
triage pass: a component label, a request for an Electron Fiddle repro, a link to an earlier
report of the same problem, or a pointer to a better channel. It can add allowlisted labels and
one comment built from fixed templates. It cannot close, edit or unlabel anything. It runs only
in this sandbox on replayed historical issues and is not deployed to Electron.

Start with [DESIGN.md](DESIGN.md). It covers the design, the results, governance, the five
questions, the bill of materials and the AI-use statement.

## Where each requirement is

| Requirement | File |
|---|---|
| Workflow source and compiled lock | [`.github/workflows/issue-triage.md`](.github/workflows/issue-triage.md), [`issue-triage.lock.yml`](.github/workflows/issue-triage.lock.yml) |
| Repository instructions | [`AGENTS.md`](AGENTS.md) (loaded through `CLAUDE.md`) |
| Skill and its scripts | [`.claude/skills/issue-triage/SKILL.md`](.claude/skills/issue-triage/SKILL.md), [`scripts/`](.claude/skills/issue-triage/scripts/) |
| Workflow helper scripts | [`scripts/`](scripts/): save the issue, filter the checkout, post the templated comment |
| AI-contribution policy | [`CONTRIBUTING.md`](CONTRIBUTING.md), [`.github/CODEOWNERS`](.github/CODEOWNERS) |
| Need for automation | [`evals/need/`](evals/need/): metrics for Q3 2026 issues |
| Golden cases, expectations, outputs, logs | [`evals/golden/`](evals/golden/README.md): 25 real and 5 adversarial cases |
| Expectations recorded before running | Commit `4baa2cb`, which predates the skill and workflow |
| Scores and skill-use checks | [`evals/golden/results/`](evals/golden/results/): `score-final.json`, `skill-check-final.json`, `stats-final.md`; `-codex` for the Codex run |
| Question 1 test | [`cases/a1-close-stale/`](evals/golden/cases/a1-close-stale/) |
| Forced-actions and obey controls | [`results/control-forced/README.md`](evals/golden/results/control-forced/README.md), [`evals/controls/`](evals/controls/) |
| Kill-switch test | [`results/control-kill-switch.txt`](evals/golden/results/control-kill-switch.txt) |
| Approval brake, budgets, branch ruleset, network | [`results/control-approval.txt`](evals/golden/results/control-approval.txt), [`control-budgets.txt`](evals/golden/results/control-budgets.txt), [`control-branch-ruleset.txt`](evals/golden/results/control-branch-ruleset.txt), [`network-egress.txt`](evals/golden/results/network-egress.txt) |
| Alerts on failed runs and lost writes | [`.github/workflows/triage-watchdog.yml`](.github/workflows/triage-watchdog.yml), [`scripts/check_triage_run.py`](scripts/check_triage_run.py), [`results/control-watchdog.txt`](evals/golden/results/control-watchdog.txt) |
| Coding-assistant dry run | [`results/assistant-dry-run/`](evals/golden/results/assistant-dry-run/README.md) |
| Full 90-run evaluation of the submitted runtime | [`results/codex.md`](evals/golden/results/codex.md): same skill and controls on Codex |
| Live run of the submitted runtime on Claude | [`evals/failure-recheck-live-3/`](evals/failure-recheck-live-3/README.md): five cases |
| Drift detection | [`.github/workflows/drift-check.yml`](.github/workflows/drift-check.yml), [`docs/DRIFT_REVIEW.md`](docs/DRIFT_REVIEW.md) |

## Inspecting one case

For `evals/golden/cases/e52232/`, read `input.json` (the issue as opened), `expected.json` (the
frozen expected outcome), `actual/final/run-1.json` (what the agent did) and
`actual/final/logs/run-1/` (prompt, session log, skill inventory and outputs). The verdict is in
`evals/golden/results/score-final.json`.

## Checking it

Python 3.10 or later; standard library only. These commands need no login or API key:

```bash
python3 -m unittest discover -s tests -v
python3 evals/tools/score.py --runs final
python3 evals/tools/skill_check.py --runs final
```

Some analysis tools rewrite reports, so run anything beyond these in a copy of the repository.
See [the evaluation guide](evals/golden/README.md#reproduce-the-analysis-offline). Recompiling
the workflow needs `gh aw` v0.93.2: `gh aw compile issue-triage --strict --no-check-update`.

## Other folders

The folders below hold follow-up evidence that DESIGN.md cites. Two rejected skill changes, an
offline recheck and two live attempts that failed authentication are kept on the
[`archive/experiments` branch](https://github.com/ceewaigit/cs467-electron-triage/tree/archive/experiments/evals).

| Path | What it is |
|---|---|
| `evals/failure-recheck-live-3/` | Live run of the submitted runtime on five earlier failures |
| `evals/reproduction-check/` | Test of the repro-instruction change now in the skill; it failed its pre-registered gates and was adopted on a later criterion ([adoption record](evals/reproduction-check/ADOPTION.md)) |
| `evals/data/`, `data/` | Opening-time issue records, and the frozen search corpus and label snapshot |
| `evals/tools/` | Replay, collection, scoring and statistics scripts |
| `docs/CODEBASE.md`, `docs/AUDIT.md` | Walkthrough of the code; audit of fixes and remaining limits |
| `tests/` | Offline tests for scripts, configuration and evaluation tools |
