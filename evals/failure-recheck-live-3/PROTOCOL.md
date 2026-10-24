# Five-case live recheck

This follows the owner's renewed authorization to use the updated API secret. Only the five
previous dry-run failures are selected: e52255, e52266, e52385, e52463 and e53734, in that order.
Each gets one new sandbox issue and one workflow dispatch at source `117346362d6f0123926b430597a1277e5a6f44de`.
The first case also checks that the updated credentials and current workflow work end to end.

Run sequentially. Inspect the first run's outcome, artifacts, model identity and costs before
starting another. Stop on billing, setup, enforcement or evidence-integrity failure. Do not
retry a wrong decision to obtain a pass. Do not launch the separate 90-run hardened experiment.
If the first run has unexpectedly high usage or its costs cannot be inspected, pause further
paid dispatches and report the uncertainty. Agent-session cost excludes threat detection;
report available cost components separately and do not invent a total invoice amount.

The runner delegates issue creation, mention neutralisation, dispatch and collection to the
unchanged replay helper. Existing owner-authored issue events should skip before inference;
verify that control before each manual dispatch. Workflow permissions, model, skill, runtime
limits and compiled lock stay unchanged. Every case retains its frozen opening input and
expectation. Expected outcomes are evaluator-side only and must not be sent to the agent.

Save the new outcomes and native session evidence under this directory. Keep all previous
results intact. Independently score the first outcomes with the frozen scorer and have a
fresh checker review their correctness and any remaining submission issues before reading
the coordinator's conclusions. Distinguish rubric disagreement from an implementation bug.

This targeted, single-repeat check cannot establish population accuracy, pass cubed or the
complete hosted acceptance protocol. It uses configured Claude, whereas the earlier dry run
used Codex. Differences therefore cannot be attributed solely to the reproduction wording.
Cases were selected because they previously failed; do not replace their old outcomes or
combine them with the old 20 passing cases to claim a new full-suite pass rate.

This third credential attempt follows another owner-confirmed secret update. The fifteen
runtime files are byte-identical to source `7debabe`. Preserve both preceding failures.
No workflow/header change is being tested: a workspace-scoped replacement key can satisfy
the provider requirement without changing the runtime. Scope is not proven by metadata.

Before every further dispatch, require inspectable agent and detector usage. Stop if a
completed run estimate exceeds $0.50 or cumulative estimate reaches $2. These thresholds
apply between runs and cannot cap a request already in flight. Do not retry a wrong
decision for a passing score. Stop on authentication, setup, safety or evidence failure.
