#!/usr/bin/env python3
"""Workflow step (runs before the agent, outside its sandbox): save the
triggering issue to .triage/issue.json for the skill's scripts.

Inputs come from environment variables set by the workflow:
  REPO, ISSUE   repository and issue number
  AS_OF         when the issue was opened (replays pass the original time)
  ASSOC         the author's association (replays pass the original value)
  REPLAY        "true" for evaluation replays started by workflow_dispatch

Only workflow_dispatch can set AS_OF/ASSOC by hand, and GitHub only lets
users with write access dispatch a workflow, so issue authors cannot.
"""
import json
import os
import pathlib
import re
import subprocess
import sys

ASSOCIATIONS = {"OWNER", "MEMBER", "COLLABORATOR", "CONTRIBUTOR", "FIRST_TIME_CONTRIBUTOR", "FIRST_TIMER", "NONE"}


def main():
    repo, number = os.environ["REPO"], os.environ["ISSUE"]
    if not re.fullmatch(r"\d{1,7}", number):
        sys.exit(f"invalid issue number {number!r}")
    raw = json.loads(subprocess.run(["gh", "api", f"repos/{repo}/issues/{number}"],
                                    check=True, capture_output=True, text=True).stdout)
    if raw.get("pull_request"):
        sys.exit("not an issue")
    as_of = os.environ.get("AS_OF") or raw["created_at"]
    if not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", as_of):
        sys.exit(f"invalid as_of {as_of!r}")
    assoc = (os.environ.get("ASSOC") or raw.get("author_association") or "NONE").upper()
    if assoc not in ASSOCIATIONS:
        sys.exit(f"invalid author association {assoc!r}")
    issue = {
        "number": raw["number"],
        "title": raw["title"],
        "body": raw.get("body") or "",
        "labels": [l["name"] for l in raw.get("labels", [])],
        "state": raw["state"],
        "author_association": assoc,
        "as_of": as_of,
        "replay": os.environ.get("REPLAY") == "true",
    }
    out = pathlib.Path(".triage")
    out.mkdir(exist_ok=True)
    (out / "issue.json").write_text(json.dumps(issue, indent=1, ensure_ascii=False))
    print(f"saved issue #{issue['number']} ({assoc}, as of {as_of}, {len(issue['labels'])} labels)")


if __name__ == "__main__":
    main()
