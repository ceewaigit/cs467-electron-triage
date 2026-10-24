#!/usr/bin/env python3
"""Reconstruct the recorded input-only workspaces from their local Git commit.

    python3 prepare.py --destination /tmp/NEW_EMPTY_DIRECTORY

The destination must not exist. This needs local Git history, Python and no network.
It reads only the recorded runtime paths and frozen input.json files, never gold
answers or previous outcomes. Agent orchestration remains an explicit human step.
"""
import argparse
import hashlib
import importlib.util
import json
import pathlib
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def from_commit(commit, path):
    """Read a file from local history without checking it out or accessing a remote."""
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def neutralise(text):
    """Apply the same transformation as the historical replay helper."""
    import re
    text = re.sub(r"https?://(?:www\.)?github\.com/([\w.-]+)/([\w.-]+)/(?:issues|pull|discussions)/(\d+)[^\s)\]>]*",
                  r"`\1/\2#\3`", text)
    text = re.sub(r"(?<![\w/`])([\w.-]+/[\w.-]+#\d+)", r"`\1`", text)
    return re.sub(r"(?<![\w`])@([A-Za-z0-9][\w-]*)", "@​\\1", text)


def prepare(destination):
    """Rebuild every opaque case and verify recorded hashes before handing it to a runner."""
    manifest = json.loads((HERE / "manifest.json").read_text())
    source = manifest["source_commit"]
    runtime = {name: from_commit(source, name) for name in manifest["runtime_sha256"]}
    for name, raw in runtime.items():
        assert hashlib.sha256(raw).hexdigest() == manifest["runtime_sha256"][name], name
    destination.mkdir(parents=True, exist_ok=False)
    recorder = (ROOT / "evals/tools/offline_dry_run.py").read_bytes()
    assert hashlib.sha256(recorder).hexdigest() == manifest["recorder_sha256"], "recorder changed"
    (destination / "recorder.py").write_bytes(recorder)
    for token, metadata in manifest["cases"].items():
        directory = destination / "cases" / token
        checkout = directory / "checkout"
        for name, raw in runtime.items():
            target = checkout / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        case_raw = from_commit(source, f"evals/golden/cases/{metadata['case_id']}/input.json")
        assert hashlib.sha256(case_raw).hexdigest() == metadata["input_sha256"], token
        case = json.loads(case_raw)
        issue = {"number": 800000 + int(token[1:]), "title": neutralise(case["title"]),
                 "body": neutralise(case["body"]), "labels": case["labels_at_open"],
                 "state": "open", "author_association": case["author_association"],
                 "as_of": case["as_of"], "replay": True}
        (checkout / ".triage").mkdir()
        (checkout / ".triage/issue.json").write_text(json.dumps(issue, indent=1, ensure_ascii=False))
        spec = importlib.util.spec_from_file_location("context", checkout / "scripts/prepare_agent_context.py")
        context_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(context_module)
        count = context_module.prepare_context(checkout)
        recorded = ROOT / "evals/golden/cases" / metadata["case_id"] / "actual/assistant-dry-run/logs/run-1/context.json"
        context = json.loads(recorded.read_text())
        assert count == context["earlier_corpus_rows"], token
        for name, sha in context["file_sha256"].items():
            assert hashlib.sha256((checkout / name).read_bytes()).hexdigest() == sha, f"{token}/{name}"
        (directory / "context.json").write_text(json.dumps(context, indent=2) + "\n")
    print(f"Reconstructed {len(manifest['cases'])} input-only workspaces at {destination}.")
    print("No assistant was invoked. Do not reuse or overwrite the recorded experiment for new decisions.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=pathlib.Path, required=True)
    prepare(parser.parse_args().destination.resolve())
