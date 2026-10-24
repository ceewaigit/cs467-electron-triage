#!/usr/bin/env python3
"""Export completed recorder sessions and proposed outcomes without reading gold answers.

Run from any directory: python3 collect.py --workspace PREPARED_DIRECTORY
This writes a new assistant-dry-run variant and refuses existing output records.
Run the frozen scorer separately, only after every first decision has been sealed.
"""
import argparse
import datetime as dt
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]
VARIANT = "assistant-dry-run"


def digest(path):
    """Hash exact bytes for provenance and first-decision preservation."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export(workspace):
    """Check all sessions before exporting any; never modify their decisions."""
    manifest = json.loads((HERE / "manifest.json").read_text())
    sessions = []
    for token, metadata in manifest["cases"].items():
        directory = workspace / "cases" / token
        checkout = directory / "checkout"
        context = json.loads((directory / "context.json").read_text())
        for name, sha in context["file_sha256"].items():
            assert digest(checkout / name) == sha, f"changed snapshot: {token}/{name}"
        proposal = json.loads((directory / "proposal.json").read_text())
        events = [json.loads(line) for line in (directory / "transcript.jsonl").read_text().splitlines()]
        assert events[-1]["event"] == "assistant_decision", token
        assert events[-1]["content"] == proposal, token
        assert sum(e["event"] == "assistant_decision" for e in events) == 1, token
        destination = ROOT / "evals/golden/cases" / metadata["case_id"] / "actual" / VARIANT
        assert not destination.exists(), f"preserve existing evidence: {destination}"
        sessions.append((token, metadata, directory, checkout, proposal, events, destination))

    sealed = {"sealed_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
              "phase": "all first decisions recorded; expected outcomes not read by this exporter",
              "sessions": {t: {"proposal_sha256": digest(d / "proposal.json"),
                               "transcript_sha256": digest(d / "transcript.jsonl")}
                           for t, _, d, _, _, _, _ in sessions}}
    with (HERE / "sealed-proposals.json").open("x") as stream:
        stream.write(json.dumps(sealed, indent=2) + "\n")
    procedures = {}
    for token, metadata, directory, checkout, proposal, events, destination in sessions:
        labels, comment = [], None
        comment_request = None
        for item in proposal["items"]:
            if item["type"] == "add_labels":
                labels = item["labels"]
            elif item["type"] == "triage_comment":
                comment_request = item
                command = [sys.executable, ".claude/skills/issue-triage/scripts/render_comment.py",
                           "--kinds", item["kinds"], "--refs", item["refs"]]
                rendered = subprocess.run(command, cwd=checkout, capture_output=True, text=True)
                assert rendered.returncode == 0, f"invalid final comment proposal: {token}"
                comment = rendered.stdout.split("-----BEGIN COMMENT-----\n", 1)[1].split("\n-----END COMMENT-----", 1)[0]
        scripts = [e for e in events if e["event"] == "script"]
        good = [e for e in scripts if e["exit_code"] == 0]
        checks = [e for e in good if e["command"][1].endswith("/triage_checks.py")]
        validated = {label for e in good if e["command"][1].endswith("/check_labels.py") for label in e["command"][2:]}
        comments = [e for e in good if e["command"][1].endswith("/render_comment.py")]
        procedures[metadata["case_id"]] = {
            "checks_executed": bool(checks), "labels_validated": set(labels) <= validated,
            "comment_rendered_before_decision": comment is None or any(comment in e["stdout"] for e in comments),
            "rejected_script_calls": [{"command": e["command"], "output": e["stdout"]} for e in scripts if e["exit_code"]],
        }
        logs = destination / "logs/run-1"
        logs.mkdir(parents=True)
        for name in ("context.json", "proposal.json", "transcript.jsonl"):
            shutil.copy2(directory / name, logs / name)
        shutil.copy2(checkout / ".triage/issue.json", logs / "issue.json")
        transcript = [f"# Coding-assistant dry run: {metadata['case_id']} ({token})\n",
                      "Recorded context, helper calls/results, and final proposed actions. No actions were published.\n"]
        for number, event in enumerate(events, 1):
            transcript.append(f"\n## {number}. {event['event']} — {event['time_utc']}\n")
            if event["event"] == "context":
                transcript.append(event["content"] + "\n")
            else:
                transcript.append("\n````json\n" + json.dumps(event, indent=2, ensure_ascii=False) + "\n````\n")
        (logs / "transcript.md").write_text("".join(transcript))
        outcome = {"labels_added": labels, "comment": comment, "other_writes": [],
                   "execution_mode": "coding-assistant-dry-run", "writes_executed": False,
                   "interpretation": "Scorer field names represent proposed actions, not observed GitHub writes.",
                   "source_commit": manifest["source_commit"], "case_token": token,
                   "proposal_sha256": digest(directory / "proposal.json"),
                   "explanation": proposal["explanation"]}
        (destination / "run-1.json").write_text(json.dumps(outcome, indent=2, ensure_ascii=False) + "\n")
    (HERE / "procedure-checks.json").write_text(json.dumps(procedures, indent=2, ensure_ascii=False) + "\n")
    print(f"Exported {len(sessions)} first decisions; no gold files read, no remote writes.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=pathlib.Path, required=True)
    export(parser.parse_args().workspace.resolve())
