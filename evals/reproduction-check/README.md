# Reproduction requests: fresh offline comparison

The candidate handled the known missed request correctly, but did not demonstrate fewer
reproduction errors on 120 fresh paired decisions. The independent checker confirmed the
failed adoption criteria. The runtime the experiment tested is `962fac7`; its candidate change was later adopted on a separate criterion ([ADOPTION.md](ADOPTION.md)).

This experiment tests one change: distinguish an incomplete code fragment from a runnable
reproduction before deciding whether to request an Electron Fiddle. A multiline constructor
example was mistaken for a complete reproduction in the preceding
[linking/label comparison](https://github.com/ceewaigit/cs467-electron-triage/blob/archive/experiments/evals/conservative-linking/README.md). That known failure motivated the
change; it is excluded from this experiment's fresh cases.

The candidate changes only section 3 of the issue-triage skill. It asks the assistant to check
whether the supplied example includes the startup and inputs needed to reach the failure.
Line counts, code fences, configuration fragments and alternative constructor options do not
establish that. Complete short examples still count, and existing skip, feature, supported-version
and security exceptions remain in place. Scripts, hints, templates, workflow permissions and
linking/component instructions are unchanged.

## Design fixed before execution

The baseline is commit `962fac774c7845bca0da2d310ca1bdcca09c50ea`. Exact policy copies and their
hashes are recorded in [protocol.json](protocol.json). An independent assistant selects and
annotates 18 historical Q2 cases, six per month using seed 4672027, excluding all earlier case
inputs. All sampled cases are retained. It also creates 12 separate controls: five incomplete
examples, three complete reproductions and four cases where a request must be suppressed.
A second assistant reviews the annotations before execution. Neither annotator receives the
candidate policy or this experiment's proposed actions. AI authorship and any context exposure
are disclosed in their records.

Both annotators could see prior aggregate results in the repository docs, and knew the
known-regression check had run. Neither saw its input, policy or proposed actions. This is
recorded in the annotation provenance and review.

Each version handles all 30 cases twice, for 120 first decisions. Twelve fresh assistant
sessions receive anonymous policy names, ten cases each, and the same case order for each
paired repetition. They see opening inputs, the assigned skill and earlier corpus rows;
expected outcomes and previous outputs are excluded from their prepared workspaces. This is
context minimisation, not enforced isolation of the assistant's entire environment.

The primary measure is the constructed reproduction boundary: the candidate must have both
strictly lower weighted error cost and fewer missed required reproduction actions in each
repetition. Every candidate control must make the correct reproduction decision. Historical
cost and omissions must not increase, and historical case passes must not decrease. Unwanted
repro requests, unsafe or invalid proposals, missing helper validation and structural output
violations disqualify the candidate. Positive link/component controls must retain their actions.
The exact gates are in the protocol and executable comparison helper.

A separate one-shot check must also correct the already-observed `e51957` failure against
its original expectation. That is a known regression case, excluded from the 120 fresh
decisions and their reported metrics; it cannot establish generalisation.

These gates differ from the preceding broad linking/label experiment because this change
addresses one specific boundary. They were declared before new decisions were generated.
A gain on invented controls alone is not evidence of better accuracy across real Electron
reports. The two repetitions are correlated; neither cohort establishes statistical significance
or the original hosted acceptance thresholds.

## Evidence and reproduction

`experiment.py` is a standalone adaptation of the preceding experiment's corrected wrapper.
It prepares isolated input directories, reconstructs them, seals first decisions, exports
proposals, and scores them with the unchanged frozen `score_run` function. It calls no model
or network service. Writes use exclusive creation; existing evidence cannot be overwritten.
The source used for execution is itself preserved in `evidence/frozen/`.

| Path | Contents |
|---|---|
| `selection.json`, `select_cases.py` | Sampling rule, eligible IDs, exclusions and selected opening inputs |
| `dataset.json`, `cases/*/{input,expected,annotation}.json` | Independently authored expectations, rationales and hashes |
| `annotation-review.json`, `pre-execution-review.md` | Independent check of the final annotations before execution |
| `policies/`, `protocol.json` | Exact compared instructions and predeclared decision rule |
| `prior-evidence-hashes.json` | Hashes of existing tracked files and the previous local experiment before this work |
| `evidence/manifest.json`, `evidence/frozen/` | Exact inputs, runtime, annotation and execution provenance |
| `cases/*/actual/*/logs/run-*/` | Displayed context, helper calls, first proposal, JSONL and readable transcript |
| `evidence/sealed-proposals.json`, `evidence/collection.json` | First-decision seals and export hashes |
| `evidence/score.json` | Separate cohort results, changed decisions and every adoption gate |
| `known_regression.py`, `known-regression/` | Separate check of the previously observed failure; excluded from fresh metrics |
| `pre-execution-tests.txt` | Complete output from 103 passing offline tests before fresh execution |

From the repository root, reconstruction is offline and performs no new inference:

```bash
python3 -m unittest discover -s tests -v
python3 evals/reproduction-check/experiment.py reproduce --destination /tmp/NEW_UNUSED_DIRECTORY
```

To reproduce scoring, copy this experiment directory to a new temporary directory, remove
only that copy's `evidence/score.json`, and run
`python3 evals/reproduction-check/experiment.py --experiment COPIED_DIRECTORY score`.
Compare the result with the preserved report. Do not prepare, collect or score over existing
evidence, or mistake rescoring for a new assistant trial.

## Cost and limits

Execution uses existing Codex assistant access; the exact inherited backend identifier and
metered usage are unavailable. There are no Anthropic/provider API calls, purchased credits,
paid hosted evaluations, workflow dispatches or external triage writes in this experiment.
The configured Claude engine is not tested. Transcripts record displayed context and commands,
not private reasoning or every part of the assistant's environment. Hosted permissions,
threat detection, networking, posting and budgets remain untested here.

The original results and 90 deferred hosted evaluations retain their existing status. A new
local result does not replace or retroactively validate them. The student remains responsible
for reviewing and explaining the AI-assisted code, annotations, analysis and documentation.

## Results

All 120 first decisions were sealed before scoring. The candidate did not meet the predeclared
adoption criteria. Both versions made all required and forbidden reproduction decisions correctly
on the fresh cases; neither missed a required request or made an unwanted one. The two ambiguous
historical installer cases remain separately identified as optional, not forced into either target.
The independent blind checker reproduced the result and recommended retaining the original.
The owner later adopted the candidate on a narrower criterion ([ADOPTION.md](ADOPTION.md)).

| Measure | Original, pass 1 | Candidate, pass 1 | Original, pass 2 | Candidate, pass 2 |
|---|---:|---:|---:|---:|
| Historical full-case passes | 17/18 | 18/18 | 17/18 | 17/18 |
| Historical weighted error cost | 1/18 (0.0556) | 0/18 | 1/18 (0.0556) | 1/18 (0.0556) |
| Constructed full-case passes | 11/12 | 11/12 | 11/12 | 11/12 |
| Constructed weighted error cost | 1/12 (0.0833) | 1/12 (0.0833) | 1/12 (0.0833) | 1/12 (0.0833) |
| Missed required reproduction actions | 0 | 0 | 0 | 0 |
| Unwanted reproduction actions | 0 | 0 | 0 | 0 |
| Constructed positive links retained | 2/2 | 2/2 | 2/2 | 2/2 |
| Constructed positive components retained | 10/10 | 10/10 | 10/10 | 10/10 |
| Safety / invalid proposal / procedure failures | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |

The strict constructed-cost and missed-reproduction reductions failed in both repetitions.
The positive-control full-case gate also failed: every version added the unaccepted
`component/transparent` label on `r01-multiline-constructor`. Each included the required
WebContentsView component and both reproduction actions, so positive-action coverage itself
was retained. The complete proposal still fails its unchanged expectation. The blind reviewer
considered the transparency label defensible because the reported symptom is loss of transparent
appearance. This is a disagreement with the predeclared annotation, not an established semantic
error. The expectation and score remain intact. Discounting this shared mismatch would still
leave both versions tied on constructed cost and reproduction omissions.

Historical reproduction accuracy did not change. The sole scored historical gain was a
component label on `e51950` in pass 1; the candidate omitted it in pass 2. Across both passes,
original scored 34/36 historical trials and candidate 35/36. Each scored 22/24 constructed trials.
These repeated trials are correlated, and the single component difference does not establish
that the reproduction instruction caused a broader accuracy gain.

Eight paired decisions differed:

| Case | Difference and consequence |
|---|---|
| `e51619`, `e51963`, both passes | Original requested reproduction; candidate abstained. Both choices were accepted for these terminal-only installer cases before execution. |
| `e51950`, pass 1 | Candidate added the required node-integration component; original omitted it. Both omitted a required component in pass 2. Neither requested redundant reproduction. |
| `e51014`, pass 1 | Candidate omitted the additional transparent component. Both label choices were acceptable. |
| `e50678`, pass 2 | Candidate omitted the additional webcontents component. Both label choices were acceptable. |
| `e52098`, pass 1 | Candidate linked 51767 as well as 51761. Both were predeclared acceptable references. |

All other actions tied. No unsupported reference, repeated/reporter reference, label-limit or
security-combination violation was observed. The [score report](evidence/score.json) records every
trial, change and decision gate. Original expectations, source policies and first decisions were
not revised after execution. These cohorts must not be compared directly with the earlier
20/25 results, which used different inputs. No conventional rule baseline was run here.

The separate known regression passed its original expectation: the candidate proposed both
`blocked/need-repro` and `need-repro`, with valid BrowserWindow/fullscreen labels and no reference.
Its first decision and transcript are preserved. Recollecting it with a stricter collector gave
the same result ([collector-verification.json](known-regression/collector-verification.json));
the executed collector is `known-regression/collection-source.py`.

## Independent audit and disposition

The [blind review](evidence/blind-review.md) recomputed the results independently; all 120
scored rows, eight changed decisions and 23 adoption gates match the saved report.

The known regression is corrected in this one candidate trial, but the fresh comparison does
not establish a reproduction improvement: both versions already satisfy the reproduction
expectations. The owner later adopted the candidate on a narrower criterion ([ADOPTION.md](ADOPTION.md)).
No extra cases, changed expectations or repeated decisions were introduced to obtain a favourable result.
