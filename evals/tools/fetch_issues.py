#!/usr/bin/env python3
"""Fetch electron/electron issues as they looked when they were opened.

Read-only GraphQL via `gh api graphql`. For each issue it keeps the opening
title (from the first rename event, if any) and the opening body (the oldest
entry in userContentEdits, if the body was ever edited). Comments, later
labels and the close state are deliberately not kept: they did not exist when
the issue was opened.

Raw API pages go to evals/data/raw/; the cleaned rows go to
evals/data/electron_issues.jsonl.

Usage: python3 evals/tools/fetch_issues.py 2025-07-01 2026-09-30
"""
import json
import pathlib
import subprocess
import sys
from datetime import date, timedelta

REPO = "electron/electron"
ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "electron_issues.jsonl"

QUERY = """
query($q: String!, $after: String) {
  search(query: $q, type: ISSUE, first: 25, after: $after) {
    issueCount
    pageInfo { hasNextPage endCursor }
    nodes { ... on Issue {
      number title createdAt authorAssociation
      author { login __typename }
      body
      userContentEdits(last: 1) { totalCount nodes { editedAt diff } }
      timelineItems(first: 1, itemTypes: [RENAMED_TITLE_EVENT]) {
        nodes { ... on RenamedTitleEvent { createdAt previousTitle } } }
      labeledAtOpen: timelineItems(first: 20, itemTypes: [LABELED_EVENT]) {
        nodes { ... on LabeledEvent { createdAt actor { login } label { name } } } }
    } }
  }
}
"""


def gql(q, after):
    """Fetch one read-only GraphQL search page for a dated issue query."""
    args = ["gh", "api", "graphql", "-f", f"query={QUERY}", "-f", f"q={q}"]
    if after:
        args += ["-f", f"after={after}"]
    return json.loads(subprocess.run(args, check=True, capture_output=True, text=True).stdout)


def months(start, end):
    """Split an inclusive date range into monthly search slices."""
    d = start
    while d <= end:
        nxt = (d.replace(day=1) + timedelta(days=32)).replace(day=1)
        yield d, min(nxt - timedelta(days=1), end)
        d = nxt


def opening_state(n):
    """Reconstruct opening text and early form/bot labels from a saved GraphQL node."""
    created = n["createdAt"]
    edits = n["userContentEdits"]
    body = n["body"] or ""
    body_source = "current (never edited)"
    if edits["totalCount"] and edits["nodes"]:
        oldest = edits["nodes"][0]
        body = oldest["diff"] or ""
        body_source = f"userContentEdits oldest revision ({oldest['editedAt']})"
    renames = n["timelineItems"]["nodes"]
    title = renames[0]["previousTitle"] if renames else n["title"]
    # Labels applied in the first two minutes by the issue form (actor is the
    # author) or by Electron's deterministic bots count as known at opening
    # time. A human triager's label is hindsight even if it came quickly.
    author = (n["author"] or {}).get("login")
    early_actors = {author, "electron-issue-triage", "github-actions"}
    bot_labels = sorted({
        e["label"]["name"] for e in n["labeledAtOpen"]["nodes"]
        if e and e.get("actor") and e["actor"]["login"] in early_actors
        and seconds_between(created, e["createdAt"]) <= 120
    })
    return {
        "number": n["number"],
        "created_at": created,
        "author": (n["author"] or {}).get("login"),
        "author_type": (n["author"] or {}).get("__typename"),
        "author_association": n["authorAssociation"],
        "title": title,
        "body": body,
        "body_source": body_source,
        "edit_count": edits["totalCount"],
        "labels_at_open": bot_labels,
    }


def seconds_between(a, b):
    """Return elapsed seconds between two GitHub UTC timestamps."""
    from datetime import datetime
    f = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))
    return (f(b) - f(a)).total_seconds()


def main(start, end):
    """Save raw pages and cleaned opening-state rows, checking each search slice is complete."""
    RAW.mkdir(parents=True, exist_ok=True)
    rows = []
    for a, b in months(date.fromisoformat(start), date.fromisoformat(end)):
        q = f"repo:{REPO} is:issue created:{a}..{b}"
        after, page, got = None, 0, 0
        while True:
            data = gql(q, after)
            (RAW / f"{a}_{page:02d}.json").write_text(json.dumps(data))
            s = data["data"]["search"]
            nodes = [n for n in s["nodes"] if n]
            rows += [opening_state(n) for n in nodes]
            got += len(nodes)
            if not s["pageInfo"]["hasNextPage"]:
                break
            after, page = s["pageInfo"]["endCursor"], page + 1
        print(f"{a}..{b}: {got} of {s['issueCount']}", file=sys.stderr)
        assert got == s["issueCount"], "search slice incomplete"
    rows.sort(key=lambda r: r["number"])
    with OUT.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} issues to {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main(*sys.argv[1:3])
