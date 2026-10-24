#!/usr/bin/env python3
"""Separate two-case diagnostic: unchanged known inputs/targets, excluded metrics.

Four fresh anonymous sessions contain two cases each: one policy and repetition
per session. Preparation depends on the already-frozen fresh experiment so both
namespaces use exactly the same policies, source, recorder, scorer and protocol.
No command invokes an assistant, GitHub or any provider API.
"""
import argparse
import json
import pathlib
import sys

import experiment as comparison

KNOWN_IDS = ("e52255", "e53734")


def prepare(experiment, repo, destination):
    h = comparison.helpers(repo, experiment / "evidence")
    fresh = h.load_manifest(experiment / "evidence")
    directory = experiment / "known-cases"
    h.require(not directory.exists() and not destination.exists(), "preserve existing known-case preparation")
    h.require(not destination.is_relative_to(experiment) and not experiment.is_relative_to(destination),
              "runner and evaluator must use separate directory trees")
    for name in ("experiment.py", "known_cases.py"):
        h.require((pathlib.Path(__file__).parent / name).read_bytes()
                  == h.checked_frozen(experiment / "evidence", fresh, name),
                  "execution source changed after fresh preparation")
    protocol = h.checked_frozen(experiment / "evidence", fresh, "protocol.json")
    cases = []
    frozen_sources = {}
    for case_id in KNOWN_IDS:
        files = {}
        for name in ("input.json", "expected.json"):
            source_name = f"evals/golden/cases/{case_id}/{name}"
            raw = comparison.source(repo, source_name)
            relative = f"cases/{case_id}/{name}"
            frozen_sources[relative] = raw
            files[name] = {"path": relative, "sha256": h.sha256(raw), "source": source_name}
        cases.append({"id": case_id, "group": "known", "fresh_case": False,
                      "positive_controls": ["link"] if case_id == "e53734" else [],
                      "coverage_supported_refs": [53350] if case_id == "e53734" else [],
                      "acceptable_optional_refs": [51761, 52098] if case_id == "e52255" else [],
                      "repro_expectation": "optional" if case_id == "e53734" else "forbidden",
                      "files": files})
    frozen_sources["protocol.json"] = protocol
    frozen_sources["dataset.json"] = h.json_bytes({"namespace": "known", "cases": cases,
        "purpose": "Development-informed known diagnostics. Original golden inputs and expectations are byte-for-byte unchanged; excluded from fresh metrics."})
    for arm in comparison.ARMS:
        name = f"policies/{arm}-SKILL.md"
        frozen_sources[name] = h.checked_frozen(experiment / "evidence", fresh, name)
    for name, raw in frozen_sources.items():
        h.write_new(directory / name, raw)
    h.write_json(directory / "source-provenance.json", {
        "baseline_commit": comparison.BASELINE, "fresh_manifest_sha256": h.digest(experiment / "evidence/manifest.json"),
        "known_cases": list(KNOWN_IDS), "fresh_case": False,
        "files": {name: h.sha256(raw) for name, raw in frozen_sources.items()},
    })
    result = comparison.prepare(directory, repo, destination, namespace="known")
    for name in ("helper.py", "recorder.py", "score.py", *[f"runtime/{name}" for name in fresh["runtime_sha256"]]):
        h.require(result["freeze_sha256"][name] == fresh["freeze_sha256"][name], "known and fresh runtime source mismatch")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", type=pathlib.Path, default=comparison.HERE)
    parser.add_argument("--repo", type=pathlib.Path, default=comparison.ROOT)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("prepare", "reproduce"):
        commands.add_parser(command).add_argument("--destination", type=pathlib.Path, required=True)
    commands.add_parser("collect").add_argument("--workspace", type=pathlib.Path, required=True)
    commands.add_parser("score")
    args = parser.parse_args()
    experiment = args.experiment.resolve()
    if args.command == "prepare":
        prepare(experiment, args.repo.resolve(), args.destination.resolve())
    elif args.command == "reproduce":
        comparison.reproduce(experiment / "known-cases", args.destination.resolve())
    elif args.command == "collect":
        return 0 if comparison.collect(experiment / "known-cases", args.workspace.resolve()) else 1
    else:
        comparison.score(experiment / "known-cases")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as error:
        sys.exit(f"Stopped; existing evidence preserved: {error}")
