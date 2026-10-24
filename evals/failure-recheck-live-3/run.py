#!/usr/bin/env python3
"""Run one explicit stage for one of the five recorded cases.

Uses the existing replay helper for neutralisation, dispatch and collection.
The separate case copies and state directory keep historical evidence intact.
No default case, repetitions, retry or force-overwrite option is provided.
File and dispatch contact the owner's sandbox; dispatch spends provider credit.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def main():
    manifest = json.loads((HERE / "manifest.json").read_text())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("step", choices=("file", "dispatch", "collect"))
    parser.add_argument("--case", required=True, choices=manifest["cases_in_order"])
    args = parser.parse_args()
    for name, expected in manifest["runtime_sha256"].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise SystemExit(f"Runtime changed: {name}; do not mix configurations.")
    helper = ROOT / "evals/tools/replay.py"
    if hashlib.sha256(helper.read_bytes()).hexdigest() != manifest["replay_sha256"]:
        raise SystemExit("Replay helper changed.")
    for case, hashes in manifest["case_sha256"].items():
        for name, expected in hashes.items():
            if hashlib.sha256((HERE / "cases" / case / name).read_bytes()).hexdigest() != expected:
                raise SystemExit(f"Frozen case changed: {case}/{name}")
    spec = importlib.util.spec_from_file_location("five_case_replay", helper)
    replay = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(replay)
    replay.GOLDEN = HERE
    replay.STATE = HERE / "replay"
    replay.VARIANT = manifest["variant"]
    replay.WORKFLOW = "issue-triage.lock.yml"
    if replay.REPO != manifest["repository"]:
        raise SystemExit("Wrong replay repository.")
    if args.step == "dispatch":
        remote = replay.api(f"repos/{replay.REPO}/commits/{manifest['requested_ref']}")
        if remote["sha"] != manifest["source_commit"]:
            raise SystemExit("Remote ref changed; refuse to evaluate a different commit.")
        active = replay.api(f"repos/{replay.REPO}/actions/workflows/{replay.WORKFLOW}/runs?per_page=100")
        if any(run["status"] != "completed" for run in active["workflow_runs"]):
            raise SystemExit("Another triage run is active; wait and inspect it first.")
    options = SimpleNamespace(cases={args.case}, k=1, ref=manifest["requested_ref"], force=False)
    {"file": replay.cmd_file, "dispatch": replay.cmd_dispatch,
     "collect": replay.cmd_collect}[args.step](options)


if __name__ == "__main__":
    main()
