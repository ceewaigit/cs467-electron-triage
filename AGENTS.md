# AGENTS.md

Instructions for coding agents (and people) changing this repository. The triage agent itself
follows `.claude/skills/issue-triage/SKILL.md` and the body of `.github/workflows/issue-triage.md`;
this file is for whoever edits those.

## What this repo is

A sandbox for a GitHub Agentic Workflow that does first-pass triage of new issues, tested by
replaying historical `electron/electron` issues. Nothing here is deployed to Electron, and nothing
here may write to `electron/electron`.

## Layout

| Path | What |
|---|---|
| `.github/workflows/issue-triage.md` | workflow source: trigger, permissions, tools, safe outputs, budgets |
| `.github/workflows/issue-triage.lock.yml` | compiled workflow. Generated; never edit by hand |
| `.claude/skills/issue-triage/` | the skill: `SKILL.md`, three scripts, label allowlist, component hints |
| `scripts/prepare_issue.py` | pre-agent step that saves the triggering issue to `.triage/issue.json` |
| `data/` | frozen issue corpus for the similar-issue search, and Electron's label list |
| `evals/golden/` | rubric, 30 cases (`input.json`, `expected.json`, `actual/`), results |
| `evals/tools/` | fetch, case builder, replay, collector, baseline and scorer |
| `tests/` | unit tests for the skill's scripts |

## Commands

```bash
gh aw compile issue-triage --strict          # after any change to the workflow .md
python3 -m unittest discover -s tests        # script tests; no network
python3 evals/tools/score.py --runs agent    # score collected runs
python3 evals/tools/baseline.py && python3 evals/tools/score.py --runs baseline
```

Python 3.10+, standard library only. Do not add dependencies to the skill's scripts: they run
inside the agent's sandbox, which has no package install step.

## Rules

- **Expected outcomes are frozen.** Do not edit `evals/golden/cases/*/expected.json` or
  `evals/golden/RUBRIC.md` after commit `4baa2cb`. If one is wrong, leave it and record the
  disagreement in `DESIGN.md` under test findings.
- **Do not widen the agent's power.** Do not add permissions beyond `read`, a `github` tool, more
  `bash` commands, `jobs:`, or any safe output other than `add-labels`, `add-comment` and `noop`.
  In particular never add `close-issue`, `update-issue`, `remove-labels`, `create-pull-request`,
  `merge-pull-request` or `GH_AW_GITHUB_TOKEN`. Such changes need review from the code owner.
- **Labels the agent may add** are listed twice, in `safe-outputs.add-labels.allowed` and in
  `assets/allowed-labels.txt`. Change both together.
- **Do not tune the skill on the golden cases.** Examples in `SKILL.md` must stay unlike the eval
  cases. Use Q2 2026 issues from `evals/data/` for development.
- **Replayed issues must not reach Electron.** `evals/tools/replay.py` breaks `@mentions` and
  rewrites `electron/electron` links before creating sandbox issues. Do not bypass it.

## Labels in this repo

- `component/*`: the Electron API or feature an issue is about (copied from Electron).
- `blocked/need-repro`: waiting for an Electron Fiddle gist from the reporter.
- `blocked/upstream ❌`: the cause is in Chromium or Node.js.
- `blocked/need-info ❌`, `needs-template`: added only by replay, to mirror Electron's own bots.
