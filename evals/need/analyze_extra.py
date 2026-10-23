#!/usr/bin/env python3
"""Extra triage metrics: repro requests, AI-authored proxy, duplicate-link lag.

Reads issues_table.csv and raw/issues/*.json; writes extra_metrics.json.
"""
import csv
import glob
import json
import pathlib
import re
import statistics as st
from datetime import datetime

HERE = pathlib.Path(__file__).resolve().parent
MAINT = {"MEMBER", "OWNER", "COLLABORATOR"}
WG = {"nmggithub", "georgexu99"}
REPRO = re.compile(r"fiddle|gist|standalone|minimal (repro|sample|test)|test ?case|reproduc", re.I)
AI = re.compile(r"in-depth investigation|\b(claude|codex|chatgpt|copilot|gpt-\d|llm|ai[- ](generated|assisted))\b", re.I)
ts = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))

# Duplicate / same-root-cause links found by reading maintainer and contributor comments.
# (issue, canonical it was linked to, who linked, when linked) - hand-coded from raw JSON.
DUP_LINKS = [
    (52255, 51761, "MarshallOfSound", "2026-08-11T07:56:00Z"),
    (53610, 51761, "nmggithub", "2026-09-06T03:50:00Z"),
    (53024, 52674, "YUCLing (non-maintainer)", "2026-08-19T23:46:00Z"),
    (53734, 53350, "MarshallOfSound (same answer re-typed, no link)", "2026-09-08T02:52:00Z"),
    (52821, 50531, "nikwen", "2026-08-17T21:59:00Z"),
    (52427, 48446, "nikwen", None),
    (53307, 53213, "nikwen", None),
]


def main():
    rows = {}
    for f in glob.glob(str(HERE / "raw/issues/*.json")):
        for r in json.loads(pathlib.Path(f).read_text())["data"]["search"]["nodes"]:
            rows[r["number"]] = r
    t = [r for r in csv.DictReader(open(HERE / "issues_table.csv"))
         if r["outside"] == "True" and r["template_closed"] == "False"]
    bugs_nogist = [r for r in t if r["bug_form"] == "True" and r["gist_at_open"] == "False"]

    def first_ask(n):
        r = rows[int(n)]
        times = [ts(c["createdAt"]) for c in r["comments"]["nodes"]
                 if c["author"] and (c["authorAssociation"] in MAINT or c["author"]["login"] in WG)
                 and c["author"]["login"] != r["author"]["login"] and REPRO.search(c["body"] or "")]
        for e in r["timelineItems"]["nodes"]:
            if e["__typename"] == "LabeledEvent" and e["label"]["name"] == "blocked/need-repro":
                times.append(ts(e["createdAt"]))
        return (min(times) - ts(r["createdAt"])).total_seconds() / 3600 if times else None

    asks = [first_ask(r["number"]) for r in bugs_nogist]
    asked = [a for a in asks if a is not None]
    outside_all = [r for r in rows.values() if r["authorAssociation"] not in MAINT
                   and (r["author"] or {}).get("__typename") != "Bot" and r["author"]["login"] not in WG]
    bodies = [len(r["body"] or "") for r in outside_all]
    dup = []
    for n, canon, who, when in DUP_LINKS:
        lag = round((ts(when) - ts(rows[n]["createdAt"])).total_seconds() / 3600, 1) if when else None
        dup.append({"issue": n, "linked_to": canon, "by": who, "hours_to_link": lag})
    m = {
        "bug_reports_without_gist_at_open": len(bugs_nogist),
        "asked_for_repro_label_or_comment": f"{len(asked)}/{len(bugs_nogist)}",
        "hours_to_repro_ask": {"median": round(st.median(asked), 1) if asked else None,
                               "max": round(max(asked), 1) if asked else None},
        "outside_issue_body_chars": {"median": st.median(bodies), "over_4000": sum(b > 4000 for b in bodies),
                                     "n": len(bodies)},
        "ai_authorship_proxy": f"{sum(bool(AI.search(r['body'] or '')) for r in outside_all)}/{len(outside_all)}",
        "duplicate_links": dup,
        "quarterly_issue_volume_search_api": {"2025Q3": 210, "2025Q4": 214, "2026Q1": 185, "2026Q2": 198, "2026Q3": 193},
    }
    (HERE / "extra_metrics.json").write_text(json.dumps(m, indent=1))
    print(json.dumps(m, indent=1))


if __name__ == "__main__":
    main()
