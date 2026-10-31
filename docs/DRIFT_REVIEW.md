# Drift review

`.github/workflows/drift-check.yml` reruns every golden case once on fresh sandbox issues,
scores the outputs with the frozen scorer, compares them with a reference run set
(`evals/tools/drift_report.py`) and opens a `drift-review` issue assigned to the owner when
anything changed. The job has no AI and no secrets.

It runs on manual dispatch. The weekly run (Mondays 03:00 UTC) starts only while the repository
variable `DRIFT_WEEKLY` is `true`. That is off in this sandbox, where nothing is live and each
run spends provider credit, so today a silent provider change goes unseen until someone
dispatches a check. An explicit model ID does not pin the provider's weights.

The check needs `triage-writes` free of required reviewers: a run waiting for approval holds the
job until its time limit, and no review issue opens.

The `final` reference for Claude is weak: it predates later skill changes, and `e54035`, `e54123`
and `e54317` have no output there, so they are listed as "no reference" and not compared. Run
a full set on the current runtime and use it as the reference before relying on a Claude check.

Two runs so far, both on the Codex copy against the `codex` reference, using a workflow choice
since removed. All 30 cases at `5511ef8`
(`drift-41161648267`, review issue #350): no new failure, e52255 passed once (0/3 before), and
two outputs changed (e52255 dropped its comment; e53610 linked three similar issues). Pass rate
.84, error cost .32, adversarial 5/5. Two cases at `ade9c8c` (`drift-41173979997`), to check the
job itself: it ran unattended, both matched the reference and no issue opened.

## When review is required

The owner must review fresh golden results before accepting a changed model or runtime for
hosted use, or approving deployment beyond the evaluation sandbox. A known provider change
or an unexpected allowed label/comment also prompts review. Documentation-only changes do
not require paid model runs. This is a documented human review policy; CI and branch settings
do not enforce it automatically.

## What the owner reviews

For a drift check, use all 30 frozen golden cases, including no-action cases and
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
(about $8 at $0.25 a run). `ceewaigit`
reviews every item in the review issue within two days and records keep, revise or disable.
Any new failure triggers the full three-repeat acceptance run before the configuration stays
enabled. One repeat can reveal drift but does not replace that run.
