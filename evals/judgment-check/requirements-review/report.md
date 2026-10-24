# Independent original-requirements review

Reviewed submission: `90724fea4152861499063b4f163d84c28348b0d3` only.
Original requirements: `../REQUIREMENTS.md`, SHA-256
`5242b663b3160ceb5c751363eecf9c607b59046dee3b4955118fd6b765733c1d`.

This is a strong, broadly compliant submission. I found no missing required configuration
artifact. It has considerably more evaluation evidence than the assignment minimum, and its
negative results and evidence limits are reported candidly. I would not yet make a confident
A+ recommendation: the student’s review and submission duties remain unverified, the current
status of drift governance needs clarification, and historical evaluation validity and exact
current hosted assurance have genuine limits. No numeric rubric was supplied, so this report
does not invent weights or predict a guaranteed grade.

[The matrix](matrix.md) maps every normative requirement and compound subrequirement one by
one: 101 entries, of which 89 are met, 10 are partial and two are explicit exemptions. These
are traceability counts, not points. Several partial rows refer to the same underlying issue;
they must not be treated as separate grading deductions. The machine-readable versions are
[matrix.json](matrix.json) and [findings.json](findings.json).

## Assignment requirements versus extra acceptance targets

The assignment requires at least ten real historical inputs, no-action cases, at least one
attack, pre-run expectations, actual-versus-expected comparison, failure explanations and a
reproducible record. The golden dataset has 25 real inputs, four explicit skip cases and five
attacks. All original cases were executed three times; all were also covered once in the
historical coding-assistant fallback. The template experiment’s eleven credit failures are
reported separately rather than counted as correct no-actions.

The repository’s 90-run, k=3, pass³ and weighted-baseline acceptance conditions are its own
shadow-deployment protocol. The later strict comparison gates are also self-imposed. Their
incompletion or failure must remain visible, but neither 90 successful paid trials nor zero
model decision errors is an original assignment requirement. I would not prescribe buying
another 90 runs to close an assignment checkbox. Two failed current live model decisions do
not by themselves make the assignment fail: reporting and explaining them satisfies a real
part of the assignment.

Current coverage is broader than five selected hosted cases. After substituting the frozen
candidate skill into its recorded runtime manifest, all 15 files in the adopted reproduction
comparison match the reviewed commit. Its candidate arm has 60 dry-run decisions over 18 fresh
historical inputs and 12 constructed controls. I independently rescored 35/36 historical and
22/24 constructed passes, verified 132 frozen source hashes and all 120 experiment export hash
maps, and confirmed the installed skill equals the frozen candidate. This is current-policy
evidence, but the inherited Codex backend was not the configured Claude model and did not
exercise hosted permission, network, detector or billing enforcement.

## What was verified directly

- The reviewed Git archive contains 5,502 files. Full committed-file SHA-256 values, commit,
  tree and archive hashes are in [source-provenance.json](source-provenance.json).
- All 62 frozen rubric/scorer/input/expected files are unchanged from commit `4baa2cb`.
  That commit is dated 08:46 UTC on 23 October; the earliest inspected original run event is
 09:40:48 UTC. This proves a pre-run freeze, not blind annotation.
- All 25 historical inputs match both saved clean rows and reconstruction from raw source
  nodes. Opening edits and labels are reconstructed by the saved fetcher.
- All 103 offline tests pass from an archive of the exact reviewed commit; see
  [unit-tests.txt](unit-tests.txt). No uncommitted candidate test was included.
- Rescoring `final`, rescoring the historical fallback, recomputing the skill-check summary,
  and regenerating both need-analysis JSON files reproduce the committed data exactly.
  [reproduction-results.json](reproduction-results.json) and command logs retain the checks.
- Both workflows strictly compile with gh-aw `v0.93.2` and produce byte-identical locks.
  The coordinator ran the compiler in a disposable baseline archive; I inspected its output
  and independently matched both reported hashes to my committed archive manifest. See
  [compiler-check/result.json](compiler-check/result.json) and
  [compiler-evidence-verification.json](compiler-evidence-verification.json). The warnings
  concern the intentionally forbidden forced-control curl command and experimental rate
  limiting; permissions were not expanded.
- Direct session inspection finds 79/79 historical `final` Skill invocations and helper calls.
  In the five current hosted sessions, four invoke the Skill tool and one directly reads
  SKILL.md; all expose the current reproduction instruction and execute triage_checks.py.
  This meets load-and-use evidence without incorrectly requiring one specific loader call.
- All 15 current live runtime hashes match `90724fe`. Raw saved timelines attribute current
  triage labels/comments to `github-actions[bot]`; owner-added replay setup labels are distinct.
- Direct rescoring of current runs 40069225337, 40069706446, 40070123304, 40070625159 and 40071013500
  gives 3/5 passes, cost 4, zero scored safety failures. GPU-reference and extra app-label
  mismatches remain failures, with no attempted substitution of a different target.
- DESIGN.md has exactly 150 lines and ordinary wrapping; its longest 169-character line is
  a table row. Its final section is the required AI-use statement.

The full direct results are in [direct-checks.json](direct-checks.json), produced by
[checks.py](checks.py). This reviewer made no provider, GitHub or network calls, read no
uncommitted candidate outcomes, and did not consult existing blind-review conclusion files
before forming the assessment. Ordinary submission documentation and saved execution data
were used. The supplied compiler evidence is separately attributed above.

## What prevents a confident A+ recommendation

**The student still has work only the student can do.** DESIGN.md:150 explicitly says the
latest edits await their review and explanation. Automated checks cannot demonstrate that
someone can explain every script, each permission, the scoring disagreements and the limits
of AI-assisted authorship. The statement is admirably honest, but submission readiness
requires finishing that review, not deleting the admission prematurely. Independence from
other students likewise cannot be inferred merely from using independent AI assistants.

**Drift detection is a proposal, not a clearly adopted current control.** DESIGN.md:93 and
105–108 propose weekly golden checks, k=3 confirmation and owner review. Current CI runs
scripts and a rule baseline; it cannot detect changed provider behaviour. Deferring paid
experiments for cost is reasonable, and the assignment does not demand a paid schedule.
However, the literal instruction says to implement each control or explain why it is
unnecessary/unsupported. A brief owner-approved manual rerun/review gate before reactivation,
model or configuration changes—or an explicit explanation why recurring live monitoring is
unnecessary in the present limited sandbox scope—would close this more cleanly. State that
provider drift may otherwise remain undetected until the next authorised rerun. This is one
underlying concern across G0/G8/Q2/D7, not four deductions.


Suggested wording, **only if the owner adopts this scope and procedure**:

> Live drift monitoring is not scheduled in this evaluation sandbox because each hosted
> rerun spends provider credit. Until the owner authorises a hosted golden rerun, provider
> drift may go undetected; deterministic CI does not test model behaviour. Before any future
> deployment, `ceewaigit` reruns the golden tasks and reviews changed labels/comments, missing
> results and safety failures; weekly hosted reruns remain proposed.

This wording must not be substituted for a claim that a scheduler or a new model rerun was
implemented. If unattended live operation is intended to continue, a genuine owner-approved
review cadence is still needed; an evaluation-only rationale would then be inappropriate.

**The historical evidence cannot support fully blind or leakage-free claims.** Earlier
checkouts exposed future corpus rows and outcome-bearing prose, although inspected direct
Read paths did not show access to those files. Gold selection and hints used hindsight;
author association is a collection-time value. Current preparation removes evaluation
material and filters on-disk corpus rows, but retains Git history and is explicitly context
minimisation. The fresh comparison helps, and honest discussion deserves credit. It cannot
retroactively remove those weaknesses from the older pass rates. Keep the limits rather
than modifying frozen targets or presenting agreement with maintainers as independent gold.

**Exact-current hosted safeguard assurance remains bounded.** The current five live runs
show ordinary skill use, validators, clean detection verdicts and bot output. Historical
attacks and forced controls test their own versions; new negative guards have offline
coverage. That is meaningful evidence, not proof of exhaustive attack resistance or limit
exhaustion. The current fresh dry run must also be credited. More targeted current tests
could strengthen the engineering story if separately authorised, but this is not a claim
that the original assignment demands a new 90-run campaign.

**Submission/access are not established locally.** The owner must submit one specific-commit
GitHub URL through eLearn, ensure that commit is available remotely, and add `ctreude` if the
repository is private. These are pending external/human checks, not defects an offline code
review can repair. Later changes do not count unless the submitted commit is updated.

One small consistency issue is actionable without new evaluation: data/README.md:34 still
says the context-filtering change has no new live replay, while the five current live runs
use those exact files. Update that current summary or label it historical; preserve old
run logs and results. Some experiment READMEs intentionally describe their pre-adoption
state, with ADOPTION.md explaining the later decision; that preserved history is not itself
a reason to overwrite them.

## Recommended order

1. Finish the student review/explanation and make the AI-use declaration accurate.
2. Clarify the current drift policy or its scope-based absence rationale within the 150-line
   DESIGN limit; keep paid recurring work disabled unless separately chosen by the owner.
3. Correct the secondary data-summary inconsistency and retain all failed/missing results.
4. Check the exact final commit tree, GitHub visibility/collaborator access and eLearn link.
5. Treat additional hosted attack/load testing as optional assurance work, not as the only
   route to a good assignment submission. Do not silently claim any incomplete experiment
   has passed.

## Reproduce this review

Start from the repository root. Extract the reviewed commit to a fresh disposable directory;
do not run report-rewriting commands over the saved submission evidence.

```bash
review_snapshot="$(mktemp -d /private/tmp/cs467-requirements.XXXXXX)"
git archive 90724fea4152861499063b4f163d84c28348b0d3 | tar -x -C "$review_snapshot"
python3 evals/judgment-check/requirements-review/checks.py --snapshot "$review_snapshot"
cd "$review_snapshot"
python3 -m unittest discover -s tests -v
python3 evals/tools/score.py --runs final
python3 evals/tools/skill_check.py --runs final
python3 evals/tools/stats.py --runs final --baseline baseline-v2
python3 evals/tools/score.py --runs assistant-dry-run --k 1
python3 evals/need/analyze_issues.py
python3 evals/need/analyze_extra.py
```

The checks script regenerates this review’s direct-checks.json; the remaining commands only
modify the disposable archive. No assistant inference is replayed by these commands. Exact
source hashes and saved raw inputs make the verification reproducible. The disposable full
snapshot is excluded from review deliverables; only source, hashes, matrix and result logs
are retained here.
