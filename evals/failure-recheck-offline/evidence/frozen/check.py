#!/usr/bin/env python3
"""Prepare/reconstruct five input-only snapshots, collect first decisions, or score.

Reuses the verified context and export functions from the earlier experiment.
It does not invoke an assistant, call a provider or write to GitHub. Every output
uses exclusive creation. Keep preparation, assistant execution and scoring separate.
"""
import argparse
import datetime as dt
import importlib.util
import json
from pathlib import Path
import random
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
EVIDENCE = HERE / "evidence"
SOURCE = "7debabe981d26af3ff36cc4606f45bc6efb1daf3"
CASES = ("e52255", "e52266", "e52385", "e52463", "e53734")


def load_helper(path):
    spec = importlib.util.spec_from_file_location("recorded_context_helpers", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare(destination):
    helper = load_helper(ROOT / "evals/reproduction-check/experiment.py")
    helper.require(not EVIDENCE.exists() and not destination.exists(), "preserve existing evidence")
    def source(name):
        return subprocess.check_output(["git", "show", f"{SOURCE}:{name}"], cwd=ROOT)
    paths = json.loads(source("evals/golden/results/assistant-dry-run/manifest.json"))["runtime_sha256"]
    runtime = {name: source(name) for name in paths}
    frozen = {f"runtime/{name}": raw for name, raw in runtime.items()}
    frozen.update({"helper.py": source("evals/reproduction-check/experiment.py"),
                   "recorder.py": source(helper.RECORDER), "score.py": source(helper.SCORER),
                   "policies/latest-SKILL.md": runtime[helper.SKILL],
                   "protocol.md": (HERE / "PROTOCOL.md").read_bytes(),
                   "check.py": Path(__file__).read_bytes()})
    order = list(CASES)
    random.Random(4672028).shuffle(order)
    for case in order:
        for name in ("input.json", "expected.json"):
            raw = source(f"evals/golden/cases/{case}/{name}")
            frozen[f"cases/{case}/{name}"] = raw
            helper.write_new(HERE / "cases" / case / name, raw)
    manifest = {"source_commit": SOURCE, "prepared_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                "execution_mode": "coding-assistant-dry-run", "writes_executed": False,
                "model_identifier": "inherited Codex backend; exact identifier unavailable",
                "selection": "five prior scored failures; not a fresh or representative sample",
                "repetitions": 1, "planned_first_decisions": 5, "seed": 4672028,
                "runtime_sha256": {name: helper.sha256(raw) for name, raw in runtime.items()},
                "freeze_sha256": {name: helper.sha256(raw) for name, raw in frozen.items()},
                "batches": [{"id": f"s{index:03d}", "arm": "latest", "opaque_arm": "A", "repetition": 1,
                             "cases": [{"case_id": case, "token": "d001"}]}
                            for index, case in enumerate(order, 1)]}
    for name, raw in frozen.items():
        helper.write_new(EVIDENCE / "frozen" / name, raw)
    helper.construct_workspaces(EVIDENCE, manifest, destination, record_context=True)
    helper.write_json(EVIDENCE / "manifest.json", manifest)
    helper.write_new(EVIDENCE / "manifest.sha256", (helper.digest(EVIDENCE / "manifest.json") + "\n").encode())
    print(f"Prepared five input-only sessions at {destination}; no inference performed.")


def score(helper):
    manifest = helper.load_manifest(EVIDENCE)
    collection = helper.read_json(EVIDENCE / "collection.json")
    helper.require(collection["first_decisions"] == 5, "seal all first decisions before scoring")
    for export in collection["exports"].values():
        for name, expected in export["file_sha256"].items():
            helper.require(helper.digest(HERE / name) == expected, f"changed export: {name}")
    scorer = helper.import_scorer(EVIDENCE / "frozen/score.py")
    rows = {}
    for case in CASES:
        expected = json.loads(helper.checked_frozen(EVIDENCE, manifest, f"cases/{case}/expected.json"))
        actual = helper.read_json(HERE / "cases" / case / "actual/latest/run-1.json")
        helper.require(actual["scored"], "invalid final proposal must be reported separately")
        rows[case] = {"score": scorer.score_run(expected, actual), "procedure": actual["procedure"]}
    report = {"case_count": 5, "passes": sum(row["score"]["pass"] for row in rows.values()),
              "weighted_error_cost_total": sum(row["score"]["cost"] for row in rows.values()),
              "cases": rows, "limits": "One trial on five selected old failures; no full-suite or causal claim."}
    helper.write_json(EVIDENCE / "score.json", report)
    print(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("step", choices=("prepare", "reproduce", "collect", "score"))
    parser.add_argument("--workspace", type=Path)
    args = parser.parse_args()
    if args.step != "score" and args.workspace is None:
        parser.error("--workspace is required for this step")
    if args.step == "prepare":
        prepare(args.workspace.resolve())
        return
    helper = load_helper(EVIDENCE / "frozen/helper.py")
    if args.step == "reproduce":
        helper.reproduce(HERE, args.workspace.resolve())
    elif args.step == "collect":
        helper.collect(HERE, args.workspace.resolve())
    else:
        score(helper)


if __name__ == "__main__":
    main()
