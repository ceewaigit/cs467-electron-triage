# Drift review

`.github/workflows/drift-check.yml` reruns all 30 cases once on fresh sandbox issues, scores them
with the frozen scorer, compares them with a reference (`evals/tools/drift_report.py`) and opens a
`drift-review` issue for the owner if anything changed.

**It is off.** The weekly run (Mondays 03:00 UTC) needs the variable `DRIFT_WEEKLY=true`, and each
run costs about $8. Until then a silent provider change goes unseen unless someone dispatches a
check. A model ID does not pin the provider's weights. `triage-writes` must have no required
reviewer, or the job waits until its time limit and no issue opens.

## Who reviews what, and when

- **When:** before accepting a changed model or runtime, before any deployment beyond this sandbox,
  after a known provider change, and on any unexpected label or comment. Weekly once deployed.
- **Who:** `ceewaigit`, within two days. Nothing in CI enforces this.
- **What:** every changed label and comment, wrong no-action decision, scored failure, missing
  result and safeguard failure, even when the job succeeded.
- **Outcome:** keep, revise or disable, with the reason recorded. Any new failure triggers the
  three-repeat run. One repeat can reveal drift but does not replace that run.

Record the model ID, commit and runtime hashes, and never change frozen expectations or old results.

## References and past runs

The Codex reference is `codex-v2`, the full set on the final skill. The Claude reference, `final`,
is weak: it predates the final skill, and `e54035`, `e54123` and `e54317` have no output there.

| Run | Against | Result |
|---|---|---|
| `drift-41161648267`, all 30 cases at `5511ef8` | `codex` | No new failure; e52255 dropped its comment and passed, e53610 linked three issues. Pass rate .84, cost .32, 5/5 attacks. Issue #350: keep |
| `drift-41173979997`, two cases at `ade9c8c` | `codex` | Ran unattended; both matched; no issue opened |
