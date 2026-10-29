# Result: candidate rejected

The candidate does not meet the conditions for adoption. It removes the GPU reference
rejected by the frozen expectation in both repeats, but the app-label mismatch remains.
It also loses a required build label in one fresh paired trial. The installed policy,
all earlier results and commit `90724fe` remain unchanged. Nothing from this experiment
was committed or pushed.

## Recorded outcomes

All 104 first decisions were saved before scoring: 96 fresh decisions and eight separate
known-case decisions. There were no invalid final proposals, scored safety failures or
procedure failures. Both policies covered the designated positive controls. No provider API,
paid hosted evaluation, workflow dispatch or external triage write was used. The trials used
existing Codex assistant access; its exact backend identifier and metered usage are unavailable.

| Cohort | Current policy passes | Candidate passes | Current weighted cost | Candidate weighted cost |
|---|---:|---:|---:|---:|
| 12 fresh historical cases, twice per policy | 21/24 | 20/24 | 3 | 4 |
| 12 constructed controls, twice per policy | 24/24 | 24/24 | 0 | 0 |
| All fresh decisions | 45/48 | 44/48 | 3 | 4 |
| Two known cases, twice per policy | 0/4 | 2/4 | 8 | 2 |

Weighted cost is the frozen rubric's error measure, not money. Known cases informed the
candidate and are excluded from fresh results. Repetitions and cases sharing a session are
correlated; these totals are not an estimate of deployment accuracy.

## Failures and the adoption decision

- **Known e52255:** both current-policy trials link #51767, which is outside the frozen
  acceptable references. The candidate retains `component/gpu` and omits the optional
  similar comment; both candidate trials pass. The opening already mentions the accepted
  references. No new reference or altered expectation was used to obtain these passes.
- **Known e53734:** both policies add `component/app` in both repeats. That label fails the
  unchanged expectation. Both retain the accepted #53350 reference and reproduction request.
- **Fresh e52099:** both policies miss required `component/build` in repeat 1. In repeat 2,
  the current policy supplies it and passes; the candidate omits it and fails. This is the
  one paired score regression and the one lost fresh pass.
- **Fresh e51065:** both policies, in both repeats, omit the required alternative component
  (`component/BrowserWindow` or `component/webcontents`). Their `component/multithreading`
  and reproduction actions do not satisfy that obligation. These shared failures remain
  in the reported totals.

The [frozen protocol](protocol.json) requires every paired trial to avoid regression and
both known cases to pass both candidate repeats. Both conditions fail. A gain on e52255
does not override them. [decision.json](evidence/decision.json) records `accepted: false`.
No policy rewrite, extra repeat, changed expectation or selective adoption followed the result.

## Independent checks and disagreement

The independent checker sealed its calculations before the coordinator produced score
reports. It reconstructed all 104 contexts, replayed all 239 recorded helper calls exactly,
and matched all 104 coordinator score rows and 52 paired gate dictionaries. All 5,502 prior
tracked files still match their original raw hashes. The full suite passed 119 tests before
execution; the separate committed-submission review passed its original 103 tests.

One candidate-policy session attempted `component/window`. The validator rejected it before
the first final decision; the session then validated `component/BrowserWindow`. The original
rejection remains in the transcript. The independent audit confirmed this was permitted
intermediate validation recovery, not a replaced final decision.

A separate reviewer saw only anonymous action pairs, opening text and earlier corpus for
the three changed pairs. It assessed both directions before their policy identities were
mapped and found no demonstrable semantic harm. It considered the build label a plausible
optional classification, and #51767 a defensible symptom-level similarity whose common cause
was unconfirmed. These judgements disagree with the stricter frozen expectations. The packet
contained abstract comment kinds and references, not rendered comment wording or a complete
project-specific component definition; that limits the semantic assessment.

The disagreement is preserved. It neither changes the scores nor rescues adoption. The
observed score regression does not establish that the instruction change caused a general
decline, just as the known-case gain does not establish a general improvement.

## Evidence and scope

- [Fresh scores](evidence/score.json), [known scores](known-cases/evidence/score.json),
  and every case's `actual/<policy>/logs/run-*/` preserve inputs, helper calls and decisions.
- [Independent calculation](evidence/independent-score.json) and
  [audit](evidence/independent-audit.json) verify scoring, procedure and preservation.
- [Anonymous semantic review](evidence/semantic-review-blind.json) preserves all six
  directional judgements; [mapped review](evidence/semantic-review.json) records adoption scope.
- [Annotation exposure disclosure](evidence/annotation-exposure-disclosure.json) records
  that the annotation reviewer saw later label metadata during provenance checking.
  The case author used opening inputs; no expected outcome was changed during review.
- Frozen sources, context hashes, batch instructions and collection seals are under
  `evidence/`; [execution metadata](evidence/execution-sessions.json) identifies all 20 sessions.

This comparison does not retest configured Claude, hosted enforcement or billing controls.
The separate 90-run plan remains pending. The two earlier live failures remain failures;
this rejected candidate does not update the installed policy's acceptance status.

The separate [requirements matrix](requirements-review/matrix.md) and
[blind grader's report](requirements-review/report.md) assess committed `90724fe` against
the original assignment. They find no missing required configuration artifact, while
identifying drift-governance wording, historical evidence limits, student understanding
and submission duties. The 101 checklist entries are not rubric points.
