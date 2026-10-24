#!/usr/bin/env python3
"""Limit the disposable Actions checkout before the agent starts.

The search helper already filters candidates by opening time. This step also
filters the file on disk, so a direct Read cannot reveal future corpus entries.
It removes evaluation results and prose that discusses expected outcomes.

Do not run this against a development checkout. The command-line entry point
requires GitHub Actions and its matching workspace. Tests call prepare_context
with a temporary fixture. Git history is retained for gh-aw compatibility; this
is context minimisation, not a complete filesystem or network isolation boundary.
"""
import datetime as dt
import json
import os
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXCLUDED_PATHS = (
    "evals", "tests", "DESIGN.md", "docs", "README.md", "data/README.md", "CONTRIBUTING.md",
)


def timestamp(value):
    """Accept only the UTC timestamp format used by the frozen issue corpus."""
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value):
        raise ValueError(f"invalid UTC timestamp: {value!r}")
    return dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")


def prepare_context(root):
    """Filter corpus rows and remove grading material from one disposable checkout."""
    root = pathlib.Path(root)
    issue = json.loads((root / ".triage/issue.json").read_text(encoding="utf-8"))
    cutoff = timestamp(issue["as_of"])
    corpus_path = root / "data/issue-corpus.jsonl"
    original_lines = corpus_path.read_text(encoding="utf-8").splitlines()
    retained_lines = []
    # Validate every timestamp before changing any file. Equal timestamps are
    # excluded too: the current report was not available before its own opening.
    for line in original_lines:
        if not line.strip():
            continue
        row = json.loads(line)
        if timestamp(row["created_at"]) < cutoff:
            retained_lines.append(line)

    temporary_path = corpus_path.with_suffix(".jsonl.filtered")
    temporary_path.write_text("".join(line + "\n" for line in retained_lines), encoding="utf-8")
    temporary_path.replace(corpus_path)
    for relative_path in EXCLUDED_PATHS:
        path = root / relative_path
        if path.is_symlink() or path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)

    print(f"prepared context: {len(retained_lines)} earlier corpus rows retained; "
          "evaluation files and result summaries removed")
    return len(retained_lines)


def main():
    """Refuse local execution so this cleanup cannot erase submission files by accident."""
    workspace = os.environ.get("GITHUB_WORKSPACE")
    if os.environ.get("GITHUB_ACTIONS") != "true" or not workspace or pathlib.Path(workspace).resolve() != ROOT:
        print("refusing cleanup outside the matching GitHub Actions workspace", file=sys.stderr)
        return 1
    prepare_context(ROOT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
