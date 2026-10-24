# Five-case live recheck

This follows the owner's renewed authorization to use the updated API secret. Only the five
previous dry-run failures are selected: e52255, e52266, e52385, e52463 and e53734, in that order.
Each gets one new sandbox issue and one workflow dispatch at source `7debabe981d26af3ff36cc4606f45bc6efb1daf3`.
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
