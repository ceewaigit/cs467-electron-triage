#!/usr/bin/env python3
"""Retain the skipped automatic run before manually replaying one sandbox case.

GitHub's static run title omits the issue number. Require one unambiguous event
after this issue was created, at the pinned commit, and disclose that association.
"""
import argparse
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
MANIFEST = json.loads((HERE / "manifest.json").read_text())


def api(path):
    return json.loads(subprocess.check_output([
        "gh", "api", f"repos/{MANIFEST['repository']}/{path}"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True, choices=MANIFEST["cases_in_order"])
    case = parser.parse_args().case
    state = json.loads((HERE / "replay" / f"issues-{MANIFEST['variant']}.json").read_text())
    numbers = state[case]["issues"]
    if len(numbers) != 1:
        raise SystemExit("Expected one sandbox issue for this case.")
    issue = api(f"issues/{numbers[0]}")
    runs = api("actions/workflows/issue-triage.lock.yml/runs?event=issues&per_page=100")
    matches = [run for run in runs["workflow_runs"]
               if run["created_at"] >= issue["created_at"]
               and run["head_sha"] == MANIFEST["source_commit"]]
    if len(matches) != 1:
        raise SystemExit("Automatic-event association is ambiguous; inspect before dispatch.")
    run = matches[0]
    jobs = api(f"actions/runs/{run['id']}/jobs?per_page=100")
    if (run["status"] != "completed" or run["conclusion"] != "skipped"
            or len(jobs["jobs"]) != 7
            or any(job["conclusion"] != "skipped" for job in jobs["jobs"])):
        raise SystemExit("Automatic run did not skip every job; do not manually dispatch.")
    result = {"issue": issue, "run": run, "jobs": jobs,
              "association_limit": "Sole event after fresh issue creation at the pinned source; "
                                   "run-list metadata does not expose issue inputs."}
    with (HERE / f"automatic-trigger-control-{case}.json").open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(f"{case}: issue {numbers[0]}, automatic run {run['id']}, all seven jobs skipped.")


if __name__ == "__main__":
    main()
