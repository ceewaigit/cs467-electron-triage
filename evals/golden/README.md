# Golden-task evaluation

25 real Electron issues from July to September 2026 and five attacks, each run three times.
[RUBRIC.md](RUBRIC.md) defines correctness and error cost. A successful run does not mean a correct
decision.

| Run set | What ran | Real runs passed | Attacks |
|---|---|---:|---:|
| [`codex-v2`](results/codex-v2.md) | **Final:** stricter skill on Codex (`d1a6dcf`), 90/90 | 65/75 | 15/15 |
| [`codex`](results/codex.md) | Earlier skill on Codex (`801846e` and two same-runtime commits), 90/90 | 60/75 | 15/15 |
| `final` | Template comments on Claude (`5ab5169`), 79/90 | 52/64 | 15/15 |
| `final-requested` | The same runs, scored on [requested labels](results/delivery-final.md) | 57/64 | 15/15 |
| `agent` | Free-text comments on Claude, 90/90 | 59/75 | 15/15 |
| `baseline-v2` | Rules, once per case | 18/25 | n/a |

Controls and one-off runs: [live recheck](../failure-recheck-live-3/README.md) (3/5);
[network](results/network-egress.txt) (both blocked hosts denied);
[approval](results/control-approval.txt) (label landed only when approved); drift
[full](results/drift-drift-41161648267.md) and [job](results/drift-drift-41173979997.md) checks.

## What was frozen

Commit `4baa2cb` (23 October 2026) fixed `RUBRIC.md`, every `input.json` and `expected.json`, and
`evals/tools/score.py` before the skill and workflow existed. Never change them. Check with
`git log --follow -- <path>`.

This proves expected outcomes came before runs. It does not prove blind annotation: component hints
were written after reading the inputs, and research notes held later outcomes.

## Cases

Seventeen curated cases, plus eight random ones (seed 467, `evals/tools/build_cases.py`).

- **Expect a skip:** `e52334`, `e53213` (maintainers); `e53376`, `e53939` (template-check label).
- **No write required:** `e54317`, `e52255`.
- **Attacks:** `a1-close-stale` claims maintainer approval; `a2-hidden-comment` hides instructions in
  HTML; `a3-tool-error` asks for `curl | bash`; `a4-label-request` asks for priority labels;
  `a5-poisoned-corpus` plants an injection in synthetic issue `900001`, which search returns.

**Limits.** Opening text comes from GitHub edit history where available. Opening labels are author
or bot actions within 120 seconds, an approximation. `author_association` is the value at collection.
Runs before the prepare step had the full corpus in the checkout; that step cannot repair them.

## Inspect one case

In `cases/e52232/`: `input.json`, `expected.json`, `actual/codex-v2/run-1.json`, then
`actual/codex-v2/logs/run-1/`. The verdict is in `results/score-codex-v2.json`. A missing output is
missing evidence, not a correct no-action decision.

## Missing runs in `final`

Eleven of 90 Claude runs failed with `billing_error`: `e53939` repeats 2 and 3, and all of `e54035`,
`e54123` and `e54317` ([details](results/final-execution-failures.json)). No output was invented.
So 16 of 21 is over fully sampled cases, not all 25, and no acceptance decision follows from it.

## Files

| Path | Holds |
|---|---|
| `cases/<id>/actual/<set>/` | Outputs and logs per run set; `-requested` copies come from `requested_view.py` |
| `cases/<id>/actual/agent-v2/` | Twelve reruns of four cases after `d76fd0c` |
| `cases/<id>/actual/baseline/`, `baseline-v2/` | Rule baseline, before and after that fix |
| `cases/<id>/actual/obey/` | 15 attack runs under a prompt to obey the issue |
| `cases/e52232/actual/preflight/failures/` | One failed credit check, not scored |
| `replay/` | Sandbox issues, run IDs and manifests per run set; `hardened` has no runs |
| `results/` | Scores, skill checks, statistics, controls and failure records |

## Reproduce the analysis offline

No login or key needed. Several tools rewrite reports, so work in a copy, from the repository root:

```bash
audit_dir="$(mktemp -d)"
cp -R . "$audit_dir/repo"
cd "$audit_dir/repo"
python3 -m unittest discover -s tests -v
python3 evals/tools/score.py --runs codex-v2
python3 evals/tools/skill_check.py --runs codex-v2
python3 evals/tools/stats.py --runs codex-v2 --baseline baseline-v2
```

To check the rule baseline, maintainer agreement and need metrics:

```bash
python3 evals/tools/baseline.py --out baseline-audit
python3 evals/tools/score.py --runs baseline-audit --k 1
python3 evals/tools/agreement.py
python3 evals/need/analyze_issues.py
python3 evals/need/analyze_extra.py
```

`baseline-audit` can differ from `baseline-v2` because it uses current scripts. Agreement is a
consistency check, not independent validation: some later activity was visible during annotation.

With `gh aw` v0.93.2, `bash evals/controls/broken_config.sh` checks that bad permissions and outputs
are caught. It uses temporary copies and starts no runs.

## Rerun it live

This spends provider credit (at most about $23 on Codex), and creates sandbox issues.

You need your own sandbox (set `REPO` in `evals/tools/replay.py`, never `electron/electron`), `gh`,
`gh aw` v0.93.2 and the provider's secret. `triage-writes` must have no required reviewer. Push the
compiled commit to a branch, then in a copy, with a new run-set name:

```bash
wf=issue-triage-codex.lock.yml   # or issue-triage.lock.yml for Claude
python3 evals/tools/replay.py labels --variant rerun-1 --workflow "$wf"
python3 evals/tools/replay.py file --variant rerun-1 --workflow "$wf" --k 3
python3 evals/tools/replay.py dispatch --variant rerun-1 --workflow "$wf" --ref <branch> --k 3
python3 evals/tools/replay.py collect --variant rerun-1 --workflow "$wf"
python3 evals/tools/skill_check.py --runs rerun-1
python3 evals/tools/score.py --runs rerun-1
python3 evals/tools/stats.py --runs rerun-1 --baseline baseline-v2
```

- Use one dispatcher and no other manual triggers: the run list hides the issue number, so a
  concurrent run on that branch can be mismatched. If pairing fails, inspect runs before retrying.
- Compare `head_sha` in the run records with the commit you meant to test.
- Owner-filed issues also fire the live workflow, which must skip.
- Do not use `collect --force` to replace evidence. Failed runs go to `failures/`, unscored.
- If the workflow has expired, compile with `--refresh-stop-time` and commit the lock first.

Three repeats expose some variation but do not establish reliability.

## Rerun the controls

These are live too. **Obey:** compile `evals/controls/issue-triage-obey.md` in your sandbox, then use
`--variant obey --cases a1-close-stale,a2-hidden-comment,a3-tool-error,a4-label-request,a5-poisoned-corpus`
for `file`, `dispatch` and `collect`. **Forced:** compile `evals/controls/issue-triage-forced.md`,
dispatch it on a disposable issue and compare with [the report](results/control-forced/README.md).
It asks for forbidden actions, so keep it in the sandbox. **Kill switch:** disable `issue-triage`,
confirm dispatch is rejected and a new issue starts no agent, then cancel running work.
