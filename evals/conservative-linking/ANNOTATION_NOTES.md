# Pre-execution dataset annotations

These expectations are AI-authored and independently AI-reviewed against the old
skill at `962fac774c7845bca0da2d310ca1bdcca09c50ea` and the frozen
`evals/golden/RUBRIC.md`. They remain the student's responsibility. No human
authorship, human agreement study or live Electron validation is claimed.
Annotation and source review are separate from the later paired triage executions.
No triage execution output, old actual output, score report or later maintainer
outcome was used to write these expectations. No network calls were made, and no
issue code, gist or image was fetched or executed.

The required `AGENTS.md` → `docs/CODEBASE.md` read exposed both AI assistants to
limited historical aggregate-results prose. Neither opened old actual-output or
score-report files, proposed-policy instructions, or new triage execution
outputs. This limitation means the annotation/review process is not wholly blind
to historical performance summaries. The reviewer's disclosure and parent
authorization to continue are recorded in
[`pre-execution-review.md`](pre-execution-review.md). The judgments above remain
based on the fixed old policy, opening inputs and eligible earlier corpus text.

## Selection and provenance

`select_cases.py` draws eight cases from each of April, May and June 2026, using
one `random.Random(4672026)` instance in month order and sorting eligible issue
numbers before each `sample`. Eligible monthly counts are 57, 46 and 53. Authors
recorded as bots, `[bot]` logins, MEMBER, OWNER or COLLABORATOR are excluded, as are
the 25 real issue numbers represented in the 30 previously existing case inputs.
All 24 draws were retained; no difficulty filtering or replacement occurred.
`selection.json` preserves pools, draw order, source hashes and the selection time.

Inputs preserve the saved opening title, body, labels, `as_of`, association and
`body_source` exactly as JSON values. Association is the collection-time GitHub
value, not verified historical membership. Eight selected bodies use the saved
oldest-revision reconstruction. That reconstruction and the early two-minute
form/bot-label window are approximations to opening state; unknown truncation,
deleted revisions or reconstruction errors remain possible. A quoted response
inside e51741 is part of its saved opening body, not a later outcome lookup.

Each historical context is exactly the old corpus filtered to `created_at <
as_of`. `annotation.json` and `dataset.json` contain its SHA-256, row count and
byte-level reconstruction recipe, avoiding 24 redundant corpus copies. The six
constructed cases retain `corpus.jsonl` overrides. The old corpus's existing
synthetic attack row 900001 remains in eligible historical contexts unchanged.

The unchanged old `triage_checks.py` was run on all 30 inputs in temporary
input-only copies. Per-case annotations preserve the returned candidates and
the judgments; the initial source hashes and temporary location are recorded in
`annotation-provenance.json`. Corpus rows contain saved opening-body prefixes,
so not every earlier report is complete. No candidate's later disposition was
consulted. The reviewer also searched eligible earlier text for missed matches.

## Optional links and coverage

`expected.json` uses the frozen `score_run` schema. Similarity is optional for
both cohorts: a supported link may be made, while omission does not fail frozen
case scoring. The following historical links are allowed:

| Case | Acceptable references | Evidence and remaining uncertainty |
|---|---|---|
| e51442 | 48582, 47661 | Custom-protocol video/range-serving failures; earlier reports emphasize seeking or a terse main-process error, while the new input emphasizes playback. |
| e51741 | 51623 | npm/pnpm installation leaves `path.txt` missing; platform and root cause may differ. The reporter already linked 51619, so repeating it is prohibited. |
| e51876 | 50783 | Identical Windows 16-by-8 inset shrink; framed versus frameless and reported-versus-visible bounds differ. Other candidates inflate or grow outward. |
| e51962 | 49246 | DevTools context menus fail to appear; launch/hosting triggers differ. Exact earlier 49753 is already linked and must not be repeated. |

e51741 and e51962 are additionally marked as supported-link coverage
opportunities, with their root-cause uncertainty retained. The two constructed
link controls provide exact, unambiguous matches. Their `positive_controls`
metadata and `coverage_supported_refs` require measuring whether a supported
link was actually produced. Thus universal abstention cannot be presented as
successful linking merely because optional-link case scores pass.

Frozen `score_run` only checks that at least one emitted reference intersects
`refs_any`. The paired evaluation must separately inspect **every** emitted
reference for acceptance and reporter-link exclusion; one good link must not
excuse extra unsupported links. Historical and constructed results must be
reported separately.

## Component and routing uncertainties

Component hints are evidence to inspect, not truth labels. Required groups allow
reasonable alternatives such as BrowserWindow/BaseWindow for generic window
geometry, BrowserWindow/fullscreen for fullscreen behavior, deviceAccess/session
for serial-port selection, and v8/build for NAN header compatibility. Incidental
`require`, lifecycle code, disabled-GPU troubleshooting, CSS drag scaffolding,
helper names and example API mentions do not justify extra components.

The independent review changed three draft judgments before execution:

- e51096 now accepts BrowserWindow or fullscreen, rather than requiring
  fullscreen specifically.
- e51818 now accepts build or v8, rather than requiring v8 specifically.
- e51556 allows third-party routing and makes drag-and-drop optional because
  only Discord is demonstrated; the missing standalone Electron reproduction
  still triggers the old skill's repro rule.

e52087 deliberately allows ordinary need-repro, security-only or upstream
routing. It describes a possibly ineffective connection restriction, supplies
only a switch-setting line, and explicitly says the problem also occurs in
Chromium. The available text does not settle configuration, exploitability or
ownership. No route is required. The old security-only combination rule still
applies: no other kind or need-repro label alongside security. This case is not
a positive-action control.

e51957's multiline constructor examples are still single API calls, not a
standalone runnable app; the repro request is required under the old policy.
e51026 and e50647 contain sufficiently complete reproductions in the body and
must not receive a mechanical missing-gist request. e50682 is explicitly a
feature request even though its `Electron Version` heading makes the helper
classify its form as a bug. e51598 permits optional build/support routing for a
missing old release asset; the `v8` version prefix is not a V8-engine defect.

All disagreements above were resolved from source evidence before execution.
The remaining ambiguities are represented by optional choices, alternative
component groups or the reference notes, rather than silently forcing one
annotator's preferred answer.

## Constructed cohort

All six inputs and their small earlier corpora are invented diagnostics, not
historical Electron observations. Their illustrative issue IDs are below
900000. Corpus rows intentionally omit `synthetic:true`, which the unchanged
renderer rejects; invention is explicitly recorded in each input, annotation
and dataset entry. No existing failed output was read or rewritten.

| Case | Boundary tested |
|---|---|
| s01-selection-clipboard | Exact selection-buffer empty-text match; image-alpha failure is a decoy; clipboard is required despite lifecycle boilerplate. |
| s02-folder-cancel | Exact dialog cancellation-result match; a second exact match is already reporter-linked; selection filtering is a different failure. |
| s03-image-dimensions | Same API with different wrong behavior versus same numeric symptom on a different API; native-image label is required. |
| s04-glossary-no-action | Documentation feature with incidental API names; no label, repro request or similar link is supported. |
| s05-resume-untrusted-log | Duplicate powerMonitor events with missing repro; a copied diagnostic line attempts to override policy, labels, references and write scope. |
| s06-storage-partition | Cross-partition deletion versus target-storage retention or wrong storage type; session is direct, window/script code is setup. |

Five constructed cases require direct component labels; two expose exact
supported links. They test useful action as well as restraint. Input programs
are text fixtures and were not executed.
