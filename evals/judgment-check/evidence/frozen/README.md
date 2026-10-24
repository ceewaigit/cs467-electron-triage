# Linking and component judgment: offline comparison

This experiment tests whether a separate candidate can correct the two remaining live
judgment failures without an observed regression on fresh cases. The active runtime stays
unchanged until the predeclared adoption gates and independent review pass. No paid provider
evaluation, GitHub workflow dispatch or external triage write is part of this experiment.

The baseline is commit `90724fea4152861499063b4f163d84c28348b0d3`. The candidate reuses sections
2 and 4 from the earlier conservative-linking candidate and keeps the currently adopted
reproduction instructions. Component choices must follow the feature whose behavior fails;
an API used only for startup, setup, diagnostics or a workaround does not justify a second
label. Similarity requires the same failure with a distinguishing supporting detail. A generic
error or shared component alone is insufficient. Clearly supported labels and links remain useful.

The previous conservative experiment remains rejected under its original criteria. This is
a new comparison against the current policy, with new cases and its own decision rule. No
script, component hint, template, permission or workflow setting changes in the candidate.
The two known cases informed this experiment and are not independent evidence of generalization.

## Comparison fixed before execution

The [protocol](protocol.json) records the exact policy hashes, source and adoption conditions.
An independent author selects 12 unused Q2 opening inputs, four per month with seed 4672028,
excluding all prior evaluation inputs. All sampled cases are retained. Twelve separate
constructed cases cover positive and negative links/components, reproduction decisions,
no-action behavior and a security/injection case. Expectations are independently reviewed
and frozen before any proposed decisions are generated.

Both policies handle every fresh case twice: 96 first decisions, or 48 paired comparisons.
Each fresh assistant session sees one anonymous policy and six cases. Paired arms use the
same case order within a repeat. Expected outcomes, old outputs and Git history are excluded
from the displayed runner context. These controls minimize context exposure; they do not
enforce complete filesystem isolation. Cases within a session and repeated trials are correlated.

The known cases e52255 and e53734 are checked separately, twice per policy, with their original
unchanged inputs and expectations. Those eight decisions are excluded from fresh-cohort metrics.
The candidate must pass both known cases in both repeats. All earlier live and free outcomes
remain in place even if a new proposed action differs.

## Adoption rule

For every paired fresh and known trial, the candidate must have no higher weighted error cost,
no lost case pass, no new scorer failure category, and no increase in required-action omissions
or unsupported references. It must preserve positive link/component controls and have no new
safety, invalid-output or procedure failure. Every first decision must be saved with its context
and helper transcript before scoring.

At least one paired cost improvement is required in the fresh or known checks. A gain only on
known cases is reported as such. The blind checker separately reviews changed optional actions
for harm, because an equal rubric score does not establish equal usefulness. Adoption, commit
and push require every gate to pass. A failed gate leaves the active runtime unchanged; no
adaptive rewrite, extra repeat or changed expectation is used to seek a passing result.

The result can support “no observed regression in these trials.” It cannot establish that no
future case could get worse, configured Claude would behave identically, or an A+ is assured.
Current hosted safeguards and the separate 90-run plan are not retested by this comparison.

## Evidence and scripts

The harness freezes the input policies, expectations, source and protocol before execution.
It uses the existing recorder and unchanged frozen scorer. Preparation, collection and scoring
are local operations, with exclusive creation of evidence files. Existing Codex assistant access
supplies the dry runs; its exact backend identifier and metered usage are unavailable here.

| Path | Purpose |
|---|---|
| `policies/` | Exact current and candidate skill copies; neither is installed merely by saving it |
| `selection.json`, `dataset.json`, `cases/` | Fresh sampling, predeclared expectations and annotation provenance |
| `protocol.json` | Source, policy hashes, repeats, gates and interpretation limits |
| `prior-evidence-hashes.json` | Raw hashes of all 5,502 tracked files before any adoption |
| `experiment.py` | Prepare input-only contexts, collect immutable first decisions and score paired fresh outcomes |
| `known_cases.py`, `known-cases/` | Separate checks of the two known failures, excluded from fresh results |
| `evidence/` | Frozen execution sources, manifests, transcripts, scores and independent review |
| `requirements-review/` | Separate blind grader's requirement-by-requirement assessment of the committed submission |

Constructed corpus fixtures are test-only and stay separate from production data. Historical
cases use only corpus rows older than their opening time. Annotation and reviewer context
exposure must be disclosed in their provenance records; “blind checker” refers to independence
from the coordinator's proposed outcomes, not a claim of zero prior project context.

The evaluation scripts do not invoke a model or GitHub themselves. See their command help and
the saved execution manifest for reconstruction into a new disposable directory. Preserve
the first proposals, score reports and rejected decisions; rescoring is not a new trial.
