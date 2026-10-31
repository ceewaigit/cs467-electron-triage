# Label writes that did not land

`score-final.json` scores each issue's state after the run. In 12 of the 91 runs in `final` and
`agent-v2`, a label the agent requested never reached the issue. Every
comment matched its request. Requests are in `cases/*/actual/<runs>/logs/run-N/agent_output.json`;
filtered run logs are in `delivery-logs/<run id>.txt`. Checked on 29 October 2026 with
`gh run view <id> --log`; the other runs (agent, obey, failure-recheck-live-3) delivered every
requested label. The `codex` runs are covered in the suggestions section.

## Detection failed, labels withheld (9 runs, all at `5ab5169`)

The provider credit ran out during the batch. The agent finished, then the threat-detection
call failed with "Credit balance is too low" (`THREAT_DETECTION_STATUS: reason=engine_error`).
gh-aw turned this into a `warning` verdict, and its warn policy aborted `add_labels`
(Requirement WTD3). The job still showed success.

| Case | Runs | Sandbox issues | Requested |
|---|---|---|---|
| e53610 | 1-3 | #193-#195 | `component/gpu` |
| e53734 | 1-3 | #196-#198 | `blocked/need-repro` |
| e53747 | 1-3 | #199-#201 | `component/BrowserWindow` |

The next run (e53939 run 1, #202) also had a warning but asked only for no action. Runs 2 and 3
of e53939 and every run of e54035, e54123 and e54317 failed in the agent itself.

At `5ab5169` the `triage-comment` job did not check the verdict, so the six e53610 and e53734
runs still posted their comments after detection had failed. `scripts/post_triage_comment.py`
has refused to post without a `success` verdict since `7ef6696`
(`tests/test_post_triage_comment.py`).

## Recorded as suggestions (3 runs)

Detection succeeded. gh-aw v0.93.2 (`add_labels.cjs`) sends each label with the agent's
rationale and confidence through GitHub's GraphQL `updateIssue` call. GitHub applies a label
marked `HIGH` and stores any other as a suggestion that a maintainer must accept. The run log
says "Successfully added 0 labels" and "Suggested 1 labels"; the issue timeline shows no label.

| Case | Run | Run id | Issue | Requested | Landed |
|---|---|---|---|---|---|
| e52266 (final) | 3 | 39954157858 | #150 | `component/printing`, `blocked/need-repro` (MEDIUM) | `component/printing` |
| e52427 (final) | 1 | 39954337484 | #160 | `component/desktopcapturer` (MEDIUM) | none |
| e52821 (agent-v2) | 2 | 39943781786 | #116 | `component/menu` (MEDIUM) | none |

Across `final`, `agent-v2`, `obey`, `codex` and the drift check `drift-41161648267`, all 125
`HIGH` labels landed and none of the 11 `MEDIUM` labels did (two were in withheld e53747 runs;
the drift check's two were e52463 upstream and e54035 screen). In `codex`, the
suggested labels were `blocked/upstream ❌` in all three e52463 runs, where upstream was the
wrong call, and `component/screen` in e54035 run 3. Labels sent without a confidence (`agent`, most of `final`) landed whenever detection
passed. This works as a partial human-approval step that the workflow does not control: the
agent sets the confidence.

## Scoring what was requested

`evals/tools/requested_view.py --runs final` copies each run with its requested labels, and the
frozen scorer then scores that copy (`score-final-requested.json`, `stats-final-requested.md`).

| View | Run pass rate | All 3 runs pass | Error cost/case (22 cases) |
|---|---:|---:|---:|
| Delivered (`score-final.json`) | 52/64 = .812 | 16/21 | .333 |
| Requested (`score-final-requested.json`) | 57/64 = .891 | 18/21 | .258 |

e52427 and e53747 become 3/3 and e52266 becomes 1/3. e53610 and e53734 passed either way,
because their labels are acceptable rather than required. For `agent-v2`, e52821 becomes 3/3.
For `codex` (`score-codex-requested.json`), the pass rate stays .800 and cost rises from .44 to
.48, because the suggested upstream label on e52463 adds a wrong label to a failed case.
