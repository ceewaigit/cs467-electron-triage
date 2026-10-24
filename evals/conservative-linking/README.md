# Fresh-case comparison of more conservative triage instructions

This experiment compares the submitted skill at commit `962fac7` with a candidate that asks
for stronger evidence before linking an earlier issue or adding a component label. The candidate
requires a matching failure plus a distinguishing detail for links. It distinguishes the failing
component from APIs mentioned only in setup, workarounds or diagnostics. It still asks the agent
to retain well-supported links, labels and reproduction requests.

Only those two skill sections change. The scripts, hint table, templates, workflow permissions
and original golden evaluation stay unchanged. Both policy snapshots are in `policies/`.
The [original dry run](../golden/results/assistant-dry-run/README.md) remains evidence of its own
configuration; this comparison does not correct or replace any of its five failed decisions.

## Design fixed before execution

The [protocol](protocol.json) records the source commit, policy hashes, comparison and adoption
criteria. An independent annotator selected eight outside-contributor issues from each month
of Q2 2026 with seed 4672026, retaining all 24 regardless of difficulty. These are fresh cases for
this evaluation, not a claim that their text was absent from research, retrieval data or model
training. Six separately reported constructed cases check boundaries and positive behaviour.
They are invented controls, not additional historical observations.

Expected outcomes are written from opening text and earlier corpus evidence before either arm
runs. A second reviewer checks those annotations without seeing the candidate instructions or
new outputs. The review records any uncertainty and any exposure to earlier project summaries.
The frozen historical scorer is reused on this new dataset; its old cases and expectations are
not changed. A separate reference audit checks every proposed link because the scorer's
`refs_any` test alone does not reject extra incorrect references beside an acceptable one.

The annotator and reviewer both encountered limited old-results prose through the repository's
required codebase guide. Neither read the candidate instructions or new outcomes. Their
[annotation notes](ANNOTATION_NOTES.md) and [pre-execution review](pre-execution-review.md)
disclose this exposure, the uncertain cases and the accepted file hashes. These expectations
were AI-authored and independently AI-reviewed; the student remains responsible for them.

Both policies receive two passes on the same inputs and filtered corpus. Fresh Codex assistants
receive anonymous case batches and only one policy; no assistant compares both versions of a
case. Each handles up to ten cases in order, so within-batch carry-over remains possible.
Decisions and actual local helper calls are recorded with the existing recorder. The first
proposal is preserved, including mistakes. Expectations, version mappings and scores remain
outside the prepared runner copies. This is procedural separation, not a sandbox that prevents
all wider filesystem or tool access.

## Adoption criteria

The candidate must lower historical weighted error cost in **each** repetition, without reducing
historical case passes or increasing missed required actions. It must introduce no safety
failure or invalid final proposal. Constructed-case passes must not decline, all designated
positive controls must pass, and unsupported references must not increase. All conditions were
specified before model execution. Suppressing every link or label cannot satisfy these checks.

Two passes on a small selected cohort can show a useful local difference, but cannot establish
statistical significance, deployment acceptance or superiority to the conventional rule baseline.
Changing both instructions together also does not identify which change caused a difference.

## Execution limits

This uses the existing Codex assistant rather than the configured hosted Claude engine; the
exact inherited backend model identifier is not exposed. Existing assistant inference is used,
with no exposed metered-cost total. No Anthropic API call, paid hosted evaluation, workflow
dispatch or GitHub triage write is part of this experiment.

The transcripts capture displayed context, helper commands/results and proposed decisions.
They do not capture private reasoning or certify the entire assistant environment. GitHub
permissions, hosted threat detection, posting, network restrictions, budgets and cancellation
are not exercised. Opening-state reconstruction and present-day author-association limitations
remain, and annotations still require judgement. The deferred 90 hosted evaluations remain pending.

## Follow and reproduce the evidence

| Path | Purpose |
|---|---|
| `select_cases.py`, `selection.json` | Exact random selection, eligibility sets and saved source digest; selection refuses overwrites |
| `cases/<id>/input.json`, `expected.json`, `annotation.json` | Opening input, expected actions and the evidence supporting the annotation |
| `cases/s*/corpus.jsonl` | Explicit invented corpus for each constructed control; historical corpora are reconstructed from the baseline source |
| `policies/` | Exact original and candidate skill text |
| `experiment.py` | Preparation, reconstruction, collection and scoring; no model invocation or network access |
| `evidence/frozen/`, `evidence/manifest.json` | Pre-execution copies and hashes of source, annotations, policies and protocol, plus private batch mapping |
| `evidence/batch-prompts/`, `evidence/dispatch-prompts/` | Instructions supplied to each execution assistant |
| `cases/<id>/actual/<arm>/run-N.json` | Preserved first proposed actions; no GitHub writes |
| `cases/<id>/actual/<arm>/logs/run-N/` | Canonical JSONL, readable transcript, normalized issue, context hashes, proposal and export validation |
| `evidence/sealed-proposals.json`, `evidence/collection.json` | Seals for every first decision/transcript and exported file |
| `evidence/score.json` | Both repetitions, pooled cohorts, every changed action and the predeclared adoption decision |

Corpus reconstruction needs no network: the freeze contains the exact baseline runtime, and
filtering uses each opening timestamp. The recorder and helpers are unchanged. `experiment.py`
has four explicit stages: prepare the input-only batches, reproduce their snapshots, collect
already-recorded decisions, then score the sealed exports. It cannot generate new assistant
decisions.

From the repository root, these commands test the code and reconstruct inputs without inference:

```bash
python3 -m unittest discover -s tests
python3 evals/conservative-linking/experiment.py reproduce --destination /tmp/NEW_UNUSED_DIRECTORY
```

Evidence commands refuse to overwrite existing files. To reproduce the score, copy this
experiment directory to a new temporary location, remove only that copy's `evidence/score.json`,
and run `experiment.py --experiment COPIED_DIRECTORY score`. Compare the resulting report with
the preserved one. This scores the recorded proposals; it does not rerun the assistant. Do not
run selection, preparation or collection over the preserved experiment.

## Results

All 120 first decisions were recorded and sealed before scoring. The candidate **did not meet
the adoption criteria**: historical error cost was identical in both repetitions. The fresh
independent review confirmed that result and recommended keeping the original policy. The
submitted runtime has been restored, and no commit or push was made. The candidate and this
experiment remain saved locally; the submitted files and original golden results are unchanged.

| Measure | Original, pass 1 | Candidate, pass 1 | Original, pass 2 | Candidate, pass 2 |
|---|---:|---:|---:|---:|
| Historical cases passing | 23/24 | 23/24 | 23/24 | 23/24 |
| Historical weighted error cost | 2/24 (0.0833) | 2/24 (0.0833) | 2/24 (0.0833) | 2/24 (0.0833) |
| Missed required actions | 2 | 2 | 2 | 2 |
| Constructed cases passing | 6/6 | 6/6 | 6/6 | 6/6 |
| Constructed positive links retained | 2/2 | 2/2 | 2/2 | 2/2 |
| Unsupported references | 0 | 0 | 0 | 0 |
| Scored safety failures / invalid final proposals | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |

Both policies passed 46/48 historical trials when the two repetitions are pooled, with mean
weighted error cost 4/48 = 0.0833. Repeated cases are correlated; pooling does not create 48
independent historical observations. All constructed component-positive checks also passed.
Neither policy linked any historical case, so these observations do not demonstrate better
link selection. Both omitted the two annotated historical supported-link opportunities in each
pass; those links were optional under the outcome rubric. Both retained the two deliberately
clear constructed links in each pass.

The same historical case, `e51957`, failed in all four trials. Both policies omitted the
`blocked/need-repro` label and `need-repro` comment. Its constructor snippets do not supply a
complete runnable app under the frozen annotation. This costs two units per trial; the new
linking/label instructions did not correct that reproduction judgement. The original outputs
and expectations remain unchanged.

There were seven paired action differences, none changing a case's score:

| Case | Observed difference |
|---|---|
| `e50682` | In both passes the candidate kept fullscreen and omitted the additional BrowserWindow label. Either choice was acceptable. |
| `e51940` | Original used both DevTools and node-integration. Candidate used DevTools in pass 1 and node-integration in pass 2. Each was an accepted interpretation. |
| `e51957` | Candidate omitted the additional BrowserWindow label in both passes; both policies still missed the same required repro actions. |
| `e52087` | In pass 1, original requested repro/upstream while candidate used the security-only route. Both were allowed by the pre-execution annotation; pass 2 had no paired difference. |

The candidate therefore made six fewer component-label proposals across the 48 historical
trials, but those omitted labels were already acceptable. Fewer suggestions alone is not the
predeclared definition of improvement. The security-routing difference is also not evidence
that the component/link changes caused a reliable routing improvement.

The full [score report](evidence/score.json) preserves every trial, changed action and gate.
All final outputs were valid proposals, and all recorded cases ran the checks and validated
their proposed labels/comments before finishing. No actions were posted. These figures must
not be compared directly with the original golden dry run's 20/25: the cases and independently
reviewed annotations differ. The conventional rule baseline was not run on this new cohort.

## Independent audit and final disposition

The [blind review](evidence/blind-review.md) independently calculated the outcome before reading
the parent report. It reproduced all 251 recorded helper calls and 131 export-validation calls,
checked all 120 first decisions, context/proposal/transcript hashes and readable transcripts,
and matched the saved scores, changes and adoption gates. It found no observed label-limit,
security-combination, unsupported-reference or evidence-integrity violation. The review's
scope remains this preserved local experiment, not hosted enforcement or proof of statistical
equivalence between policies.

The audit found one latent bookkeeping issue in the comparison wrapper: it counted strong
coverage references as supported but omitted separately annotated acceptable optional links.
No recorded output proposed an affected link, so the issue changed no observed score or gate.
The working `experiment.py` now accepts both sets when checking unsupported references and
still counts only strong matches as positive coverage. A new temporary-fixture regression test
covers that distinction. The exact execution-time wrapper remains unchanged in
`evidence/frozen/experiment.py`; the correction occurred after execution and is recorded in
[harness-correction.json](evidence/harness-correction.json).

Rescoring a disposable copy with the correction reproduced the original score report byte for
byte. All 82 local unit tests passed after the correction and restoration of the submitted
skill. This bookkeeping fix supplies no reason to adopt the candidate. The required strict
historical cost reduction failed in both repetitions, and the user authorized a commit/push
only if the policy improved. No further runs or expectation changes were made to seek a win.
