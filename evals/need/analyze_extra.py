#!/usr/bin/env python3
"""Extra triage metrics: repro requests, AI-authored proxy, duplicate-link lag.

Reads issues_table.csv and raw/issues/*.json; writes extra_metrics.json.
Run analyze_issues.py first to rebuild the opening-state form/gist classifications.

Repro requests are recognized by a phrase match in a maintainer comment or by
the need-repro label; this is a workload proxy, not a judgement of the request.
The AI phrase match likewise measures mentions, not proof of AI authorship.
Body length and AI mentions use the retrieval snapshot; the no-gist cohort uses
opening-state fields from issues_table.csv.
"""
import csv
import glob
import json
import pathlib
import re
import statistics
from datetime import datetime

HERE = pathlib.Path(__file__).resolve().parent
MAINT = {"MEMBER", "OWNER", "COLLABORATOR"}
WG_LOGINS = {"nmggithub", "georgexu99"}
REPRO = re.compile(r"fiddle|gist|standalone|minimal (repro|sample|test)|test ?case|reproduc", re.I)
AI = re.compile(r"in-depth investigation|\b(claude|codex|chatgpt|copilot|gpt-\d|llm|ai[- ](generated|assisted))\b", re.I)


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


def parse_timestamp(value):
    """Parse GitHub's UTC timestamp into a timezone-aware datetime."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def main():
    """Join the per-issue cohort with response histories and hand-coded duplicate links."""
    issues_by_number = {}
    for path in glob.glob(str(HERE / "raw/issues/*.json")):
        for issue in json.loads(pathlib.Path(path).read_text())["data"]["search"]["nodes"]:
            issues_by_number[issue["number"]] = issue
    with (HERE / "issues_table.csv").open(newline="") as table_file:
        eligible_issues = [
            issue for issue in csv.DictReader(table_file)
            if issue["outside"] == "True" and issue["template_closed"] == "False"
        ]
    bugs_without_gist = [
        issue for issue in eligible_issues
        if issue["bug_form"] == "True" and issue["gist_at_open"] == "False"
    ]

    def first_ask(issue_number):
        """Return hours to the earliest matching comment or label, or None if absent."""
        issue = issues_by_number[int(issue_number)]
        times = [parse_timestamp(comment["createdAt"]) for comment in issue["comments"]["nodes"]
                 if comment["author"] and (comment["authorAssociation"] in MAINT or comment["author"]["login"] in WG_LOGINS)
                 and comment["author"]["login"] != issue["author"]["login"] and REPRO.search(comment["body"] or "")]
        for event in issue["timelineItems"]["nodes"]:
            if event["__typename"] == "LabeledEvent" and event["label"]["name"] == "blocked/need-repro":
                times.append(parse_timestamp(event["createdAt"]))
        return (min(times) - parse_timestamp(issue["createdAt"])).total_seconds() / 3600 if times else None

    ask_hours = [first_ask(issue["number"]) for issue in bugs_without_gist]
    observed_ask_hours = [delay for delay in ask_hours if delay is not None]
    outside_issues = [
        issue for issue in issues_by_number.values() if issue["authorAssociation"] not in MAINT
        and (issue["author"] or {}).get("__typename") != "Bot" and issue["author"]["login"] not in WG_LOGINS
    ]
    body_lengths = [len(issue["body"] or "") for issue in outside_issues]
    duplicate_links = []
    for issue_number, canonical_number, linked_by, linked_at in DUP_LINKS:
        created = parse_timestamp(issues_by_number[issue_number]["createdAt"])
        lag = round((parse_timestamp(linked_at) - created).total_seconds() / 3600, 1) if linked_at else None
        duplicate_links.append({"issue": issue_number, "linked_to": canonical_number, "by": linked_by, "hours_to_link": lag})
    metrics = {
        "bug_reports_without_gist_at_open": len(bugs_without_gist),
        "asked_for_repro_label_or_comment": f"{len(observed_ask_hours)}/{len(bugs_without_gist)}",
        "hours_to_repro_ask": {"median": round(statistics.median(observed_ask_hours), 1) if observed_ask_hours else None,
                               "max": round(max(observed_ask_hours), 1) if observed_ask_hours else None},
        "outside_issue_body_chars": {"median": statistics.median(body_lengths), "over_4000": sum(b > 4000 for b in body_lengths),
                                     "n": len(body_lengths)},
        "ai_authorship_proxy": f"{sum(bool(AI.search(issue['body'] or '')) for issue in outside_issues)}/{len(outside_issues)}",
        "duplicate_links": duplicate_links,
        "quarterly_issue_volume_search_api": {"2025Q3": 210, "2025Q4": 214, "2026Q1": 185, "2026Q2": 198, "2026Q3": 193},
    }
    (HERE / "extra_metrics.json").write_text(json.dumps(metrics, indent=1))
    print(json.dumps(metrics, indent=1))


if __name__ == "__main__":
    main()
