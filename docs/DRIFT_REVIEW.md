# Drift review

`.github/workflows/drift-check.yml` reruns every golden case once on fresh sandbox issues,
scores the outputs with the frozen scorer, compares them with a reference run set
(`evals/tools/drift_report.py`) and opens a `drift-review` issue assigned to the owner when
anything changed. It also runs the watchdog check on each run, because the triage watchdog does
not fire for runs this job dispatches. The job has no AI and no secrets.

It runs on manual dispatch, and every Monday at 03:00 UTC while the repository variable
`DRIFT_WEEKLY` is `true` (off in this sandbox, since each run spends provider credit). An
explicit model ID does not pin the provider's weights, so between runs drift can go unnoticed.
While the `triage-writes` environment has a required reviewer, each rerun waits for approval at
its start, writes and conclusion, so approve the batch from the Actions page.

One run so far, on Codex at `5511ef8` against the `codex` reference (`drift-41161648267`,
review issue #350): no new failure, e52255 passed once (0/3 before), and two outputs changed
(e52255 dropped its comment; e53610 linked three similar issues). Pass rate .84, error cost
.32, adversarial 5/5. Both `MEDIUM` labels in that run were held as suggestions and alerted
(#353, #354).

## When review is required

The owner must review fresh golden results before accepting a changed model or runtime for
hosted use, or approving deployment beyond the evaluation sandbox. A known provider change
or an unexpected allowed label/comment also prompts review. Documentation-only changes do
not require paid model runs. This is a documented human review policy; CI and branch settings
do not enforce it automatically.

## What the owner reviews

For an authorized diagnostic, use all 30 frozen golden cases, including no-action cases and
adversarial inputs, in a separate evidence namespace. Agree on the spending budget and trial
count before dispatch. A one-repeat diagnostic can reveal drift but does not complete the
existing three-repeat hosted acceptance protocol. Follow the
[evaluation guide](../evals/golden/README.md) without changing frozen expectations or old results.

Record the model ID, source commit and runtime hashes with the new transcripts, tool calls,
actual outputs, execution failures and available cost records. Compare the same cases using
the frozen scorer. `ceewaigit` reviews every changed label and rendered comment, incorrect
no-action decision, scored failure, missing result and safeguard failure. Check the outputs
even when the workflow job succeeds, and keep ambiguous judgement disagreements visible.

The owner records whether to retain, revise or disable the configuration and why. Failures
require investigation before approval.

## Schedule for sustained operation

Before any deployment beyond this sandbox, set `DRIFT_WEEKLY` so all 30 cases run once a week
(about $3 on Codex at the measured $0.10 a run, about $8 on Claude at $0.25). `ceewaigit`
reviews every item in the review issue within two days and records keep, revise or disable.
Any new failure triggers the full three-repeat acceptance run before the configuration stays
enabled. One repeat can reveal drift but does not replace that run.
