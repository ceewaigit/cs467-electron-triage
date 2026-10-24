# Independent publication review — initial finding

Reviewed on 24 October 2026 by a separate Codex reviewer. This review began from the
original REQUIREMENTS.md, AGENTS.md, codebase instructions, proposed documentation and
saved sources, without the coordinator's earlier conversation. The reviewer formed its
documentation assessment before reading the experiment's discussion of prior reviews.
The coordinator later supplied its inventory/test summary; the reviewer had independently
computed the same inventory exceptions first. This is an AI review, not a human sign-off.

## Publication blocker

The new tests depend on the baseline commit being present in local Git history.
`tests/test_judgment_experiment.py` calls `EXP.helpers(ROOT)` and `EXP.source(ROOT, ...)`;
`evals/judgment-check/experiment.py:33–34` implements that source read using `git show`
of `90724fe`. The unchanged `.github/workflows/checks.yml` uses the default single-commit
checkout. Once publication adds a new tip, that checkout will not contain the baseline.
The local 119-test pass therefore does not establish that these new tests can pass CI.

The reviewer reproduced the original test's error under a synthetic missing-baseline
condition, without network or Git mutations. See
[source](independent-ci-dependency-source.py) and [result](independent-ci-dependency-reproduction-v2.json).
This is not a hosted CI execution. The first reproduction is also preserved; v2 corrects
only its traceback source display after the maintained test was concurrently edited.

Before publication, make the maintained tests portable to the unchanged CI checkout while
preserving the original test, frozen experiment, decisions and runtime. Then verify a
disposable export with no Git history. The coordinator is addressing this finding; this
initial report does not declare it resolved.

## Documentation assessment

No documentation blocker was found. DESIGN.md remains exactly 150 lines and its final
section is the AI-use statement. The drift policy identifies `ceewaigit`, review before
model/runtime acceptance or deployment, additional triggers, all 30 golden cases and the
specific outputs/failures to inspect. It says paid monitoring is unscheduled, why it is
deferred, that CI cannot detect provider behavior changes, and that the human policy is
not automatically enforced. It expressly retains current sandbox triggers. It does not
claim a new hosted test or completed acceptance.

The stale data/README.md statement is correctly replaced: all 15 current runtime hashes
match the saved live manifest at `1173463`, including preparation script hash
`808aed32b67860e9e9f30ee19a25e05b962560210d4a37f49443ce923566e6f1`.
Five saved successful outcomes name that source. These are ordinary executions and do not
prove complete isolation; the revised wording retains that distinction and Git-history risk.

PUBLICATION.md and the experiment README distinguish later publication authorization from
the rejected adoption. The frozen decision is `accepted: false`; original RESULTS.md and
final-state records retain their historically accurate uncommitted/no-push statements.
The root summary agrees with the saved rows: 45/48 fresh current-policy passes and 44/48
candidate passes, with the GPU gain and retained app mismatch confined to known cases.
No A+, student-understanding, submission, or human-review certification is made.

## Integrity and publication checks

[The independent check](independent-publication-check.json) found only the four intended
documentation changes among 5,502 prior tracked files, and only the new README notice among
1,203 pre-existing experiment/test files at that point. The runtime, golden cases, scorer,
original results, sealed decisions, and original test were unchanged. This snapshot predates
the coordinator's test portability correction, which needs a separate follow-up inventory.

The inventory records raw worktree hashes. A raw Git archive comparison differed for 199
historical logs because their worktree CRLF bytes normalize to LF in Git. Every such log
still matches its original raw inventory and is identical after line-ending normalization;
see [explanation](independent-line-ending-explanation.json). The initial check's
`prior_inventory_matches_named_commit: false` is this encoding distinction, not new drift.

Relative file targets in the seven reviewed documents exist. A bounded credential-pattern
scan of 1,209 publication inputs found no matches, symlinks, NUL-bearing binaries, or files
larger than 50 MiB. This heuristic is not a guarantee of absence of secrets; public issue
material and local execution-path provenance are intentionally retained. The saved
full-history suite log contains 119 tests in 57.205 seconds, OK.

This review performed no provider call, network access, workflow dispatch, new evaluation,
commit or push. It does not re-evaluate every prior semantic judgment, test hosted limits,
verify remote state, certify deployment readiness, or replace owner/student review.
