#!/usr/bin/env python3
"""Validate the labels the agent wants to add, before it calls add_labels.

Usage: python3 .claude/skills/issue-triage/scripts/check_labels.py "component/tray" "blocked/need-repro"

Checks, none of which need judgement:
  - every label is in assets/allowed-labels.txt (the same list the workflow's
    safe-outputs allowlist enforces; this check only gives earlier feedback);
  - no label is already on the issue;
  - at most 3 labels, at most 2 of them component/*;
  - blocked/need-repro only on a bug report with no gist, and not when the
    bot already asked for a supported version.
Exit code 0 means every label passed.
"""
import json
import pathlib
import sys

VERSION = "issue-triage/check_labels v1"
SKILL = pathlib.Path(__file__).resolve().parents[1]
REPO = SKILL.parents[2]


def main(wanted):
    allowed = set((SKILL / "assets" / "allowed-labels.txt").read_text().splitlines())
    issue = json.loads((REPO / ".triage" / "issue.json").read_text())
    present = set(issue.get("labels") or [])
    body = issue.get("body") or ""
    errors = []
    for lab in wanted:
        if lab not in allowed:
            errors.append(f"{lab!r} is not in the allowlist")
        if lab in present:
            errors.append(f"{lab!r} is already on the issue")
    if len(wanted) > 3:
        errors.append("more than 3 labels")
    if sum(lab.startswith("component/") for lab in wanted) > 2:
        errors.append("more than 2 component labels")
    if "blocked/need-repro" in wanted:
        if "### Testcase Gist URL" not in body:
            errors.append("blocked/need-repro is only for bug reports")
        if "https://gist.github.com/" in body.split("### Testcase Gist URL")[-1][:300]:
            errors.append("blocked/need-repro but the report has a gist")
        if "blocked/need-info ❌" in present:
            errors.append("blocked/need-repro but the bot already asked for a supported version")
    print(f"[{VERSION}] {'ok' if not errors else 'rejected'}")
    print(json.dumps({"labels": wanted, "valid": not errors, "errors": errors}, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
