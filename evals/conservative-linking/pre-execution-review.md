# Pre-execution annotation review

Status: accepted for pre-execution freeze on 2026-10-24. All 30 expectations and
inputs were reviewed, source checks passed, and substantive corrections were resolved.
Acceptance applies to the hashes below and retains the disclosed uncertainty and
limited historical-summary exposure. It does not assess any execution outcome.

## Review boundary and provenance

The reviewer used the skill and its deterministic helpers from commit
`962fac774c7845bca0da2d310ca1bdcca09c50ea`, the frozen `evals/golden/RUBRIC.md`,
the saved opening-state source rows, the new case inputs and expectations, and
strictly earlier corpus candidates. No candidate policy, current working skill,
new experiment protocol thresholds, new model decision, provider API or network
request was inspected or executed. The reviewer did not inspect prior actual-output
files or score reports.

This review was performed by a separate Codex assistant context. It is an
AI-assisted review, not independent human annotation or maintainer validation.
The exact inherited model backend identifier was not exposed to the reviewer.

There was a limited blinding deviation: `AGENTS.md` directs readers to
`docs/CODEBASE.md`, which includes an earlier experiment's aggregate results and
two old case-level observations. The reviewer read that document before noticing
the historical-result content, immediately disclosed it to the parent, and was
instructed to proceed while recording the limitation. This is therefore a
pre-execution review unaware of the proposed policy and all new execution
results, not a claim of perfect historical-result blinding. No further historical
result material was read.

The review assesses reasonable first-pass decisions from the supplied evidence.
It does not assert that the reporter's diagnosis is correct, inspect linked live
gists or screenshots, or use later maintainer outcomes. The opening-state source
is accepted as the frozen reconstruction; raw later issue histories were not
opened to independently reconstruct it.

## Independently executed verification

- Recomputed the saved source SHA-256 and the complete eligibility sets. There
  were 57 eligible April, 46 May and 53 June inputs. A single
  `random.Random(4672026)` sampled eight sorted issue numbers in each month in
  April–May–June order and exactly reproduced all 24 selections and their order.
- Independently scanned prior evaluation `input.json` files, excluding result,
  actual-output, log and new-dataset paths. The scan reproduced the 30 inspected
  prior inputs and 25 excluded real issue numbers. None of the selected inputs
  overlaps them. All selected cases were retained; there was no redraw.
- Compared title, body, author association, opening labels, body-source metadata,
  opening timestamp and source URL for every selected historical input against
  `evals/data/electron_issues.jsonl`. All 24 matched exactly. Eight use the saved
  oldest content revision and sixteen are marked never edited.
- Verified every annotation copy of the old skill, three helper scripts,
  component hints and allowlist by SHA-256 against the fixed old commit. All 24
  copies matched. Their deterministic reports preserve the input title, body and
  opening time; they are evidence extraction, not model proposals.
- Verified each of the 24 historical annotation corpora is exactly the entire
  old-commit corpus filtered to `created_at < input.as_of`, with original row
  order retained. No input self-reference or same-time/later corpus row survives.
- Compared the old corpus against the opening-state source: all 994 real rows
  have identical title/timestamp and bodies that are exact prefixes of the saved
  opening bodies. The remaining row is the existing synthetic row `900001`,
  dated `2026-06-02T08:00:00Z`; it is not misrepresented as historical evidence.
  The corpus's body truncation remains a limitation.
- Read all 24 historical inputs and their five retrieved earlier candidates.
  For borderline links, read the full saved earlier corpus bodies. Targeted
  corpus-title searches beyond the five retrieved candidates were followed by
  reloading each considered candidate from the relevant input's own earlier
  corpus.

## Historical case review notes

These observations were made before viewing expected outcomes or any new model
decisions. They distinguish symptoms from nearby keywords and record the
uncertainties that the expectations should accommodate.

| Case | Opening-evidence judgment |
| --- | --- |
| e51237 | New dark borders on left/right/bottom of Windows window; window component and reproduction request are justified. Image markup alone does not establish similarity. |
| e51026 | Internal deprecation wrapper drops return value; supplied code demonstrates the operation. Incidental `require` is not enough for node-integration. |
| e50682 | Explicit native-tabs API feature request despite helper classification as bug; no reproduction request. BrowserWindow/fullscreen are plausible component choices. |
| e51064 | NativeWindow mouse-hook lifecycle report; existing supported-version request suppresses another reproduction request. Unrelated Git hook candidates do not match. |
| e51333 | Documentation enhancement about platform performance; the `app` API is an example, and issue 49727 is already reporter-linked. |
| e50647 | Complete main/HTML/renderer code demonstrates focus loss after synchronous message box; dialog/window choices are plausible and no new repro is needed. |
| e51188 | Web Serial device path becomes basename and fails to open; device-access component and repro request fit. The report says the same code works in Chrome. |
| e51096 | Fullscreen WSLg cursor offset with a gist; fullscreen/window choices are plausible. GPU performance candidates have different symptoms. |
| e51442 | Custom protocol video playback fails with Buffer/stream responses; protocol is primary, with media/net overlap. Reporter already links 38749. Earlier video/range examples support optional, uncertain links. |
| e51556 | Discord-owned orphan drag window, no standalone Electron reproduction. Logs and one-line cleanup are not a runnable repro. Third-party responsibility remains uncertain despite detailed platform diagnosis. |
| e51789 | Top pixel of window content clipped, with gist. Window component fits. Different edge artifacts and platforms do not alone establish same symptom. |
| e51598 | Missing old Electron release archive, with an existing version request; no V8-engine label merely because URL contains `v8.5.5`. Support interpretation is possible but not proven. |
| e51765 | Helper lookup fatal error after renaming packaged helpers; concrete shell reproduction and gist. Generic SIGTRAP without the helper error is not the same crash signature. |
| e51588 | Broken code-signing documentation link, existing version request. No clear allowed component; code-signing keyword overlap is not a same-problem link. |
| e51521 | Mouse forwarding leaves body hover stuck after pointer exit; BrowserWindow/input behavior, gist present. Mouse-position requests and Wayland changes differ. |
| e51741 | npm/pnpm installation leaves `path.txt` absent; no runnable testcase, prior 51619 already linked. Earlier 51623 supports an optional same-installation-symptom link despite another OS. |
| e52055 | Arrow keys fail to move between native menu submenus; menu component and gist. Alt-menu visibility and stuck keys differ. |
| e51876 | Frameless non-resizable window shrinks by 16×8; BrowserWindow and gist. Earlier 50783 has the same inset shrink but different frame/measurement behavior, so a link is optional. |
| e51818 | NAN compilation fails on changed V8 External signatures; runnable addon source is supplied. V8/build/native-module component choices are plausible; upstream ownership is not conclusively established. |
| e52087 | Connection restriction permits connections, one flag-setting line and no testcase. Ordinary bug/repro, possible security-only and upstream interpretations are plausible alternatives. |
| e51940 | EventTarget listener dispatch drops only during inspector pauses in a Node-enabled renderer; supplied repository. DevTools/node integration fit. Node control does not reproduce; mere Blink involvement does not prove upstream responsibility. |
| e51957 | Fullscreen creation fails with `frame:false,resizable:false`; constructor snippets are one API call, not a complete runnable app. Fullscreen/window choices and a repro request are reasonable. |
| e52208 | titleBarOverlay covers renderer border only at particular scales; WCO/window choices and complete runnable testcase. Generic high-DPI black border is insufficient evidence of same symptom. |
| e51962 | Detached custom DevTools popup menus disappear; original 49753 already linked. DevTools/menu/webcontents overlap; earlier 49246 can be an optional same-menu-symptom link with trigger/platform uncertainty. |

## Corrections and uncertainties sent to the author

Before freeze, the reviewer recommended retaining optional links rather than
automatically penalizing all unannotated links for `e51442 → 48582 / 47661`,
`e51741 → 51623`, `e51876 → 50783` and `e51962 → 49246`. None of these links is
required: the saved descriptions leave uncertainty about matching triggers or
the exact failed operation. Opposite-direction window-bound inflation and
unrelated generic error strings were not treated as confirmed matches.

For `e52087`, the reviewer recommended recording ordinary bug/repro,
security-only and upstream alternatives instead of forcing one uncertain route.
The security route must suppress every other comment kind and the repro label,
as the old skill requires. The frozen expected schema allows individual kinds
and does not express all cross-action alternative constraints; that limitation
must not be mistaken for approval to combine contradictory routes.

The reviewer also flagged helper/form and code-block pitfalls: the explicit
feature request `e50682` does not need a repro, `e51556` logs plus one-line HWND
cleanup are not runnable Electron code, and the `e51957` multiline constructor
options remain a single call rather than a complete runnable application.

## Final expectation/control review and accepted hashes

The reviewer read every authored expected file and every constructed input,
corpus and annotation. The six invented controls are a separate diagnostic
cohort, not historical Electron observations:

| Control | Verified boundary |
| --- | --- |
| s01-selection-clipboard | `810101` exactly matches X11 selection write/read returning empty text; `810102` loses image alpha. Clipboard label is supported and the new link remains optional. |
| s02-folder-cancel | `810201` exactly matches confirmed-folder selection returning canceled; `810202` is an exact match already linked by the reporter and must be excluded; `810203` has different picker filtering and correct cancellation. |
| s03-image-dimensions | Actual resize dimensions are wrong while candidate `810301` explicitly has correct dimensions and wrong alpha; `810302` concerns window size. Native-image is the direct component. |
| s04-glossary-no-action | Prose-only documentation feature has no applicable component and no repro requirement. Named APIs are examples, not affected APIs. |
| s05-resume-untrusted-log | Two resume events differ from missing resume events and a disappearing tray icon. Embedded tool/label/closure demands are untrusted; powerMonitor and a reproduction request fit the real symptom. |
| s06-storage-partition | Clearing another partition differs from failing to clear the target or clearing another storage type inside the same target. Session is direct; window/webContents code sets up and observes storage. |

Two controls provide exact positive-link opportunities, and four test nonlink
boundaries, one of which contains an injection. Five supply direct-component
positive opportunities; one explicitly expects no action. The constructed cases
are clear and useful diagnostic checks, but their tiny curated corpora and
explicit symptom contrasts do not represent general retrieval difficulty. The
positive links remain optional under the frozen outcome semantics; link coverage
must be described separately rather than treating every abstention as a full
demonstration of useful linking.

The structural audit of all 30 cases passed: corpus timestamps are strictly
earlier than inputs, all expected references exist in their per-case corpora,
accepted labels are allowlisted and do not overlap forbidden labels, and required
comment kinds do not overlap optional kinds. All 24 persisted historical corpora
equal the verified old-base cutoff corpora. The dataset's listed file hashes
matched the files at inspection. Individual acceptable labels/kinds are
alternatives, not permission to violate the old skill's two-component maximum or
security-only combination rule. The frozen scorer's `refs_any` intersection check
does not validate every extra reference; a permitted reference must not hide an
unrelated or reporter-linked extra reference.

Before finalization the reviewer requested that `e51096` accept either
fullscreen or BrowserWindow, and `e51818` either V8 or build, because each pair
identifies the directly reported surface without requiring an unproven root
cause. The reviewer also requested that `e51556` allow a third-party redirect
and make its drag-and-drop label optional: only Discord is demonstrated, so the
draft rationale's acknowledged routing uncertainty should not become a forced
component decision. The old skill's bug/no-runnable-repro requirement still
supports the repro request. The author accepted all three corrections, and the
reviewer re-read their final expected files to confirm the resolutions. The
author also accepted the expanded optional `47661` reference for `e51442`,
upstream as an optional route for `e52087`, and optional rather than mandatory
similarity for both constructed positive cases. There is no unresolved
substantive annotation disagreement; the stated uncertainty remains deliberately
allowed rather than settled by later facts.

Historical corpus copies were verified before deduplication. Their exact bytes
are reproducible from the old-commit corpus: retain the original lines whose
parsed `created_at` is strictly less than `input.as_of`, preserve order, join
with LF and retain a final LF. The reviewer independently verified that this
recipe reproduces the SHA-256 of every previously persisted subset, not merely
equivalent parsed JSON. The six constructed corpus overrides remain explicit
files. The accepted hashes below identify these contexts regardless of whether
a redundant historical corpus file is stored beside its input.

## Accepted artifact hashes

Each SHA-256 was calculated independently after the final substantive corrections.
Historical context hashes are for the reconstructed bytes; constructed context hashes
are for retained `corpus.jsonl` files. Input and expected files live at
`cases/<id>/input.json` and `cases/<id>/expected.json`.

| Case | Corpus rows | Input SHA-256 | Expected SHA-256 | Corpus SHA-256 |
| --- | ---: | --- | --- | --- |
| e51237 | 669 | `be641f82c66d8799ecb0373126aefea603448ec84dea93bf09ddc9db20dacf19` | `f38d0e7cfdbd7086489f187fcb9c2f1e479d9c248b4ab4348a505227e1ea0f98` | `2261da903c38d3fd620481c853d46be3a7d2e1aac0b896f951c73d304fa44477` |
| e51026 | 639 | `dd465d6acfc5c8ef0cc1709048f929556e29cecd8cbed15bd195f01d0f698710` | `e702221c96ca6f946659300447084f665360018a7c39e4b523a9917d2094c33e` | `41b775eef49097ca8a4252c94ea5a2f9366fd227ed08b8254547f0ecdc2d58e4` |
| e50682 | 614 | `f6c69af74c4c2de0fc69395fc9e6288f6da95a0df6452865f1c4405575baf9fa` | `822f5ea464a541910ff63ef70f27450ba2cf3f0ffbe8a9374eb5df8a1bf0a1bd` | `2130335833ea44816e844b8afa48e7e501e5494ed537fd29131a3337cece0d7f` |
| e51064 | 647 | `0cc1a133457d759a696ca0ddad28c7bfa52d8f9e0d55ad18b97f96df09f4fa55` | `5479bf2ad3fb6da145c5ca01b276c3f88730b735ae527ca2c0fc52d8bf1baac2` | `93cc37cd01dc77d1ea8172e028ca9d99da04c0307a3702e4c961610d080676b3` |
| e51333 | 677 | `ed4866607fb13ab05abb179f01155a7e92aa3b824d46d8cea9fab7dcf4b8458f` | `1d93ec1575878e8e887eb198728fc1db2c69c1e2dbe73a1e51bfc8491575e7da` | `6a342dff3b8e4a421070d57e4d728cb0e6f30de6f35f44440e8481d093115dc3` |
| e50647 | 611 | `86837b692becfca0026084c3850c6251fefbc1b9b87ab2fc7e655fe58fd49068` | `6eb2447a386358453cf183ba244a704ec813c230009c1f367f7436f250095d09` | `c515554977aca221971ddc23ffba65bf78b8c51e9293f314086db52ae1b3f7ca` |
| e51188 | 662 | `b47388e70a5f314f7a1444a056704e172d7af7220dd348d7efef5820a66017cf` | `00ae788d5766c4365155e33a85c2b659ef02bd91930d50608f2eb533d6d4f371` | `175c11c2f3463913d8fda143b488a8050abf286969e1c9043d7b0ec9324b8f59` |
| e51096 | 650 | `b58f20b81b098dee24740163343fda6d1d8f67eadd426e233010a436c3094087` | `15157e809eba18f7eb18b5f9a8de4ca3f9a49a6ef451a0f44d872145f3f4a567` | `19d8b308edcea55816b10cf04564522fac37b72e234e86585c6b0c3aa3bad10b` |
| e51442 | 691 | `b7a2fbf08c47f1ce9b293b599ba529e07a2a383281e361f4ed654de5f7b2a774` | `114b8c9e48ab17c8ede115e4debc692818e1c74f5a3dbe1923fb8b0d670800c0` | `e1465fabf60bb739d3119717487077f4a0e3d1e2f7237e7a8b7fedd65cb9e685` |
| e51556 | 704 | `65fa5e8e253965bfe310880d96b890f169649e768fb17338a6b4c474fbadba65` | `0dee3c52e617a0850a9ab685f9db2d08787c1fc49a7ef038199cd8847fd5f89d` | `403f805858c355e8d8e0e951c5c86cb84ae1c98e40682eb4a10b990bf759105a` |
| e51789 | 742 | `756d3f1356bc651660c02e997cd51f10fb4c31d4613349c941d2b5874941c7b0` | `39943e1cf600fa990489627e9d6bb60519f5b6e60a4e1033f0e5f3016d64d50e` | `38ff867e2727f6ceab38d24c2fe57f6dc26e9514a61dd38ed323b7289d50d504` |
| e51598 | 713 | `b4e54989231f8713ca3ce87c862cc596355a244d1237b2ca845c7ebd0e8b61de` | `b99537cb7b220bec3a38b285e25535f201a0fe9ff5b2c047f3f9f0338b68ec15` | `9c55ecc29351910fb01b39cf06ffecafe844b1be86dc90ff16ae10e1964b6feb` |
| e51765 | 736 | `05df32fde181b2c0eb84466a4b723d543bd064318ecc29d17429f4e1b04863e8` | `c8e9aa387992ed4eb20434356e8b92710bd678eca155a76222474db0f6add66a` | `57fe197eccb750c48698706aa0375a8c366b5b9891efb0adeb31b82647bac742` |
| e51588 | 712 | `e6ad9a549ae34d61e68ed2ecf57918b1e2ab4d60d3476a2569c37cdd7d824e1c` | `7325c13d859ecad5e0a30db135f2ff6c05e169048b457821a5af830c17e85377` | `19ac6b18086ae316eefba1d6b22bc5863ed6c29c53fac7b37024fd7c0a815218` |
| e51521 | 700 | `b41926f477a77b70725ca1c08dca5a3719bced8cd76c5b22c5cc6db6393904a6` | `c441182fbee8d12a6c7d206b607594c2063ef31e2fb042d2409536b41d422915` | `a8531c12c5a3fedd3855f2fe61f2ccc63257d86bada3f94273a969d00ab9f58d` |
| e51741 | 728 | `c8923bc6700717aba8c4e0371b615a1769d0dd82d5ff4afdb8bfa8084d58b026` | `d1f98c086736264521f4c137db1e7097694e8fe1fce31535f92e53b8e8f62848` | `f093819dc31f0d36c8753dcc88482579502676b69c45ef10cfb132a6346dbd7a` |
| e52055 | 786 | `39d561e43f0bb6c70894da5f1a277e61b301536a72712c5a45ea73180f9ca0c0` | `9813dbd696bea0d2c7ac36f27584954692f91ad73738ccabc870939a2166af85` | `dc44ed3c7ab796571052ecf05d0b7cce06adbb44d81b81fd4bb3b0b3e6d56e65` |
| e51876 | 753 | `f9ceedda9a60fb90b73a6c9ac8723f502e476984303e34c90de3569cd65f93c3` | `4cd5a19ff1c614ba241d70bf9af77347e2a82e2fae972be64fd9e46641373b00` | `77aa1cd7733d5f893ac2f6d13ef1f5ebc30e85fc48381635e0ec67f81a90ddab` |
| e51818 | 745 | `d0fb3b7a3c88862276e29c948ae0e023ccb9b8df9f6a4a1929123203f9115a1e` | `dfa71fdb61bbc5312e0a51da99c915a946b502e1458d1085c381e9c47d469f76` | `1b6ee4e83a561aa051c77b6f88b5091cb717bbef02dc66afe9db0276e6ea931c` |
| e52087 | 791 | `192098def9ee9ec9c2a14ec84505b4273f81652e40d265f74404fb3c23a242c3` | `25d588e794a5dbce35f2907220f2646385e1a69f41f8e44a8937908f3dd74ae9` | `98b24c3436ecf4dd2ca06a3c1c7dcc5662d57680982e7106560e0e460c9407c5` |
| e51940 | 762 | `f9103cef8735a47d33785f95bb55a307da3738e027dbd1eb9d119922677068cc` | `0b927738cecfd6f1ed993de7cb8e2b09851ff1ef9202a21c211d3f320b814859` | `68442d01bd2d9466bf7ad3e7d4126b572a6ad64ef133923f9d063c369aea8c9b` |
| e51957 | 767 | `b2c9d9edfd170808ca1dc4c8fe32da51ec99d6e471db69759cb021641d1de6fb` | `f64363692ce39e82cb24fc8f8ac0ab5a093d90a046505d64a58a921877e3c4b3` | `c4e2e5a1916d8ed4f5f53f2e88fca1e6fb2a985e636267d3e88850e29f21f6bc` |
| e52208 | 802 | `51fd9f4245128df57ca136ade59a85eba984772f69d67b205ba03ef5787d8772` | `f5e81e8d5f8c73489021667c9b1a47a59ceda153eb2122468b8ee56dfda3ade1` | `28f739d3ee43d921c920a7c85e9985362ff424802a0794f3283bc92def54cd48` |
| e51962 | 769 | `04bea511f02f7feb7c53f5135e4fabe0ab5f768b262fc1548c7682808ca26caa` | `ce9ab641ba1f9a369229042006d052a61ac29c38b8cf06b946309fb010069b5a` | `069e29744e130731985f7616684ba1d023a3f22b430f9d6d1676caf8d179f3ab` |
| s01-selection-clipboard | 2 | `b91f37a6a5fb48206868fc27114f2f2872a5a60ae5e3f48f3a332ac28126ef88` | `32cdebf42440e1b1e367072c0e440edd233f9ba63b1954fdfc0fe874deda18ae` | `a3899c174744afa5c0676fce8e19486d9135c3543f8276d388352349b5eb5203` |
| s02-folder-cancel | 3 | `1d74f6a1c2a1c41f59c2723f5fe4bf0692a939a015ca8b3cebc940f31a579731` | `b89f98b553981957adfe850efd75e5736dda62370769909d88cd3bf3d54c0de1` | `241e921b6eed972a01ef2482fb3f55782ff547ed8f2490002bbffa0fe04a4d8a` |
| s03-image-dimensions | 2 | `e4ca12f25edfbe766fd5cb5e052dc6e0302f61c0ffaedc114fbcea09aa95ee1f` | `143cfa65d07bb71b7b828f3f615aa1e28e37fb1d6558568c3c1cb9889082cf09` | `1719e8431ab6f115dd9f5cb48d79bd57b8ad8d2f34ae264c37d87d2c12221736` |
| s04-glossary-no-action | 2 | `cb3138ad29b64142f52134637c7929df6d38719cad56a6dfa5b23bb589acb295` | `c49949260f941da6dba6096a4717d61dcfbd6d49205357835faf69249e94ff70` | `1b9453101c7dee80864c4bc3fc8fa7122040b6b7f13ca43dd31b4dafff0066b9` |
| s05-resume-untrusted-log | 2 | `65d35e4feba8232137a6f2bb445a4f3f6142a988c3e93a045254e29b6ffd3b20` | `bfb8e21e57891c9e0e2fccf7d60c2aad800eae947220a1bc059f9f7b08243da0` | `b8c7a96d4c73e1f5d03a9154a27140e040f84f8d0e0756fd56855bd7503edc77` |
| s06-storage-partition | 2 | `90653ea1c36211cb6b943489b0ae3d5614e490b1461cd8735a061b9bd3a922c7` | `eab2a836eb94e99f43e22dc3d07f058903896cc92ba95c1735b37aa637f81fc0` | `3a3509a7f338caf5d4a01dc6f83087f56fedfdba982e4e18c3a26d6762d7da23` |

## Accepted source and manifest identities

Final sign-off UTC: 2026-10-24T02:46:28.096239+00:00.
No new triage execution outcome was available to or inspected by this reviewer.

| Artifact | SHA-256 |
| --- | --- |
| dataset.json | `5e7410e2a1418a05c572cf86d33a62e4317014c28d0eee49d9c6aa2f9b4d65eb` |
| selection.json | `b8b620cae6910b0c2d42c31de3bd937e01b2bdca2cb43cb453c074a4bc0e879f` |
| ANNOTATION_NOTES.md | `760d17a7bbb61186db224b20cfa1e751f97e7741a8a4033f9bf883feec08bb68` |
| annotation-provenance.json | `d8273c2f85be8199b0471397297e6a81ba6bbbbb29e732ac9ee6b7cf0da28dc8` |
| evals/golden/RUBRIC.md | `55718a26102b320f6ae6a32391707ab1a847215b202236556bdb9347d8e51738` |
| evals/data/electron_issues.jsonl | `3fa8dfedbf7b0234b83125151723b7f3289b46fc277089332aec84035573292f` |
| old commit: .claude/skills/issue-triage/SKILL.md | `3fca13eb148727075ef8252eea7c8cdd11b33f4bb452b2ec4769acc03ee1b572` |
| old commit: data/issue-corpus.jsonl | `17f98b105cfa82f53f9162fcdb274faab69460fd9e64049cc9978cd4b2255c5c` |
