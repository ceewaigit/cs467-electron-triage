#!/usr/bin/env python3
"""Score all five completed first runs and reconcile independent review and cost.

This offline summary uses the frozen scorer, never calls a provider, and refuses
to replace its saved result. No result is written until all five cases are ready.
"""
from decimal import Decimal
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def read(path):
    return json.loads(path.read_text())


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def main():
    manifest = read(HERE / "manifest.json")
    scorer_path = ROOT / "evals/tools/score.py"
    require(hashlib.sha256(scorer_path.read_bytes()).hexdigest() == manifest["scorer_sha256"],
            "Frozen scorer changed.")
    spec = importlib.util.spec_from_file_location("frozen_scorer", scorer_path)
    scorer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scorer)
    runs = read(HERE / "replay" / f"runs-{manifest['variant']}.json")
    require(len(runs) == 5 and {r["case"] for r in runs.values()} == set(manifest["cases_in_order"]),
            "Expected exactly five distinct first-case dispatches.")
    rows = {}
    dollars = {"agent": Decimal(0), "detection": Decimal(0)}
    for case in manifest["cases_in_order"]:
        directory = HERE / "cases" / case
        for name, digest in manifest["case_sha256"][case].items():
            require(hashlib.sha256((directory / name).read_bytes()).hexdigest() == digest,
                    f"Frozen case changed: {case}/{name}")
        actual = read(directory / "actual" / manifest["variant"] / "run-1.json")
        require(actual["conclusion"] == "success" and actual["head_sha"] == manifest["source_commit"],
                f"No valid completed decision at the intended source: {case}")
        score = scorer.score_run(read(directory / "expected.json"), actual)
        reviews = [HERE / "evidence" / f"independent-{case}-results-v{version}.json"
                   for version in (4, 3, 2)]
        review_path = next((path for path in reviews if path.exists()), None)
        require(review_path is not None, f"Independent result missing: {case}")
        independent = read(review_path)
        require(score == independent["independent_frozen_score"], f"Independent score differs: {case}")
        cost = read(HERE / "evidence" / f"coordinator-cost-{case}.json")
        total = Decimal(cost["recorded_total_usd_estimate"])
        require(total == Decimal(str(independent["combined_rate_derived_estimate_usd"])),
                f"Independent cost differs: {case}")
        for phase in dollars:
            dollars[phase] += Decimal(cost["phases"][phase]["recorded_usd_estimate"])
        rows[case] = {"issue": actual["issue"], "run_id": actual["run_id"],
                      "run_url": actual["run_url"], "score": score,
                      "labels_added": actual["labels_added"], "comment": actual["comment"],
                      "recorded_usd_estimate": str(total),
                      "independent_review": str(review_path.relative_to(HERE))}
    report = {"source_commit": manifest["source_commit"], "model": manifest["model"],
              "valid_live_outputs": len(rows), "passes": sum(r["score"]["pass"] for r in rows.values()),
              "weighted_error_cost_total": sum(r["score"]["cost"] for r in rows.values()),
              "safety_failures": sum(r["score"]["safety"] for r in rows.values()),
              "recorded_usd_estimate_by_phase": {k: str(v) for k, v in dollars.items()},
              "recorded_total_usd_estimate": str(sum(dollars.values())), "cases": rows,
              "limits": ["Five selected prior failures, one trial each; not a representative accuracy estimate.",
                         "Recorded inference estimate includes agent and detection, not an inspected invoice.",
                         "No combined old/new full-suite rate, causal claim, or 90-run acceptance claim.",
                         "Ordinary allowed actions do not test adversarial rejection or hard-limit exhaustion."]}
    with (HERE / "result.json").open("x") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(json.dumps({key: value for key, value in report.items() if key != "cases"}, indent=2))


if __name__ == "__main__":
    main()
