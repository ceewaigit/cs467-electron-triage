#!/usr/bin/env python3
"""Compare a golden rerun with a reference run set and list what the owner must review.

    python3 evals/tools/score.py --runs drift-20261101
    python3 evals/tools/drift_report.py --runs drift-20261101 --reference codex

Reads results/score-<runs>.json, results/score-<reference>.json and the outputs in
cases/*/actual/<runs>/, and writes results/drift-<runs>.md. It prints one JSON line with
`needs_review`, which drift-check.yml uses to open a review issue. The review list follows
docs/DRIFT_REVIEW.md: every new failure, missing or failed execution, safety failure, and
output that differs from every reference run. A case the reference never scored cannot be
compared, so it is listed but does not ask for review. --cases limits a partial rerun.
A new failure also triggers the full three-repeat run before the configuration stays enabled.
"""
import argparse
import json

from score import ROOT, parse_comment


def load_score(name):
    """Read a score report written by the frozen scorer."""
    return json.loads((ROOT / "results" / f"score-{name}.json").read_text())


def signature(output):
    """Reduce one output to what a maintainer would see: labels, comment kinds and links."""
    kinds, refs = parse_comment(output.get("comment"))
    return (tuple(sorted(output.get("labels_added") or [])), tuple(sorted(kinds)), tuple(sorted(refs)))


def outputs(case, runs):
    """Read the successful outputs of one case and run set, keyed by run name."""
    folder = ROOT / "cases" / case / "actual" / runs
    return {path.stem: json.loads(path.read_text()) for path in sorted(folder.glob("run-*.json"))}


def failures(case, runs):
    """List failed executions, which the collector keeps outside the scorer's input."""
    return sorted(path.stem for path in (ROOT / "cases" / case / "actual" / runs / "failures").glob("run-*.json"))


def describe(sig):
    """Render a signature for the review list."""
    labels, kinds, refs = sig
    parts = [", ".join(f"`{label}`" for label in labels) or "no labels",
             "comment " + ",".join(kinds) if kinds else "no comment"]
    if refs:
        parts.append("refs " + ", ".join(f"#{ref}" for ref in refs))
    return "; ".join(parts)


def compare(runs, reference, cases=None):
    """Return the review items for each case, grouped by reason, and the report lines."""
    new, old = load_score(runs)["cases"], load_score(reference)["cases"]
    review = {"new failure": [], "fixed": [], "missing or failed": [], "safety": [], "changed output": [],
              "no reference": []}
    for case in sorted(cases or old):
        before, after = old[case], new.get(case, {"n": 0, "passes": 0, "runs": []})
        failed = failures(case, runs)
        if after["n"] == 0 or failed:
            review["missing or failed"].append(f"{case}: {after['n']} scored, failed {failed or 'none'}")
        if after.get("any_safety"):
            review["safety"].append(f"{case}: " + "; ".join(s for r in after["runs"] for s in r["safety"]))
        if after["n"] and before["n"]:
            if before["passes"] == before["n"] and after["passes"] < after["n"]:
                reasons = sorted({f for r in after["runs"] for f in r["fails"]})
                review["new failure"].append(f"{case}: {after['passes']}/{after['n']} ({'; '.join(reasons)})")
            elif before["passes"] < before["n"] and after["passes"] == after["n"]:
                review["fixed"].append(f"{case}: {before['passes']}/{before['n']} before, "
                                       f"{after['passes']}/{after['n']} now")
        known = {signature(o) for o in outputs(case, reference).values()}
        if not known:
            review["no reference"].append(f"{case}: `{reference}` has no output for this case")
            continue
        for name, output in outputs(case, runs).items():
            if signature(output) not in known:
                review["changed output"].append(f"{case} {name}: {describe(signature(output))} "
                                                 f"([run]({output.get('run_url', '')}))")
    return review


def main():
    """Write the drift report and print whether the owner must review it."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True)
    ap.add_argument("--reference", required=True)
    ap.add_argument("--cases", help="Comma-separated case ids, for a partial rerun")
    a = ap.parse_args()
    review = compare(a.runs, a.reference, a.cases.split(",") if a.cases else None)
    summary = load_score(a.runs)["summary"]
    commits = sorted({o.get("head_sha", "")[:7] for case in load_score(a.runs)["cases"]
                      for o in outputs(case, a.runs).values()})
    needs_review = any(review[key] for key in ("new failure", "missing or failed", "safety", "changed output"))
    lines = [f"# Drift check `{a.runs}` against `{a.reference}`", "",
             f"Commit(s) {', '.join(commits) or 'none'}. Real run pass rate "
             f"{summary['real_run_pass_rate']}, error cost {summary['real_mean_cost_per_case']}, "
             f"adversarial {summary['adversarial_runs_passed']}, safety failures "
             f"{summary['safety_failures_any_run'] or 'none'}.", "",
             "**Owner review required.**" if needs_review else "**No change from the reference.**", "",
             "`ceewaigit` reviews every item below within two days and records the decision (keep, "
             "revise or disable) in the review issue. A new failure triggers the full three-repeat "
             "run (docs/DRIFT_REVIEW.md).", ""]
    for key, items in review.items():
        lines.append(f"## {key.capitalize()} ({len(items)})")
        lines.extend([f"- {item}" for item in items] or ["- none"])
        lines.append("")
    (ROOT / "results" / f"drift-{a.runs}.md").write_text("\n".join(lines))
    print(json.dumps({"needs_review": needs_review, **{k: len(v) for k, v in review.items()}}))


if __name__ == "__main__":
    main()
