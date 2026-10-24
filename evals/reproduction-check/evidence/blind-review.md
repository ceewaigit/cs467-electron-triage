# Independent review: retain the original policy

The candidate does **not** meet the frozen adoption rule. The independent calculation
was saved at `2026-10-24T05:07:12.494745+00:00`, before opening `score.json`, the README
Results section, or any parent assessment. Subsequent comparison matched all cohort
summaries, 120 scored rows, eight paired action changes, 23 gates and the rejection.
Six gates fail: strict constructed-cost improvement, strict reproduction-omission
improvement, and positive-control full-case success, in each repetition. The separate
known regression passes but cannot override the fresh-comparison requirements.

| Cohort and measure | Original 1 | Candidate 1 | Original 2 | Candidate 2 |
|---|---:|---:|---:|---:|
| Historical full-case passes | 17/18 | 18/18 | 17/18 | 17/18 |
| Historical total weighted cost | 1 | 0 | 1 | 1 |
| Historical required-action omissions | 1 | 0 | 1 | 1 |
| Constructed full-case passes | 11/12 | 11/12 | 11/12 | 11/12 |
| Constructed total weighted cost | 1 | 1 | 1 | 1 |
| Required reproduction actions missed, both cohorts | 0 | 0 | 0 | 0 |
| Unwanted reproduction actions, both cohorts | 0 | 0 | 0 | 0 |
| Constructed positive links retained | 2/2 | 2/2 | 2/2 | 2/2 |
| Constructed positive components retained | 10/10 | 10/10 | 10/10 | 10/10 |

The 120 proposals are valid and have the required successful checks and label/comment
validation before their unique first decision. There are no safety, label-limit,
security-combination, unsupported-reference, duplicate-reference or reporter-reference
violations. Every required/forbidden reproduction disposition is satisfied in both arms;
the two optional installer targets remain optional.

The eight paired changes are fully accounted for: `e51619` and `e51963` lose optional
reproduction requests in both repetitions; candidate adds an accepted component on
`e51950` in repetition 1; candidate omits optional components on `e51014` in repetition 1
and `e50678` in repetition 2; and candidate adds accepted reference 51767 on `e52098`
in repetition 1. All other scored action sets tie. The historical gain is one component
decision, not evidence of an improvement in reproduction requests.

The shared `r01-multiline-constructor` failure is a **predeclared annotation mismatch**:
all four proposals add `component/transparent`, which the target does not accept. The
opening explicitly describes lost transparency, so that additional component is
defensible under the broad component rule. This audit does not establish that it is
semantically wrong. Keep the original target and score intact. Even discounting this
shared mismatch would leave the strict constructed-cost and reproduction-omission
comparisons tied in both repetitions, so non-adoption does not depend on that judgment.

Evidence integrity and procedure were checked independently:

- All 132 frozen files and 3,143 prior file hashes match. The original rubric, scorer
  and 60 golden input/expected files also match `4baa2cb`; runtime files match
  `962fac774c7845bca0da2d310ca1bdcca09c50ea`. Candidate policy bytes differ only in
  section 3. Tracked runtime, helpers, hints, workflow and earlier evidence are unchanged.
- Sampling independently reproduces seed 4672027, all 55 prior source-ID exclusions,
  eligible counts 49/38/45, six draws per month, and retention of all 18 original opening
  inputs. The reviewed dataset binds all 102 case files and 30 cutoff corpora. The
  final review predates preparation and every fresh context/decision.
- All 120 workspaces were reconstructed without importing the experiment wrapper.
  Normalized inputs, strictly earlier corpus bytes, context hashes, anonymous arm mapping
  and paired case order match. Paired snapshots differ only in the assigned skill.
  The 1,920 original prepared files and original proposal/transcript/context copies
  also match. Prepared inventories contain no grading data, expected files or Git history.
- All 120 proposals, JSONL transcripts, readable transcripts, displayed contexts, seals,
  export-validation records and actual outputs were checked. Commands precede decisions;
  cases follow their prescribed session order; decisions precede the common seal.
  Fresh context starts at `04:56:31.345005+00:00`; the last decision is at
  `05:02:27.679059+00:00` on 2026-10-24.
- All 265 recorded fresh helper calls and 145 fresh export-validation calls were
  replayed from reconstructed snapshots, matching stdout, stderr and exit status.
  The known case adds three helper calls and two export validations, also matching.
  All 21 emitted reference occurrences exist in the eligible corpus and precede the cutoff.
- Two annotation-time retrieval rankings (`e51619`, `e51393`) differ in order from
  execution, with exactly the same five IDs. Targeted offline replay proves this is
  caused by the frozen replay neutralization of title/body: original text reproduces
  the review order, normalized text reproduces execution. Initial observations and the
  resolution remain in the check record. No missing reviewed candidate or unresolved
  evidence-integrity finding remains.

The known `e51957` case is not fresh and was excluded from every cohort count. Its input
and original expectation are unchanged. The candidate policy, context, unique proposal,
transcripts, validation commands and frozen score independently verify both reproduction
actions and the original full-case pass. The executed collector source is preserved;
its strengthened successor adds protocol/policy/context and malformed-proposal checks.
Original file/workspace hashes and the added verification record agree, and the independently
reconstructed export and score match the preserved result. No assistant retry was performed.

This reviewer authored none of the compared policies, dataset, annotations or harness and
executed no assistant case. Required `AGENTS.md`/`docs/CODEBASE.md` and the pre-execution
review exposed historical aggregates: final 79/90, hardened 0/90, fallback 20/25 real and
5/5 adversarial, costs 0.56 versus 0.44, the synthetic-reference rejection and e54317 noop
wording. The known-case collector-verification metadata disclosed its earlier pass before
paired collection; no paired outcome or parent score was read before independent calculation.
This is result-blind checking of the fresh comparison, not complete blindness to history.

The source and README are readable and their result claims match the evidence, including
the annotation caveat. These are local proposed actions using existing Codex access,
AI-authored/AI-reviewed targets and two correlated repetitions. Recorder logs do not prove
isolation of the assistant's entire environment. No hosted Claude, paid replay, GitHub
enforcement, threat detection, posting, population generalization, statistical significance,
conventional-rule superiority or A+ acceptance is established. Exact backend identity and
metered assistant usage are unavailable. The existing hosted results retain their status.

The executable [independent-check-source.py](independent-check-source.py) never invokes
`primary_decision` or a new assistant. [independent-check-results.json](independent-check-results.json)
preserves the initial independent computation and later comparison, supplemental checks and
retrieval resolution separately, with timestamps and source/report hashes. To rerun, copy
the experiment to a disposable location under a copy of this repository, remove only that
copy's independent result, then run the source followed by `--compare-parent`,
`--supplemental-checks` and `--resolve-retrieval`. The latter two checks require the original
runner workspaces recorded in the dispatch files. Do not overwrite original evidence.

Recommendation: retain the original runtime. Preserve this unsuccessful candidate experiment;
do not revise expectations, redraw cases or repeat first decisions to obtain adoption.
