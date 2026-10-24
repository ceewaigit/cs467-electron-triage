# Independent review of both completed live failures

Both attempts failed before a valid model decision with the same provider HTTP 400
`invalid_request_error`: the key was not scoped to a workspace and the request required
`anthropic-workspace-id`. The refreshed secret did not resolve that condition.
This finding applies to **both the triage agent and the threat detector**.

| Attempt | Sandbox issue | Completed run | Valid triage decisions |
|---|---|---|---|
| `failure-recheck-live` | 217 | 40066776440 | 0 |
| `failure-recheck-live-2` | 218 | 40067336688 | 0 |

The read-only verification source is `live-review-source.py`; its preserved output is
`live-review.json`. All **167 checks passed**. The checker made no GitHub/provider request,
dispatched nothing, read no credential value and changed no runtime configuration.
It preserves hashes of the reviewed artifact bytes and identifies the local framework
source used for its additional inspection. Those hashes preserve local evidence; they are
not independent authentication of GitHub's downloaded archive signatures.

## Source, decisions and writes

Both completed run records identify `7debabe981d26af3ff36cc4606f45bc6efb1daf3`.
The pre-execution seals, fifteen runtime hashes, replay/scorer hashes and all selected
input/expected hashes match. They also match the offline experiment's source manifest.
Saved runtime metadata identifies `claude-sonnet-5-5`, Claude Code **2.1.300** and
AWF **0.28.70**, with digest-pinned images. Each dispatch mapping contains only e52255;
the other four cases were not dispatched in either namespace.

Each agent transcript contains two distinct CLI session results, both API errors.
The agent output contains only the framework's `report_incomplete` signal; it is not a
model's no-action decision. The safe-output item ledger is empty, the MCP transcript has
no `tools/call`, and `triage_comment` is skipped. Native failure records report no added
labels, comment or other writes and are correctly excluded from scoring.

Together these records support **no observed triage issue writes**. The experiment did
create the two sandbox issues and their opening labels as setup; “no writes” must not be
read as denying that setup. I did not query GitHub again. The replay collector's saved
write summaries are derived from the issue timeline and current state; the raw timelines
were not separately retained for this reviewer to recompute. Runtime artifacts corroborate
the absence of triage outputs.

The workflow logs confirm the corpus was prepared with 809 earlier rows before the agent
started. Skill inventory establishes staging, not actual model use: inference failed before
the agent could execute the triage procedure. These attempts cannot establish the quality
of current decisions or successful adversarial resistance, budgets under load or posting.

## Inference usage and detector status

For **each** attempt, upstream-error artifacts contain six agent rejections: two model-list
GETs and four message POSTs. The detector has four: two GETs and two message POSTs.
Every one is HTTP 400 with the workspace-scoping message. Two agent CLI sessions therefore
do not mean only two HTTP requests. None of the remaining targeted cases was dispatched.

Both agent sessions record zero input/output/cache tokens and `total_cost_usd: 0`.
Both agent and detector proxy usage ledgers are present and empty. Detector usage summaries
explicitly record zero input/output tokens and zero AI credits. These independent signals
support **zero recorded inference usage**, not merely an assumption from missing files.
No provider invoice, account balance or GitHub Actions infrastructure bill was inspected.
The live run's actual credit caps were 100 for the agent and 400 for the detector; those
caps are not spending observed in these failed runs.

The detector job's GitHub conclusion is `success`, because execution uses continue-on-error.
Its own logs report an engine error and the conclusion job warns that **no security verdict**
was produced. Successful job status here does not validate a detection result. The overall
workflow concludes `failure` in both attempts. Empty outputs and the skipped comment job
prevent any inference that the detector approved a triage action.

## What can and cannot be verified locally about a fix

The saved agent and detector configurations both bind `ANTHROPIC_API_KEY` to the repository
secret, hold that credential in the API-proxy path and exclude it from the agent environment.
Neither saved container configuration supplies `ANTHROPIC_CUSTOM_HEADERS` or a workspace-ID
setting. The provider itself states two possible remedies: a key scoped to the intended
workspace, or the correct workspace header. Secret-update metadata proves an update time;
it does not reveal or establish the replacement key's workspace permissions.

The local compiler checkout is tag `v0.93.2`, commit
`764fdc608e552558e4e15ffebec8e2953feb18d7`. I inspected its schema and harness, and ran a
synthetic, credential-free probe with global fetch and standard HTTP(S) request/get calls
blocked. It confirms
that `buildClaudeChildEnv` preserves an `ANTHROPIC_CUSTOM_HEADERS` variable already present
in its input environment. This is narrowly an environment-propagation result.

It does **not** prove the pinned Claude CLI parses/emits that header, the pinned proxy
preserves it upstream, or the compiler supplies it to both phases. The exact Claude **2.1.300**
binary is absent from the inspected local versions, and no AWF binary is available on PATH.
I did not install/download either or substitute a newer version for a compatibility claim.
The local compiler tag also does not independently prove every published setup-action
bundle is byte-identical to that checkout.

There is an additional route to account for: `awf_reflect.cjs` performs model-list requests
with a bare `fetch(requestUrl, { signal })`, separate from Claude's message calls. It relies
on proxy-side credential injection. Preserving a custom-header variable for Claude alone
does not demonstrate workspace scoping for those model-list requests.

The bundled schema allows Anthropic target fields `host`, `basePath` and `authHeader`, and
rejects additional target properties. `authHeader` changes the API-key header's name; it
is not a second workspace header. `extraHeaders` appears for Copilot targets, not Anthropic.
The schema's `anthropicWorkspaceId` belongs to GitHub-OIDC workload-identity authentication;
its presence does not establish support for adding a workspace header to the existing plain
API-key route. None of these fields is a verified drop-in fix for this configuration.

Consequently **no complete credential/header fix is verified locally**. A workspace-scoped
key would address the provider's stated requirement without changing these workflow files,
but actual scope/access cannot be established from metadata or a key's appearance. A header
solution needs an offline test of the exact pinned compiler/Claude/proxy route for agent and
detector, including model-list and message requests, before another paid workflow is justified.
Synthetic values can test transport; only the correct workspace/account information can
establish which real ID and credential belong together. The workspace ID remains missing.
Do not guess an ID, substitute an organization ID, disable the proxy/detector, or treat
another refreshed unscoped key as a verified repair.

## Coordinator documentation check

After completing the independent checks, I read the three new experiment READMEs,
both result summaries and the changes to root README, DESIGN, AUDIT and CODEBASE.
Their substantive score, failure, usage, unchanged-source and evidence-limit claims agree
with this review. DESIGN remains 150 lines. The only small path inaccuracy observed was
CODEBASE's `independent-*-source.py` wildcard including “live-failure evidence” in its
description: this live verifier is named `live-review-source.py`, outside that wildcard.
I reported that to the coordinator without editing those documents or the earlier blind review.
