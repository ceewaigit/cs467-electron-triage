# Manual review of model drift

This evaluation sandbox has no scheduled provider-drift monitor. Hosted golden reruns spend
provider credit and require separate authorization from the owner, `ceewaigit`. Recurring
paid checks are deferred while deployment approval and the full hosted evaluation are pending.
The current workflow triggers are unchanged; this document does not disable sandbox issue runs.

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

If no hosted rerun is authorized, record the affected configuration as awaiting evaluation.
Do not treat an offline test pass, a coding-assistant dry run or an older model's results as
hosted acceptance. The owner can disable new triage runs and cancel queued/running jobs using
the kill-switch procedure in [DESIGN.md](../DESIGN.md#five-questions) if continued operation is
inappropriate. Reviewing this document authorizes no provider call or workflow dispatch.

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
require investigation before approval; additional paid confirmation runs need separate
authorization. The pending 90-run plan stays pending. Weekly hosted golden reruns remain a
proposal for future sustained operation, with a cadence and budget to be agreed before launch.

This policy clarifies the current governance process. It adds no scheduler, new hosted test,
permission or automatic model-behaviour check, and it does not resolve historical evaluation
limitations or the current policy's two recorded live mismatches.
