# Manual review of model drift

This evaluation sandbox has no scheduled provider-drift monitor.

CI runs offline script, configuration and baseline checks. It cannot detect changes to the
provider's model behaviour. An explicit model ID does not verify unchanged provider weights,
and no automatic provider-change alert is configured. Drift can remain undetected until the
next authorized hosted rerun, including between unscheduled sandbox runs.

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

## Proposed schedule for sustained operation

Not implemented. Before any deployment beyond this sandbox, run all 30 golden cases once a week
(one repeat each, about $8 at the measured $0.25 per run). This is a diagnostic: `ceewaigit`
reviews every changed output within two days. Any new failure triggers the full three-repeat
acceptance run before the configuration stays enabled. This is the proposal DESIGN.md answers
question 2 with.

This is a policy, not an automated check.
