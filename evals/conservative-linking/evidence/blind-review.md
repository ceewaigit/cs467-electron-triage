# Independent post-execution review

**Verdict: retain the original policy; do not adopt the candidate.** The evidence
is internally consistent and the independent scores agree with the saved report,
but both predeclared strictly-lower historical cost gates fail. No result was
repaired or excluded, and no expected answer was changed.

This review was performed by a separate AI assistant that did not author the
policies, cases, annotations, harness or execution proposals. I first read the
frozen protocol, expectations and first proposals and calculated scores and gates
without opening `evidence/score.json` or this experiment's README Results section.
The first calculation completed before those files were opened; the final audit
also rechecked the saved score for agreement. I read repository instructions and
only the architecture/script-description portion of `docs/CODEBASE.md` (lines
14–146), avoiding its old-results sections. This is an independent AI audit, not
human verification or a claim of a distinct model family.

## Independent outcome

The unchanged `score_run` from commit `4baa2cb` was applied to scorer fields
reconstructed from each preserved proposal and the unchanged comment renderer.
The scorer file SHA-256 matches the pre-execution freeze and the baseline commit.

| Cohort / repetition | Original passes | Candidate passes | Original total cost | Candidate total cost | Required omissions per arm |
|---|---:|---:|---:|---:|---:|
| Historical 1 | 23/24 | 23/24 | 2 | 2 | 2 |
| Historical 2 | 23/24 | 23/24 | 2 | 2 | 2 |
| Constructed 1 | 6/6 | 6/6 | 0 | 0 | 0 |
| Constructed 2 | 6/6 | 6/6 | 0 | 0 | 0 |

Historical mean weighted cost is **2/24 = 0.0833333333** for each arm in each
repetition. Pooled historical outcomes are **46/48 passes and cost 4/48** per arm.
Pooling is descriptive: the repeated cases are correlated. The constructed
cohort remains separate and is **12/12** per arm when pooled.

The same historical case, **e51957**, fails in all four preserved decisions:
`blocked/need-repro` and the `need-repro` comment are omitted. Each trial incurs
two missing-action units. I inspected its input: the frozen expectation treats
its constructor examples as API calls rather than a complete runnable app. This
was decided before execution and is not revised after observing the failures.

Actual positive-action coverage, separately from optional-action rubric passes:

- Historical component controls: **15/15** per arm in each repetition.
- Constructed component controls: **5/5** per arm in each repetition.
- Constructed link controls: **2/2** per arm in each repetition. All eight emitted
  references across the experiment are the designated constructed matches.
- Historical supported-link opportunities: **0/2** per arm in each repetition
  (`e51741` and `e51962`). Neither policy emits any historical similar link,
  including the other two cases with acceptable optional links.

There are **zero** scored safety failures, invalid final proposals, unsupported
references, reporter-linked references repeated, excessive labels, excessive
component labels, or security/reproduction combination violations. All final
requests comply with the at-most-three-label, at-most-two-component, and
security-only/no-need-repro-label constraints.

There are seven paired action differences. In both repetitions, the candidate
omits an additional acceptable component on e50682, e51940 and e51957. Historical
component-label proposals therefore decrease from **40 to 34**, with no change
in any case's score. In repetition 1 only, e52087 changes from repro/upstream to
security-only; both are pre-accepted alternatives. These differences are not
error reduction. Both arms retain every required component control. Both
strict-cost gates are false; the other twelve gates are true. Adoption is false.

## Evidence integrity and execution checks

The reusable [verification source](independent-check-source.py) and
[machine-readable findings](independent-check-results.json) record the checks,
all case scores, omissions, differences, coverage and chronology.

- Baseline HEAD and declared source were
  `962fac774c7845bca0da2d310ca1bdcca09c50ea` at review. The original policy equals
  that commit. The candidate differs only in **Component label (0–2)** and
  **Similar earlier issues**; all other skill sections are identical. All 15
  runtime files and the recorder, scorer and replay code match the baseline.
- The 1,797 tracked files under the prior golden evaluation and evaluation tools
  have unchanged Git content. The 30 old inputs, 30 old expectations, rubric and
  scorer match `4baa2cb`. There are 199 old checked-out log files with CRLF bytes
  where the committed blob uses LF; each is identical after the existing Git
  normalization (`core.autocrlf=input`), and the old evaluation has clean Git
  status. This is not a claim of literal working-file byte identity for those
  logs, and no old file was edited.
- All 123 frozen-file hashes, current annotation/input copies, case metadata
  hashes and review anchors agree. I independently reproduced the monthly
  selection pools (**57, 46, 53 eligible**) and all 24 draws with seed 4672026.
  The 30 prior input files yield 25 excluded historical issue numbers, with no
  selected overlap. All 24 opening inputs match the saved source fields.
- The annotation reviewer explicitly covered all 30 cases before execution,
  independently searched earlier candidates, and documented three resolved
  ambiguities. The disclosed limited historical-summary exposure of both
  annotator and reviewer remains a limitation. Their accepted hashes, not
  post-outcome reinterpretations, are used here. I additionally inspected the
  six constructed input/corpus pairs and the failed and ambiguous cases above.
- A new temporary reconstruction contains exactly 12 batches of ten cases,
  covering **24 historical + 6 constructed × 2 arms × 2 repetitions = 120**
  decisions. Independent seed/order reconstruction matches all batch mappings.
  All 60 pairs have identical input, corpus and runtime hashes except the skill.
  Each original and reconstructed checkout has exactly the 16 recorded input
  files, with no grading files or extra files. Every corpus is the exact eligible
  prefix/override, strictly earlier than its input timestamp.
- All original runner proposal/transcript bytes match the collected evidence.
  All 120 proposals and JSONL transcripts match their seals; all 840 exported
  file hashes agree. Each transcript ends in exactly one preserved decision,
  with monotonic event times and the prescribed within-batch case order.
  Every Markdown transcript represents the JSONL events exactly.
- I reexecuted **all 251 recorded helper calls** and **all 131 export-validation
  calls** from reconstructed input copies: **382/382** exactly reproduce stdout,
  stderr and exit code. There were **zero rejected calls** to discard. The 120
  checks, 95 label validations and 36 comment validations all precede their
  decisions. Omitted `--refs` means the renderer's default empty string; thirteen
  such calls produce exactly the final request's validated comment.
- Every exported label list and rendered comment faithfully represents the
  original final request. All proposed reference arguments are preserved, at
  most three, accepted by the earlier corpus and absent from the reporter's
  linked-issue set. No final request was silently repaired.

The locally recorded chronology is:

| Event | UTC |
|---|---|
| Annotation review accepted | 2026-10-24 02:46:28.096239 |
| Manifest prepared | 2026-10-24 02:46:59.298297 |
| First recorded execution event | 2026-10-24 02:47:24.071697 |
| Last first decision | 2026-10-24 02:54:16.076716 |
| All proposals sealed | 2026-10-24 02:54:38.948649 |

The reviewed protocol, case/annotation hashes and reviewer sign-off precede the
first recorded execution event. These are consistent local records and hash
anchors, not independently timestamped or signed provider evidence.

## Saved report and interpretation

After calculating independently, I compared the saved report: **all case
scores, summaries, paired differences and adoption gates agree exactly**.
The README Results section correctly reports a tie and non-adoption, preserves
the repeated e51957 failure, separates the constructed cohort, and avoids
claiming fewer optional labels as better accuracy. Its pending-review statement
can now be updated to reference this audit. The runtime was returned to the
original policy under the predeclared conditional adoption rule.

One nonblocking implementation limitation was found and corrected after the audit:
The frozen `experiment.py` computes `unsupported_refs` by subtracting only
`coverage_supported_refs`. The frozen annotation separately permits optional
references 48582/47661 for e51442 and 50783 for e51876, which are absent from that
narrower coverage set. If emitted, those accepted optional references would be
misclassified as unsupported by the saved scoring wrapper. This audit checks
against the union of accepted optional references and coverage references and
also checks reporter-link exclusion. **No historical references were emitted,
so this discrepancy changes none of the observed counts, scores or gates.**
It does not justify revising frozen outcomes or rerunning decisions.

After this finding, the parent assistant changed only the working scoring wrapper
to subtract both reference sets, and added an isolated-fixture regression test. I
inspected the exact source delta and verified the recorded hashes in
[harness-correction.json](harness-correction.json). The frozen helper and all
execution evidence remain unchanged. I independently rescored another disposable
experiment copy with the corrected wrapper: its report is **byte-identical** to
the preserved score, SHA-256
`1426935d7a9a9a0c8ad991476d003b81c23dbc6e298174f68d645da6f316f014`.
The parent reports all 82 unit tests passed after this correction; this audit
verified the delta and independent rescore, rather than duplicating that suite.
The runtime skill has been restored to the original policy, and tracked Git
content is clean. The verifier reconstructs from the frozen harness and records
the active working policy and working-wrapper digest separately.

The saved prompts request fresh contexts with no parent history and exclude
other batches, gold and alternate policies. The original snapshots confirm that
separation of files, but these artifacts cannot prove the actual inherited model
context or exclude unrecorded wider tool access. The recorder is not a complete
provider session log or enforcement boundary. The exact backend and inference
cost are unavailable, and model-assisted annotation/review can share biases.
Each assistant handled ten cases, so carry-over within a batch remains possible.
Both policy sections changed together. None of this evidence establishes hosted
execution behavior, deployment acceptance, statistical significance, or
superiority to a conventional rule baseline. No network/provider call, workflow
dispatch, source edit, old-evidence edit, commit or push was performed by this audit.
