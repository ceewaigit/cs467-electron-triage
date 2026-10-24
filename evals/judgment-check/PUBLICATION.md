# Documentation and evidence publication

On 24 October 2026, after the candidate was rejected, the owner explicitly requested the
drift-monitoring wording and stale live-replay statement be fixed, independently reviewed,
and committed and pushed with the audit evidence. The instruction also required the current
policy and original results to stay intact and prohibited paid evaluations.

This is authorization to publish documentation and evidence. The candidate remains rejected;
neither its skill nor any other runtime change is adopted. The original experiment's
no-adoption/no-commit decision describes the state at experiment close. Its protocol, scores,
first decisions, blind reviews, RESULTS.md and final-state records remain unchanged.
Statements in those historical records that the evidence was local and uncommitted are
accurate for that earlier stage; this later publication does not rewrite them.

## Documentation changes

- [DESIGN.md](../../DESIGN.md) now links to a [manual drift-review policy](../../docs/DRIFT_REVIEW.md).
  It names the owner, review triggers, outputs to inspect and the limits of deterministic CI.
  Paid golden reruns still require separate authorization. No scheduler or paid run was added.
- [data/README.md](../../data/README.md) now identifies the five completed live replays whose
  runtime includes the current context-preparation script. It retains the limits of those
  ordinary runs and the historical exposure to future corpus rows.
- The root README and codebase guide link the new evidence and explain the comparison and
  audit scripts. The current triage policy, workflow files, corpus and original results are
  unchanged.
- The blind checker found that the new audit tests depended on a historical Git object absent
  from CI's shallow checkout. Their test-only source loader now uses the saved frozen bytes
  and verifies their hashes. The experiment harness and all test assertions are unchanged;
  the original test is preserved in both the experiment freeze and `publication/`.

The [101-item matrix](requirements-review/matrix.md) and its report still assess `90724fe`.
Their original counts and findings are preserved. The publication review under `publication/`
assesses the documentation changes separately; it does not certify student understanding,
eLearn submission, deployment readiness or an A+.

## Verification record

`publication/inventory-before.json` records hashes of the existing experiment and its test
before publication editing. The earlier `prior-evidence-hashes.json` covers all 5,502 tracked
files at `90724fe`. Publication checks distinguish the edited documentation and test loader from
the runtime, frozen cases, scorer and historical evidence that must remain byte-identical.

Offline checks and an independent documentation review precede the commit. The unchanged
push workflow runs unit tests and the deterministic baseline, with no provider calls. No
triage workflow is dispatched as part of publication. Hosted acceptance and the separate
90-run plan remain pending.
