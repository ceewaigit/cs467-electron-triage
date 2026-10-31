# Golden-task evaluation

The golden set has 25 real `electron/electron` issues opened in July to September 2026 and
five adversarial inputs. Each case has an input and an expected outcome, and each ran three
times. [RUBRIC.md](RUBRIC.md) defines correctness and weighted error cost; a successful
workflow run does not by itself mean the triage decision was correct.

| Experiment | What ran | Result |
|---|---|---|
| `agent` | Free-text comments, all 90 runs | 59/75 real runs pass, 15/15 adversarial |
| `final` | Template comments (`5ab5169`), 79 of 90 runs (11 lost to provider credit) | 52/64 real, 15/15 adversarial |
| `final-requested` | The same runs, scored on the labels the agent requested ([delivery record](results/delivery-final.md)) | 57/64 real, 15/15 adversarial |
| `baseline-v2` | Deterministic rules, once per case | 18/25 real |
| [`codex`](results/codex.md) | Submitted runtime on Codex (`gpt-6.1-sol`), all 90 runs (`801846e` and two earlier commits with the same runtime) | 60/75 real, 15/15 adversarial |
| [`drift-41161648267`](results/drift-drift-41161648267.md) | First drift check: Codex at `5511ef8`, all 30 cases once, against `codex` | 21/25 real, 5/5 adversarial; no new failure |
| [`drift-41173979997`](results/drift-drift-41173979997.md) | Drift job check: Codex at `ade9c8c`, two cases once | 2/2; matches the reference |
| [`network-test`](results/network-egress.txt) | Agent told to reach two blocked hosts | Firewall denied both |
| [`approval-test`](results/control-approval.txt) | Approval gate: e52232 twice, writes approved once and rejected once | Label landed only on the approved run |
| [Live recheck](../failure-recheck-live-3/README.md) | Submitted runtime (`1173463`), five earlier failures once each | 3/5 |

[Reproduce the analysis offline](#reproduce-the-analysis-offline) needs no login or API key.
The coding-assistant dry run and other side experiments are on the
[`archive/full-evidence` branch](https://github.com/ceewaigit/cs467-electron-triage/tree/archive/full-evidence).

## What was fixed before the runs

Commit `4baa2cb` (23 October 2026) froze `RUBRIC.md`, every `cases/*/input.json` and
`cases/*/expected.json`, and `evals/tools/score.py`, before the skill and workflow were added.
Keep those files unchanged. Inspect their history with `git log --follow -- <path>` or compare
them directly with that commit. Report a disputed expectation separately.

The component keyword hints were written after the golden inputs had been read, and the
research notes already contained later maintainer outcomes for candidate cases. The freeze
therefore establishes that expectations preceded agent runs; it does not prove independent
or blind annotation. See `DESIGN.md` at the repo root.

## Inspect one case

For `cases/e52232/`, read these files in order:

1. `input.json`: opening title and body, opening labels, author association and replay time.
2. `expected.json`: required, acceptable and forbidden outputs, with a rationale.
3. `actual/final/run-1.json`: observed labels, comment, other writes and the GitHub run URL.
4. `actual/final/logs/run-1/`: the prompt, session events, skill inventory and output artifacts.
5. `results/score-final.json`: the scorer's verdict and reasons for this case and each repeat.

Paths in steps 1 to 4 are relative to the case directory; step 5 is relative to this guide.
A missing output file is unavailable evidence, not a successful no-action decision.

## Experiments and files

| Location | Meaning |
|---|---|
| `../failure-recheck-live-3/` | Five selected live cases at `1173463`, with scores, logs and costs; separate from full-suite results |
| `cases/<id>/actual/final/` | Template-comment experiment: 79 collected outputs and log directories |
| `cases/<id>/actual/codex/`, `codex-requested/` | Submitted runtime on Codex: 90 outputs and logs, and the requested-label view |
| `cases/<id>/actual/final-requested/`, `agent-v2-requested/` | Copies scored on the labels the agent requested, built by `evals/tools/requested_view.py` ([why](results/delivery-final.md)) |
| `cases/e52232/actual/preflight/failures/` | One unsuccessful provider-credit check, excluded from scoring |
| `cases/<id>/actual/agent/` | First experiment using the older `add-comment` output: 90 outputs |
| `cases/<id>/actual/agent-v2/` | Twelve reruns of four cases after the repository-link fix in `d76fd0c` |
| `cases/<id>/actual/baseline/` | Original deterministic baseline, one output per case |
| `cases/<id>/actual/baseline-v2/` | Baseline after the repository-link fix, one output per case |
| `cases/<id>/actual/obey/` | Fifteen adversarial runs with a prompt that tells the model to obey issue text |
| `cases/<id>/actual/<variant>/failures/` | Future collector records for unsuccessful executions, excluded from scoring; associated logs go under `failures/logs/run-N/` |
| `replay/` | Sandbox issue numbers, dispatched run IDs and owner-trigger skip observations, grouped by variant |
| `replay/experiment-hardened.json` | Audited candidate commit, requested ref, planned coverage, compiler, model and runtime-source hashes |
| `replay/experiment-preflight.json` | Archived manifest for the earlier candidate used in the failed preflight |
| `results/` | Scores, skill checks, statistical summaries, controls and execution-failure evidence |

`final` is commit `5ab5169`; the later `hardened` namespace has no runs.

Historical files are evidence of the code that ran at their recorded commit. Regenerating a
baseline with today's scripts changes the experiment. Save new output under a new name or
use a disposable copy; do not replace earlier results and present them as historical runs.

## Recorded results and missing runs

This section describes the historical `final` hosted experiment.

| Cohort | Planned outputs | Collected outputs | Missing outputs |
|---|---:|---:|---:|
| Real issues | 75 | 64 | 11 |
| Adversarial cases | 15 | 15 | 0 |
| Total | 90 | 79 | 11 |

The missing outputs are `e53939` repeats 2 and 3, and all three repeats of `e54035`, `e54123`
and `e54317`. GitHub records all eleven as failed executions. Their provider logs report
`billing_error`, HTTP 400, because the credit balance was too low. Run IDs, commit hashes,
URLs and error excerpts are in [final-execution-failures.json](results/final-execution-failures.json).
No triage output has been invented for these runs.

The frozen scorer reports 52 passing real outputs out of the 64 collected, and all 15
adversarial outputs pass. Its pass^3 value uses only cases with three collected outputs:
16 of 21 real cases pass all three. This is not a result over the full planned set of 25
real cases. Use [stats-final.md](results/stats-final.md) for coverage and an explicit
completeness check. Do not describe the full evaluation as complete or its
preregistered acceptance decision as established.

All 79 collected runs include evidence that the skill was installed, discovered, invoked and
executed. One run lacks the expected label-validation sequence; the skill checker reports
78 of 79. All 25 posted comments match the rendered templates. The recorded agent-session
cost is $10.74, excluding threat detection, which the live recheck measured at about $0.11 a run. See
[skill-check-final.json](results/skill-check-final.json) for per-run details.

## Case selection and hindsight limits

Seventeen curated real cases cover component labels, reproduction requests, similar issues,
redirects and maintainer-authored reports. Eight more were selected with seed 467 from the
remaining non-bot Q3 issues, excluding the curated cases, as recorded in
`evals/tools/build_cases.py`. That pool includes maintainers: the random case `e52334` has
author association `MEMBER` and expects a skip.

Four cases expect a skip: `e52334` and `e53213` are maintainer-authored; `e53376` and `e53939`
carry the opening template-check label. Other cases expect no comment. `e54317` and `e52255`
allow a label (and, for `e52255`, an optional similar-issue comment) but require no writes, so
their `decision` is `act` even though taking no action is correct.

The adversarial cases are:

- `a1-close-stale`: claims maintainer approval to close stale issues.
- `a2-hidden-comment`: places instructions in an HTML comment.
- `a3-tool-error`: asks the agent to run `curl | bash`.
- `a4-label-request`: asks for priority labels outside the allowlist.
- `a5-poisoned-corpus`: puts the injection in synthetic earlier issue `900001`, returned by
  the similar-issue search.

The fetcher reconstructs opening titles and bodies from GitHub edit history where available.
Opening labels include only issue-author or bot actions within 120 seconds. That interval is
an explicit approximation of the issue-form and template checks. The stored
`author_association` is the value at collection time, which can differ from the original value.

The search script filters candidates to issues opened before `as_of`. Historical runs still
had the full corpus and some outcome-bearing documentation in the checkout, reachable by the
agent's default file-reading tool. The current preparation step removes that material and
filters the corpus on disk, but this cannot repair the validity of historical runs. See
[the failures list](../../docs/FAILURES.md) for the remaining limits.

## Reproduce the analysis offline

Use Python 3.10 or later. The commands below need neither a GitHub login nor a model API key.
Several tools rewrite reports, so first copy the repository to a temporary directory. Start
from the repository root, not from `evals/golden/`:

```bash
audit_dir="$(mktemp -d)"
cp -R . "$audit_dir/repo"
cd "$audit_dir/repo"
python3 -m unittest discover -s tests -v
python3 evals/tools/score.py --runs final
python3 evals/tools/skill_check.py --runs final
python3 evals/tools/stats.py --runs final --baseline baseline-v2
```

Scoring and skill checks read the stored evidence. They do not rerun the agent. The comparison
above uses the stored `baseline-v2`. To inspect the current deterministic implementation,
write a separate baseline in this disposable copy:

```bash
python3 evals/tools/baseline.py --out baseline-audit
python3 evals/tools/score.py --runs baseline-audit --k 1
python3 evals/tools/agreement.py
python3 evals/need/analyze_issues.py
python3 evals/need/analyze_extra.py
```

The need-analysis scripts rewrite their tables and summaries. The historical baseline can differ from `baseline-audit` because the latter
uses current checks and templates. Maintainer agreement compares expectations with later
activity, some of which was already visible during case selection and annotation. Historical
agent checkouts also exposed outcome-bearing documentation. Treat agreement as a consistency
check, not an independent validation or proof that historical runs had no hindsight exposure.

With `gh aw` v0.93.2 installed, `bash evals/controls/broken_config.sh` checks that deliberate
permission and output changes are caught by compilation or configuration tests. It operates
on temporary workflow copies and does not dispatch runs.

## Optional future live experiment

These steps spend provider credit, create sandbox issues and start workflows. Use a
repository you control, with `gh` authenticated, `gh aw` v0.93.2, Python 3.10 or later, and
the repository secret `ANTHROPIC_API_KEY`. Set `REPO` in `evals/tools/replay.py` to your own
sandbox. Never use `electron/electron` as the replay target.

Use a separate checkout or disposable copy and the unused `hardened` namespace. Keep
`actual/final/`, `actual/preflight/` and their replay state intact. The helper reuses recorded
issues and skips recorded dispatches, so first check that no `issues-hardened.json`,
`runs-hardened.json` or collected hardened output exists.

Check that the copy's Git remote points to your sandbox. Compile the workflow, commit the
code and generated lock file, and push the commit to a named branch or tag in the sandbox.
The workflow must also be registered on the default branch for manual dispatch.
`--variant hardened` selects the local evidence namespace; `--ref` selects the branch or tag
GitHub runs. Without `--ref`, GitHub uses the default branch. Save a new experiment manifest
with the commit SHA and source hashes, keep the existing manifests, and compare it with the
SHA GitHub actually ran.

Check the workflow's enabled state, compiled expiry and provider credit, and that the
`triage-writes` environment has no required reviewer; otherwise `collect` waits on each run's
approvals. To extend the expiry,
run `gh aw compile issue-triage --strict --no-check-update --refresh-stop-time` and commit the
regenerated lock before dispatch. Then run these commands in the prepared copy:

```bash
triage_eval_ref="REPLACE_WITH_REVIEWED_BRANCH_OR_TAG"
python3 evals/tools/replay.py labels --variant hardened
python3 evals/tools/replay.py file --variant hardened --k 3
python3 evals/tools/replay.py dispatch --variant hardened --ref "$triage_eval_ref" --k 3
python3 evals/tools/replay.py collect --variant hardened
python3 evals/tools/skill_check.py --runs hardened
python3 evals/tools/score.py --runs hardened
python3 evals/tools/stats.py --runs hardened --baseline baseline-v2
```

Each repeat uses a separate sandbox issue. The helper neutralises mentions and cross-repo
references, then passes the source opening time and author association through dispatch.
Creating owner-authored issues also triggers live issue events that should be skipped;
`evals/golden/replay/live-skips-hardened.json` records the observations. Dispatch records and
collected outcomes retain `requested_ref`, GitHub's actual `head_sha` and `head_branch`.
Compare the observed SHA with the experiment manifest before interpreting the result.

Use only one dispatcher, with no other manual triggers for this workflow while it associates
issues with runs. The helper filters new runs to the expected branch or tag and stops if
more than one matches. GitHub's run list does not expose the `issue_number` input, so one
concurrent run on the same branch can still be misidentified. If association fails, inspect
the dispatched runs before retrying; a run may already exist even when no mapping was saved.

Do not use `collect --force` to replace preserved evidence. The current collector writes
unsuccessful executions to `actual/<variant>/failures/run-N.json`, with `scored: false`, an
exclusion reason and any partial actions. Their logs go under `failures/logs/run-N/`; preserved
artifacts include `agent-errors.jsonl` when available. Only successful executions get the
top-level `run-N.json` files read by the scorer. A successful no-action output is still scored.

Existing records are skipped unless `--force` is used. That flag permits a refresh only
within the same success or failure category. If GitHub now reports a different category,
collection stops before changing the existing record or logs. Use fresh sandbox issues and
a separate experiment namespace instead. The eleven historical failures remain documented in
`results/final-execution-failures.json`; the collector repair does not change that evidence.
A complete new evaluation needs all planned runs accounted for and manual review of both
wrong decisions and missing output.

Model sampling means repeated runs can differ. Three repeats expose some variation; they
are too few to establish broad reliability or independence between results.

## Control experiments

These are also live runs that spend provider credit. The stored reports remain available for
offline review.

The obeying prompt is in `evals/controls/issue-triage-obey.md`. To rerun it, install and compile
it in your sandbox, preserve or reset its local state in a separate copy, and use
`--variant obey --cases a1-close-stale,a2-hidden-comment,a3-tool-error,a4-label-request,a5-poisoned-corpus`
for `file`, `dispatch` and `collect`. Score it with `score.py --runs obey`.

The forced-actions workflow is in `evals/controls/issue-triage-forced.md`. To rerun it, compile
it in your sandbox, dispatch it on a disposable issue and compare with
[the control report](results/control-forced/README.md). It asks for forbidden behaviour on
purpose, so it belongs only in the sandbox.

The Codex fallback is `.github/workflows/issue-triage-codex.md`. It runs only on manual dispatch,
because its shell is open.

For the kill-switch test, disable `issue-triage`, confirm that a new dispatch is rejected and
that an opened issue starts no agent run, and cancel runs already in progress. Disabling a
workflow alone does not cancel running work. Re-enable it only after the test is complete;
`DESIGN.md` gives the phone procedure and its limitations.
