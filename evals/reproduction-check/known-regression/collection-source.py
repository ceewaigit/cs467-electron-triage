#!/usr/bin/env python3
"""Prepare or collect the separate, already-known e51957 regression check.

This uses the paired experiment's unchanged recorder and export checks. It never
invokes an assistant or the network. The known case is excluded from fresh-case
scores, and all writes refuse to replace existing evidence.
"""
import argparse
import json
import pathlib

import experiment as comparison


HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUTPUT = HERE / "known-regression"
PREVIOUS = ROOT / "evals/conservative-linking/cases/e51957"


def prepare(destination):
    """Make one input-only workspace from the baseline runtime and candidate skill."""
    comparison.require(not OUTPUT.exists(), "known regression already prepared")
    comparison.require(not destination.exists(), "workspace already exists")
    source_manifest = json.loads(comparison.from_commit(ROOT, comparison.OLD_MANIFEST))
    runtime = {name: comparison.from_commit(ROOT, name)
               for name in source_manifest["runtime_sha256"]}
    policy = (HERE / "policies/candidate-SKILL.md").read_bytes()
    protocol = comparison.read_json(HERE / "protocol.json")
    comparison.require(comparison.sha256(policy) == protocol["policy_sha256"]["candidate"],
                       "candidate differs from protocol")
    opening = comparison.read_json(PREVIOUS / "input.json")
    corpus, count = comparison.earlier_corpus(runtime[comparison.CORPUS], opening["as_of"])
    files = {**runtime, comparison.SKILL: policy, comparison.CORPUS: corpus,
             ".triage/issue.json": comparison.json_bytes(comparison.normalized_issue(opening, "d001"))}
    directory = destination / "cases/d001"
    context = {"case_token": "d001", "earlier_corpus_rows": count,
               "file_sha256": {name: comparison.sha256(raw) for name, raw in sorted(files.items())}}
    for name, raw in files.items():
        comparison.write_new(directory / "checkout" / name, raw)
    comparison.write_json(directory / "context.json", context)
    recorder = comparison.from_commit(ROOT, comparison.RECORDER)
    comparison.write_new(destination / "recorder.py", recorder)
    for name in ("input.json", "expected.json"):
        comparison.write_new(OUTPUT / name, (PREVIOUS / name).read_bytes())
    comparison.write_json(OUTPUT / "preparation.json", {
        "source_commit": comparison.BASELINE, "case_id": "e51957",
        "fresh_case": False, "context_sha256": comparison.digest(directory / "context.json"),
        "recorder_sha256": comparison.sha256(recorder),
        "policy_sha256": comparison.sha256(policy),
        "protocol_sha256": comparison.digest(HERE / "protocol.json"),
        "expected_sha256": comparison.digest(OUTPUT / "expected.json"),
        "input_sha256": comparison.digest(OUTPUT / "input.json"),
    })
    print(f"Prepared one known regression at {destination}; no assistant invoked.")


def collect(workspace):
    """Preserve the first proposal and assess the unchanged previous expectation."""
    comparison.require(not (OUTPUT / "result.json").exists(), "preserve known regression result")
    preparation = comparison.read_json(OUTPUT / "preparation.json")
    comparison.require(comparison.digest(workspace / "recorder.py") == preparation["recorder_sha256"],
                       "recorder changed")
    directory = workspace / "cases/d001"
    comparison.verify_case(directory, preparation)
    events = [json.loads(line) for line in (directory / "transcript.jsonl").read_text().splitlines()]
    proposal = comparison.read_json(directory / "proposal.json")
    comparison.require(events[0]["event"] == "context"
                       and events[0]["content"] == comparison.displayed_context(directory / "checkout"),
                       "displayed context differs")
    comparison.require(sum(event["event"] == "assistant_decision" for event in events) == 1
                       and events[-1]["event"] == "assistant_decision"
                       and events[-1]["content"] == proposal, "not a single preserved first decision")
    for name in ("input", "expected"):
        comparison.require(comparison.digest(OUTPUT / f"{name}.json") == preparation[f"{name}_sha256"],
                           f"known {name} changed")
    for name in ("context.json", "proposal.json", "transcript.jsonl"):
        comparison.write_new(OUTPUT / name, (directory / name).read_bytes())
    comparison.write_new(OUTPUT / "issue.json", (directory / "checkout/.triage/issue.json").read_bytes())
    comparison.write_new(OUTPUT / "transcript.md", comparison.readable_transcript(events))
    outcome, validations = comparison.export_proposal(proposal, directory / "checkout")
    procedure = comparison.procedure_checks(events, outcome)
    scorer_raw = comparison.from_commit(ROOT, comparison.SCORER)
    comparison.write_new(OUTPUT / "score.py", scorer_raw)
    scorer = comparison.import_scorer(OUTPUT / "score.py")
    result = scorer.score_run(comparison.read_json(OUTPUT / "expected.json"), outcome)
    kinds, _ = scorer.parse_comment(outcome["comment"])
    fixed = (outcome["scored"] and result["pass"]
             and "blocked/need-repro" in outcome["labels_added"] and "need-repro" in kinds
             and all(procedure[name] for name in ("checks_executed", "labels_validated_before_decision",
                                                  "comment_rendered_before_decision")))
    comparison.write_json(OUTPUT / "actual.json", outcome)
    comparison.write_json(OUTPUT / "export-validation.json", validations)
    comparison.write_json(OUTPUT / "result.json", {
        "fresh_case": False, "adoption_prerequisite_passed": fixed,
        "score": result, "procedure": procedure, "writes_executed": False,
        "evidence_sha256": {path.name: comparison.digest(path) for path in sorted(OUTPUT.iterdir())
                            if path.is_file()},
    })
    print(json.dumps({"known_regression_fixed": fixed, "score": result}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("prepare", "collect"))
    parser.add_argument("--workspace", type=pathlib.Path, required=True)
    args = parser.parse_args()
    (prepare if args.operation == "prepare" else collect)(args.workspace.resolve())


if __name__ == "__main__":
    main()
