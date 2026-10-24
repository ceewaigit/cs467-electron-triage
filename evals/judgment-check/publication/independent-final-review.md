# Independent publication review — final assessment

No unresolved blocker remains for publishing the reviewed documentation, rejected-experiment
evidence, and test portability correction. This is the same independent Codex review recorded
in [the initial assessment](independent-initial-review.md); it is not human approval, an A+
prediction, hosted acceptance, or verification of the eventual commit/push.

## Initial finding resolved

The first review found that the new tests required an older Git object absent from CI's
single-commit checkout. The maintained test now substitutes a source reader only while its
synthetic unit tests run. That reader loads archived sources and verifies their manifest
hashes; the experiment harness still uses its original pinned Git source. No workflow,
production runtime, frozen experiment, scorer, or expected outcome was changed.

[Independent correction checks](independent-correction-check.json) confirm:

- All 23 sources supplied by the new reader match the corresponding bytes at `90724fe`.
- All existing test-class methods, including the 16 test methods, are structurally unchanged.
- The original test matches both its publication inventory hash and frozen experiment copy.
- Altering either a runtime fixture or known-case fixture is rejected by the new reader.
- The disposable export exists without `.git`; an independent Git probe returns 128.
  Its maintained test matches the recorded source hash. The saved full-suite log and its
  hash agree: 119 tests passed in 54.687 seconds, with return code 0.

The coordinator ran that full suite; the reviewer inspected the export, checked its absence
of Git history, verified the source/log hashes and independently checked fixture equivalence
and mutation rejection. This resolves the observed portability dependency; it is not a claim
that a hosted Actions run has already occurred. The initial failure evidence remains intact.

## Documentation and preservation

The final documentation retains the initial review's satisfactory findings: DESIGN.md has
150 lines and ends with its AI-use statement. Drift review identifies the human owner,
triggers, golden cases and outputs to inspect, explains deferred paid scheduling and CI's
limitations, and does not imply automated enforcement or a disabled sandbox workflow.
The stale replay statement accurately identifies the existing five live runs at `1173463`
and preserves the incomplete-isolation and historical-exposure limits.

PUBLICATION.md discloses the test correction and distinguishes authorization to publish
from adoption of the rejected candidate. The rejected decision, original scores, first
decisions, historical no-commit statements, and requirement-review conclusions remain intact.
The current policy still has its two recorded live mismatches; the 90-run plan stays pending.

The final inventory check finds only DESIGN.md, README.md, data/README.md, and docs/CODEBASE.md
changed among the 5,502 prior tracked files. Among the 1,203 pre-publication experiment/test
files, only the README publication notice and maintained test loader changed. The original
test is preserved separately. All 15 current runtime hashes remain identical to the saved
live manifest. Exact reviewed document and test hashes are in the correction-check JSON.

The original link and bounded publication-safety checks are in
[the initial check](independent-publication-check.json). They found no broken relative file
targets or credential-pattern matches among the inspected publication inputs. The recorded
raw Git/worktree mismatch is explained by the preserved 199 CRLF logs in
[the line-ending audit](independent-line-ending-explanation.json), not by rewritten results.

## Scope and remaining limits

The review reads the original assignment and repository instructions and independently checks
the proposed publication. It does not repeat all historic semantic judgments, infer that the
candidate was adopted, certify student understanding or eLearn submission, promise a grade,
or test provider drift, hosted enforcement, spending limits, deployment, or mobile operation.
It performs no provider call, network request, workflow dispatch, paid evaluation, commit or
push. Owner/student review responsibilities remain explicit in the unchanged AI-use statement.
