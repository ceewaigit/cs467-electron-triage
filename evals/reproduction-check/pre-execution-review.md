# Independent pre-execution annotation review

Accepted before fresh policy execution. Dataset SHA-256: `4b7f69f9d83298a6134144118ce5e9bd3f9a33ca78d1bac56b29b4f4985951f8`.
Annotation provenance SHA-256: `b910a840c0bb75e931d0f35a401cb529b91d7829bd30f529d8d73c4072bf069c`. The machine-readable
`annotation-review.json` binds all 102 case files, per-case corpus hashes, findings and
30 individual review rationales. This is independent AI review, not human authorship
or maintainer adjudication. The exact backend model identifier was unavailable.

The reviewer used the rubric, original skill, scorer and runtime corpus at
`962fac774c7845bca0da2d310ca1bdcca09c50ea`, plus the new openings, expectations and provenance.
Candidate policy wording, prior actual/score/expected files, fresh policy decisions,
later maintainer histories and network material were not consulted. Required
`AGENTS.md`/`docs/CODEBASE.md` exposed historical aggregate results and procedure prose:
final 79/90, hardened 0/90, assistant fallback 20/25 real and 5/5 adversarial,
weighted cost 0.56 versus 0.44, the synthetic-reference rejection, and the e54317
noop wording observation. Directory inventories revealed prior output filenames,
and the coordinator said a separate known-regression check had completed; its
inputs, decisions and artifacts were not inspected. The protocol disclosed the
reproduction focus and gates, but no candidate wording. These limits preclude a
claim of total prior-context blindness.

The selection independently reproduces one `random.Random(4672027)` and six draws
from each sorted eligible month in April/May/June order. Eligible counts are 49,
38 and 45; all 55 prior source identifiers extracted from earlier case inputs
were excluded. All 18 draws remain, with unchanged title, body, opening labels,
author association, opening time and body-source values. New control IDs are
also distinct from every prior case ID. The source, rubric, scorer and corpus
hashes match the declared baseline.

All 30 expected schemas and reproduction dispositions agree. Eight cases require
both reproduction actions, twenty permit neither, and two installer cases make
both optional. Every expected target admits a zero-cost proposal with the unchanged
scorer and action limits; this is a schema feasibility check, not a model decision.
All 102 file hashes, 30 corpus hashes and row counts, and strict `created_at < as_of`
cutoffs were checked. Historical corpora reconstruct exactly from baseline bytes.
All 30 annotated retrieval lists independently recompute with the unchanged helper.
References exist in the eligible corpus, precede the opening, and are not already
reporter-linked. No fresh evidence directory or actual outputs existed at acceptance.

Five corrections were completed and recorded before execution:

| Cases | Correction and basis |
| --- | --- |
| e51619, e51678, e52098 | Removed optional upstream label/comment pairs. A dependency issue or tentative Node/Chromium attribution does not meet the original clear-upstream rule. |
| e51014 | Removed 48193: static transparency loss differs from the older hover/accent feedback failure. |
| e51760 | Removed 50647: the older showMessageBoxSync failure conflicts with this report's explicit statement that that API works while window.confirm fails. |

The separate optional upstream allowance in e51351 remains supported by matching
earlier corpus issue 50776, whose opening text explicitly describes that signature
as tracked in Chromium. This is available reporter evidence, not independent
verification of the upstream claim. Optional same-error-code links in e50678,
e51351 and e52098 remain under the original skill's same-error alternative; weaker
triggers are expressly excluded from strong coverage and imply no shared root cause.

Installer cases e51619/e51963 have genuine ambiguity: the terminal installation
operation itself is specified by command and environment, while the old Fiddle
wording can still justify requesting a sample. Optional targets were fixed before
execution and both cases were retained. e51950 supplies an explicit Fiddle gist
outside the empty dedicated field; e52086 supplies complete main.js/index.html and
restart steps without fences. Both forbid redundant reproduction requests. Logs,
configuration fragments and isolated calls do not become runnable merely through
formatting.

The twelve controls cover five distinct incomplete cases (formatted constructor,
call variants, configuration, missing external fixture, and stack output), three
supplied-reproduction cases (complete inline app, gist and runnable repository),
and four guards (feature, supported-version request, security, maintainer skip).
Ten require the directly named component. r02 additionally requires reference
76102 for the same app.setBadgeCount false result and missing dock badge; 76122
instead concerns a dock menu. r06 requires 76106 for the immediate false
powerSaveBlocker.isStarted result; 76126 instead concerns powerMonitor resume.
Both matches and distractors were read in full and predate the target. These
positive actions prevent success through blanket abstention.

All control corpora explicitly replace the baseline, including empty files.
Invented rows transparently disclose their fixture provenance; `synthetic=false`
uses the existing renderer's distinction from reserved adversarial rows and is
not a claim of historical authenticity. Gist/repository URLs are fictional offline
fixtures and were not fetched. Inline sufficiency means the source can be attempted
with Electron; the alleged runtime malfunction was not independently reproduced.

No blocking annotation finding remains. Freeze these exact hashes before executing
fresh decisions and do not revise targets in response to outcomes. This acceptance
says nothing about either policy's performance, population accuracy, hosted controls
or deployment readiness.
