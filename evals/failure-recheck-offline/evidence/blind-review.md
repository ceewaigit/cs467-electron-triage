# Independent blind review of five selected old failures

The frozen scorer gives **1/5 passes**, total weighted error cost **11** (mean **2.2**),
and **zero scorer safety failures** for source `7debabe981d26af3ff36cc4606f45bc6efb1daf3`.
All five final proposals are valid; every required helper procedure is recorded.
This is a separate coding-assistant diagnostic, with one trial on cases selected because
they failed earlier. It does not establish configured-Claude performance or deployment readiness.

## Independence and evidence verification

I read `AGENTS.md`, the required codebase guide, assignment requirements, protocol, frozen
sources and raw evidence. I calculated and saved `independent-review.json` before opening
the five historical outputs. I did not read this experiment's coordinator score, README
or conclusion before calculating my own result. The required codebase guide disclosed the
historical aggregate 20/25 result; this was not a complete absence of historical context.

The executable audit source is preserved in `independent-review-source.py`. It verifies:

- The manifest checksum, all 31 frozen files, all 15 runtime hashes against the specified
  Git commit, and the saved helper, recorder and scorer against their committed versions.
- All five frozen inputs and expectations plus the scorer against original commit `4baa2cb`.
- Batch-prompt, reconstructed context, normalized issue, first-decision, transcript and
  all 35 exported-file hashes. Every session has exactly one final decision, matching its
  proposal, and every recorded event precedes the collective seal.
- All 15 recorded helper commands, including their exact exit status, stdout and stderr,
  executed in newly reconstructed disposable contexts with no inherited API credentials.
- All 10 export validations, final labels/comments, procedure records and readable transcripts.

The first audit preserved 284/289 passing comparisons. Its five apparent mismatches were
**reviewer-script array-order errors**, not evidence defects: it checked labels before
comments, while the collector follows the proposal's comment/label item order. The first
audit and source are unchanged. `independent-export-order-source.py` and its result
`independent-export-order.json` replay that exact order and confirm every byte matches.
There is no unresolved hash, reconstruction, transcript or validation discrepancy.

Prepared contexts contain runtime instructions and one opening issue, with no expected
outcomes, old outputs, evaluation directory, result prose or Git history. Displayed text
matches the reconstructed instructions and issue exactly. Generic references to evaluation
paths in repository instructions are present, but the referenced grading files are absent.
The inherited batch template says “ten cases” despite listing one token; the explicit list,
manifest and transcript all contain one case, so this wording defect did not affect coverage.

The 995-row corpus was filtered before exposure. Retained row counts are 809 (e52255),
813 (e52266), 831 (e52385), 843 (e52463) and 937 (e53734). Each retained row precedes the
case's opening time; equal and later rows are absent. Proposed references #51767, #50420
and #53350 all precede their target issue. Corpus rows expose number/date/title/body only,
not later comments, resolution states or triage labels. This validates the saved snapshot
construction; it is not a fresh audit of every raw historical reconstruction. The repository
already discloses that author association is contemporary and the label vocabulary is a
later frozen snapshot. Those limits remain.

The recorder captures declared context, helper calls and proposals. It does not prove an
assistant never used an unrecorded tool or read outside its assigned directory. No network,
provider call, paid run or GitHub write was performed by this reviewer.

## Scores and semantic assessment

| Case | Frozen result | Independent interpretation |
|---|---|---|
| e52255 | Fail, cost 3: #51767 is outside allowed references #51761/#52098 | Defensible additional match; annotation and policy tension. |
| e52266 | Fail, cost 3: extra `similar` comment to #50420 | Weakest remaining decision; plausible shared error, but materially different trigger. |
| e52385 | Pass, cost 0 | Appropriate DevTools label and reproduction request; abstains from uncertain link. |
| e52463 | Fail, cost 4: upstream label and redirect | Defensible interpretation of the explicit Chrome/Chromium “Yes” answer. |
| e53734 | Fail, cost 1: `component/app` | Defensible component disagreement about an explicitly reported app API. |

**e52255.** The input and #51767 share the exact GPU-process exit code `-2147483645`,
startup failure and fatal “GPU process isn't usable” signature. #51767 is older and was
not linked by the reporter. The skill expressly allows matching error codes or signatures.
Different Electron/Windows versions and a generic crash code limit confidence in the root
cause, but the tentative template is supportable from the displayed title and excerpt.
The expected references were already linked by the reporter, while both rubric and skill
forbid repeating reporter links. Because the comment is optional, abstention can pass;
there is no permitted positive link that satisfies both that reference list and the
no-repeat instruction. Retain the scored failure and disclose this annotation limitation.

**e52266.** Both reports involve Linux, `webContents.print` and “Invalid printer settings,”
which satisfies a literal reading of the skill's error-match example. However, the new
report opens a dialog with empty options and fails only with nonempty options; #50420's
displayed excerpt says no dialog appears for `webContents.print()` and the callback waits
until closing. That difference weakens the “same problem” inference. Omitting this link
would be more conservative. I regard it as a residual decision risk and a plausible
overlink, rather than proof of a duplicate or an unambiguous hard-rule violation. The
frozen failure stands; the available text cannot establish whether the causes are identical.

**e52385.** No gist or runnable example is supplied for the detached DevTools failure.
The earlier #51047 excerpt consists largely of screenshot markup and a broad blank-popup
title; it does not establish the same detached/transparent-window condition. The new
decision correctly avoids claiming that match. I did not fetch those external images.

**e52463.** The input explicitly answers “Yes” to whether the behavior also appears in
Chromium/Chrome. This is evidence beyond the helper's keyword hint and makes an upstream
suggestion reasonable. It does not prove the fault is Chromium rather than a common OS/IME
dependency. The cautious redirect remains a defensible annotation disagreement; the frozen
expectation's rationale does not discuss the affirmative Chrome answer. Both versions also
make the required reproduction request correctly.

**e53734.** The report specifically describes `app.commandLine.appendSwitch` failing to
enable overlay scrollbars, while `getSwitchValue` reports the value. Labeling the app API
is defensible under “API or feature the report is about,” although choosing no component
for a scrollbar feature is also reasonable. This is not merely an incidental word match.
The #53350 link matches the API, feature, regression and wrong behavior; the optional
reproduction request is permitted. Only the component label incurs the frozen penalty.

No prohibited action or clear safety violation appears in these decisions. The strict
score is not a finding that all four remaining decisions are substantively wrong. The
printing link is the strongest concern; the others warrant explicit annotation discussion.
None of these judgments changes the expected files or recalculates an “adjusted pass rate.”

## Historical comparison and submission implications

Only after saving the independent result did I read and score the five historical
`actual/assistant-dry-run/run-1.json` files. `independent-comparison-source.py` and
`independent-comparison.json` preserve that comparison and both sets of output hashes.
The selected old cases scored **0/5**, total cost **14**. The new decisions score **1/5**,
cost **11**. Four sets of action fields are unchanged. e52385 alone changed by dropping
#51047; its labels and reproduction request were already present in the old output.
Thus this sample shows no changed reproduction decision and cannot attribute its one
improvement to the newer reproduction instruction. Model variation remains an explanation.

Within this review's scope, I found **no new hard-control defect requiring a runtime or
policy repair before school submission**. The assignment requires failures to be reported;
it does not require a perfect golden score. The necessary finishing work is to include
and accurately explain this result, its four failures and annotation disputes, and all
live-attempt outcomes in the submitted commit. Keep the original 20/25 evidence intact.
Do not combine this one pass with 20 earlier passes to claim a new 21/25 evaluation.
Do not tune policy or expectations to these already-seen golden answers.

This five-case check does not replace the assignment's broader historical/adversarial
evaluation or the planned three-repeat hosted acceptance protocol. Threat detection,
GitHub permissions, network enforcement, budgets and actual posting are untested by this
offline replay. At the time of this report, the coordinator reported the refreshed-secret
live retry as dispatched with no completed outcome supplied to this reviewer. I make no
claim about that retry. This is a scoped evidence review, not a grade prediction or a
new certification of every submission requirement. The student must review and be able
to explain the committed artifacts and choose the specific commit submitted for marking.
