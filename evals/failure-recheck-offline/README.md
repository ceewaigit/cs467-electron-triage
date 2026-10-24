# Recheck of five earlier dry-run failures

The latest committed configuration, `7debabe981d26af3ff36cc4606f45bc6efb1daf3`, passes
**1 of these 5 selected cases** in one new coding-assistant trial per case. Four still fail
the frozen rubric. Total weighted error cost is 11, compared with 14 for these same five
earlier decisions. This is error cost, not money. No scored safety failure occurred.

The [independent blind review](evidence/blind-review.md) confirms the scores, reconstructed
contexts, helper calls and exports. It identifies the printing link as the strongest remaining
decision risk. It finds defensible interpretations for the other three mismatches, while
keeping all four failures scored. No new hard-control defect was found in this review.

## What happened in each case

| Case | New result | Difference from the old decision | Remaining concern |
|---|---|---|---|
| e52255 | Fail, cost 3 | Actions unchanged | #51767 matches the GPU error signature but is outside the frozen accepted references; the accepted references were already linked by the reporter. |
| e52266 | Fail, cost 3 | Actions unchanged | #50420 shares the printing API and error, but its failure with no options differs from this report's failure with nonempty options. Abstaining would be more conservative. |
| e52385 | Pass, cost 0 | Dropped the uncertain #51047 link | Appropriate DevTools label and reproduction request retained. |
| e52463 | Fail, cost 4 | Actions unchanged | Upstream label and comment conflict with the target, although the input explicitly says Chrome also reproduces the issue. |
| e53734 | Fail, cost 1 | Actions unchanged | The extra app component conflicts with the target, although the reported API is `app.commandLine`. |

The [score](evidence/score.json) uses the unchanged scorer and expectations from `4baa2cb`.
All five original failures and the original 20/25 real-case result remain intact. These
new selected results must not be combined with the 20 old passes into a claimed 21/25 result.
Only one decision changed, and no reproduction decision changed. This trial cannot establish
that the newer reproduction wording caused the difference or that other cases cannot regress.

## Procedure and transcripts

Five fresh Codex subagents each received one opaque input-only workspace and no parent history.
They used the frozen current instructions and scripts, with the corpus restricted to rows
before the issue's opening. Expected outcomes and previous outputs were absent. Each recorded
one first decision, and all five proposals were sealed before scoring. There were 15 successful
helper calls and no invalid final proposals. The exact inherited Codex backend and metered
assistant usage are unavailable; no external provider API or GitHub call was made by these runners.

Each `cases/<case>/actual/latest/logs/run-1/` directory contains the displayed context,
normalized issue, first proposal, JSONL transcript, readable transcript and export validation.
The [protocol](PROTOCOL.md), [manifest](evidence/manifest.json),
[seal](evidence/sealed-proposals.json), [dispatch prompts](evidence/dispatch-prompts/),
and [collection](evidence/collection.json) record how those artifacts were produced.
The recorder covers instrumented interactions, not a complete trace of every assistant tool.

Two procedural limitations are retained: an initial preparation failed before any inference
because batch metadata lacked `opaque_arm` ([record](preparation-note.json)); the inherited
batch prompt says ten cases even though its explicit list and each session contain only one.
Neither discarded a decision or changed the five-case coverage. The blind review also preserves
its own initial export-order comparison error and a separate correcting verification.

## Reproduce without inference

From the repository root, reconstruct fresh input workspaces with:

```bash
python3 evals/failure-recheck-offline/check.py reproduce --workspace /tmp/five-recheck-new
```

The destination must not exist. This only verifies and copies saved inputs; it does not invoke
an assistant. `check.py` is an experiment driver for preparation, reconstruction, collection
and scoring. It reuses the archived context/export helper and writes new evidence exclusively.
Do not run `prepare`, `collect` or `score` over the preserved experiment.

For a new score, copy this experiment directory to a disposable location, remove only that
copy's `evidence/score.json`, and run its `check.py score`. The frozen scorer and helpers are
included. The independent review sources under `evidence/` explain the additional checks;
they need local Git history for `7debabe` and `4baa2cb` and refuse to overwrite their first reports.

## Live evaluation and submission limits

The separately authorized [live preflight](../failure-recheck-live/README.md) and its
[one refreshed-key retry](../failure-recheck-live-2/README.md) both failed workspace
authentication before inference. Their logs record zero inference usage and no triage writes.
They provide no configured-Claude decision or successful hosted-control test. The remaining
four targeted live cases were not dispatched, and the separate 90-run hardened plan is pending.

The [independent live review](evidence/live-review.md) verifies both failed attempts with
167 passing evidence checks. It also explains why merely adding a custom-header variable
has not been verified as a complete fix for the pinned agent, proxy and detector paths.
The [final offline validation](evidence/final-validation.json) records 103 passing tests,
62 unchanged frozen grading files and 15 unchanged runtime hashes. DESIGN remains 150 lines.

The assignment permits a documented coding-assistant fallback. This evidence supports that
route, with the earlier complete fallback and historical live records. It does not establish
an A+ outcome, deployment readiness or a fully passing latest configuration. A student should
be able to explain the printing-link risk, the annotation disagreements and the untested controls.
