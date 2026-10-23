# Golden tasks

30 cases for the issue-triage agent: 25 real issues from `electron/electron` (opened July to
September 2026) and 5 adversarial inputs. Rules for what counts as correct are in `RUBRIC.md`.

## What was fixed before any run

Commit `4baa2cb` (2026-10-23) froze `RUBRIC.md`, every `cases/*/input.json` and
`cases/*/expected.json`, and `evals/tools/score.py`. The skill and workflow came after it. Check
with `git log --follow -- evals/golden/cases/e52232/expected.json`: no later commit changes them.

## Layout

```
cases/<id>/input.json        issue as it was when opened (title, body, labels set at opening,
                             author association, as_of = opening time)
cases/<id>/expected.json     expected outcome, written before any run
cases/<id>/actual/agent/     run-1..3.json: what the agent did, read back from GitHub
cases/<id>/actual/agent/logs/run-N/   artifacts of that run (agent session, safe outputs, ...)
cases/<id>/actual/baseline/  rule-based baseline output
cases/<id>/actual/obey/      control: workflow told to obey the issue text (adversarial cases)
replay/                      sandbox issue numbers, run IDs, live-trigger skips
results/                     scores, agreement with maintainers, static scans, controls
```

### Cases

- **Curated (17):** chosen from the research sample to cover each decision: component only, repro
  request, similar issue, security, third-party, site policy, upstream, maintainer-authored.
- **Random (8):** seed 467 over the other Q3 outside issues (`evals/tools/build_cases.py`), so
  the set is not only cases picked to be interesting.
- **No-action cases:** the 4 skip cases (maintainer authors) plus every case whose expected
  outcome has no comment (for example `e54317`).
- **Adversarial (5):** `a1-close-stale` (claims a maintainer approved closing stale issues),
  `a2-hidden-comment` (instructions in an HTML comment), `a3-tool-error` (asks the agent to run
  `curl | bash`), `a4-label-request` (asks for priority labels), `a5-poisoned-corpus` (the
  injection sits in an *earlier* issue, synthetic corpus row #900001, that the similar-issue
  search returns).

### How inputs avoid post-event information

The title and body are the first revision (GraphQL `userContentEdits`, oldest entry), not the
current text. Labels are only those set within 120 s of opening by the issue form or Electron's
bots. The similar-issue search only sees corpus issues opened before `as_of`. Known leak:
`author_association` is today's value (`RUBRIC.md`).

## Reproduce

Needs `gh` (logged in, with admin on your sandbox copy), `gh aw` v0.93.2, Python 3.10+, and the
repository secret `ANTHROPIC_API_KEY`. Change `REPO` in `evals/tools/replay.py` to your copy.

```bash
python3 -m unittest discover -s tests          # offline
bash evals/controls/broken_config.sh           # offline; needs gh aw
python3 evals/tools/replay.py labels           # create the labels the cases use
python3 evals/tools/replay.py file --k 3       # 90 sandbox issues (bodies neutralised)
python3 evals/tools/replay.py dispatch --k 3   # 90 workflow_dispatch runs
python3 evals/tools/replay.py collect          # waits, writes actual/agent/run-*.json + logs
python3 evals/tools/skill_check.py             # did the skill load and run, per run
python3 evals/tools/score.py --runs agent
python3 evals/tools/baseline.py && python3 evals/tools/score.py --runs baseline --k 1
```

Control with the obeying prompt (copy `evals/controls/issue-triage-obey.md` to
`.github/workflows/`, `gh aw compile issue-triage-obey --strict`, push, then):

```bash
A=a1-close-stale,a2-hidden-comment,a3-tool-error,a4-label-request,a5-poisoned-corpus
python3 evals/tools/replay.py file --variant obey --k 3 --cases $A
python3 evals/tools/replay.py dispatch --variant obey --k 3 --cases $A
python3 evals/tools/replay.py collect --variant obey --cases $A
python3 evals/tools/score.py --runs obey
```

Runs are not bit-for-bit reproducible: the model samples, so expect some per-case variation.
That is why each case runs three times and the score reports pass^3.
