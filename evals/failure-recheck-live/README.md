# Targeted live recheck: authentication blocked

The owner authorized a limited live recheck after updating the repository API secret.
Only the first of five planned cases, e52255, was dispatched. It failed before inference
because Anthropic required a workspace ID. The remaining four cases were not dispatched.
There are **0 valid live triage decisions** from this attempt.

| Evidence | Value |
|---|---|
| Source | `7debabe981d26af3ff36cc4606f45bc6efb1daf3` |
| Model and runtime | `claude-sonnet-5-5`; Claude Code 2.1.300; gh-aw v0.93.2; AWF 0.28.70 |
| Sandbox issue | [217](https://github.com/ceewaigit/cs467-electron-triage/issues/217) |
| Manual run | [40066776440](https://github.com/ceewaigit/cs467-electron-triage/actions/runs/40066776440), failed |
| Automatic issue-event run | 40066727162, all seven jobs skipped |
| Recorded inference usage | Agent: two internal harness attempts, zero tokens and $0 each. Detection: zero tokens and zero AI credits. |
| Observed triage writes | No labels, comment or other writes |

The provider rejected the unscoped key with HTTP 400 and requested the
`anthropic-workspace-id` header. The refreshed-key retry is retained separately in
[failure-recheck-live-2](../failure-recheck-live-2/README.md). Neither failed execution is
a correct no-action result. Recorded usage is not a verified provider invoice.

## Evidence and spending controls

The [manifest](manifest.json), [protocol](PROTOCOL.md), [pre-execution seal](pre-execution-seal.json)
and [result](result.json) identify the exact runtime, inputs and outcome. The
[preflight review](preflight-review.json) records cost and harness limitations.
The [budget stop rule](budget-stop-rule.json) was recorded after dispatch but before the result:
stop before another dispatch if one run exceeds $0.50, total recorded cost reaches $2, or cost
evidence is missing. These are between-run stopping rules, not a hard provider billing cap.
The workflow's separate agent and detector limits still govern an in-flight run.

`runs/40066776440/` contains the complete named artifacts and workflow log. Use
`run-completed.json`, `jobs-completed.json` and `artifacts-completed.json` for final status;
the earlier metadata files are retained snapshots from collection while the run was active.
The detection job's successful job status does not establish a successful provider execution
or threat verdict. Its internal provider call also failed, and no detection result was produced.

The normal replay collector omits usage artifacts. Full artifacts are retained here to make
the zero-usage statement inspectable. `automatic-trigger-control.json` records the skipped
issue-event run separately: its association is temporal because the run-list title does not
contain the issue number. An empty collector skip list would not establish this control.

`run.py` wraps the unchanged sandbox replay helper, requires one explicit case and k=1, checks
the pinned runtime and remote commit, and refuses automatic overwrite. Its `file` and `dispatch`
commands create sandbox issues and start potentially paid workflows. `collect` reads GitHub
and saves results; it does not trigger inference. Do not repeat this preserved experiment.
The framework made two internal startup attempts despite the SDK retry setting; a workflow
dispatch is not a promise of exactly one provider request.

All prior tracked files were hashed before execution in [prior-files.json](prior-files.json).
Historical results, frozen expectations and runtime code were not changed for this recheck.
The [free five-case diagnostic](../failure-recheck-offline/README.md) is separate evidence.
The [independent live review](../failure-recheck-offline/evidence/live-review.md) verifies
both failed attempts and states the remaining limits of a workspace-header repair.
