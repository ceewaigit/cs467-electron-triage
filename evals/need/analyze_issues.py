#!/usr/bin/env python3
"""Triage-need metrics for electron/electron issues opened 1 Jul - 30 Sep 2026.

Reads raw/issues/*.json for response histories and ../data/electron_issues.jsonl
for reconstructed opening bodies. Writes issue_metrics.json and issues_table.csv.
Runs offline and leaves both source datasets unchanged.

Definitions
- maintainer comment: comment whose authorAssociation is MEMBER/OWNER/COLLABORATOR
  (association is as GitHub reports it at retrieval time, not at comment time).
- maintainer action: a non-bot, non-author account that labels, unlabels,
  closes, assigns, sets the issue type or marks a duplicate. Doing these to
  someone else's issue needs triage permission, so the actor is a triager.
- bot: GraphQL __typename Bot, or login ending in [bot], or github-actions.
- outside issue: author is not MEMBER/OWNER/COLLABORATOR and not a bot.
- first human response: earliest maintainer comment or maintainer action.
- bug form / gist at opening: fields in the reconstructed opening body, never a
  later edit or a bot label that may be delayed or missing.

Response-time summaries include only issues with an observed response. The 24-hour
and 7-day response rates include unanswered issues in their denominator. These are
descriptive workload measures, not estimates of time saved by the proposed agent.
"""
import csv
import re
import glob
import json
import pathlib
from collections import Counter
from datetime import datetime

HERE = pathlib.Path(__file__).resolve().parent
MAINT = {"MEMBER", "OWNER", "COLLABORATOR"}
# Manually identified triagers whose private org membership appears as CONTRIBUTOR.
# This fixed override is an analyst assumption, not something verified by this script.
WG_LOGINS = {"nmggithub", "georgexu99"}
ACTION_TYPES = {"LabeledEvent", "UnlabeledEvent", "ClosedEvent", "AssignedEvent",
                "IssueTypeAddedEvent", "MarkedAsDuplicateEvent"}


def parse_timestamp(value):
    """Parse GitHub's UTC timestamp into a timezone-aware datetime."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def is_bot(actor):
    """Exclude known bots and missing accounts from human-response counts."""
    if not actor:
        return True  # ghost / deleted
    login = actor.get("login", "")
    return actor.get("__typename") == "Bot" or login.endswith("[bot]") or login in {
        "github-actions", "electron-issue-triage"}


def hours(start, end):
    """Return elapsed hours between two timezone-aware timestamps."""
    return (end - start).total_seconds() / 3600


def quantile(values, probability):
    """Use linear interpolation; return None when no response times were observed."""
    values = sorted(values)
    if not values:
        return None
    position = (len(values) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    return round(values[lower] + (values[upper] - values[lower]) * (position - lower), 2)


def opening_form_fields(body):
    """Read form/gist facts from the opening revision supplied by the frozen corpus."""
    gist_section = re.search(
        r"^### Testcase Gist URL\s*\n(.*?)(?=^### |\Z)", body, re.M | re.S
    )
    gist = gist_section.group(1).strip() if gist_section else ""
    return {
        "bug_form": "### Electron Version" in body,
        "gist_at_open": bool(re.match(r"https://gist\.github\.com/\S+", gist)),
    }


def main():
    """Build one row per issue, then summarize the eligible outside-author cohort."""
    manifest = json.loads((HERE / "raw/issues_manifest.json").read_text())
    opening_issues = {
        issue["number"]: issue
        for issue in map(json.loads, (HERE.parent / "data/electron_issues.jsonl").read_text().splitlines())
    }
    rows = []
    for path in sorted(glob.glob(str(HERE / "raw/issues/*.json"))):
        rows += json.loads(pathlib.Path(path).read_text())["data"]["search"]["nodes"]

    table = []
    for issue in rows:
        author = (issue["author"] or {}).get("login")
        created = parse_timestamp(issue["createdAt"])
        outside = issue["authorAssociation"] not in MAINT and not is_bot(issue["author"]) and author not in WG_LOGINS
        events = issue["timelineItems"]["nodes"]
        labels_now = [l["name"] for l in issue["labels"]["nodes"]]

        human_times, comment_times = [], []
        for comment in issue["comments"]["nodes"]:
            if comment["author"] and not is_bot(comment["author"]) and comment["author"]["login"] != author \
                    and (comment["authorAssociation"] in MAINT or comment["author"]["login"] in WG_LOGINS):
                human_times.append(parse_timestamp(comment["createdAt"]))
                comment_times.append(parse_timestamp(comment["createdAt"]))
        label_first = {}   # label -> (time, actor_login, actor_is_bot)
        for event in events:
            event_type = event["__typename"]
            actor = event.get("actor")
            if event_type in ACTION_TYPES and actor and not is_bot(actor) and actor["login"] != author:
                human_times.append(parse_timestamp(event["createdAt"]))
            if event_type == "LabeledEvent":
                name = event["label"]["name"]
                if name not in label_first:
                    label_first[name] = (parse_timestamp(event["createdAt"]), (actor or {}).get("login"), is_bot(actor))

        first_human = min(human_times) if human_times else None
        first_comment = min(comment_times) if comment_times else None
        closes = [event for event in events if event["__typename"] == "ClosedEvent"]
        component_labels = {k: v for k, v in label_first.items() if k.startswith("component/")}
        human_component_labels = [v for v in component_labels.values() if not v[2]]
        template_closed = any(event["__typename"] == "ClosedEvent" and (event["actor"] or {}).get("login") == "github-actions"
                              for event in events) and "needs-template" in label_first
        # A missing opening record is an error: the later snapshot is not a safe fallback.
        opening_body = opening_issues[issue["number"]]["body"] or ""
        table.append({
            "number": issue["number"], "url": issue["url"], "title": issue["title"], "author": author,
            "assoc": issue["authorAssociation"], "outside": outside,
            "type": (issue["issueType"] or {}).get("name"),
            "created": issue["createdAt"], "state": issue["state"], "stateReason": issue["stateReason"],
            "closedAt": issue["closedAt"],
            "closed_by": (closes[-1]["actor"] or {}).get("login") if closes else None,
            "first_human_h": round(hours(created, first_human), 2) if first_human else None,
            "first_comment_h": round(hours(created, first_comment), 2) if first_comment else None,
            "n_maint_comments": len(comment_times),
            "n_comments": issue["comments"]["totalCount"],
            **opening_form_fields(opening_body),
            "template_closed": template_closed,
            "need_repro": "blocked/need-repro" in label_first,
            "need_repro_h": round(hours(created, label_first["blocked/need-repro"][0]), 2)
            if "blocked/need-repro" in label_first else None,
            "need_info": "blocked/need-info ❌" in label_first,
            "need_info_by_bot": label_first.get("blocked/need-info ❌", (0, 0, False))[2],
            "component_label": bool(component_labels),
            "component_by_human": bool(human_component_labels),
            "component_h": round(min(hours(created, v[0]) for v in component_labels.values()), 2) if component_labels else None,
            "platform_label": any(k.startswith("platform/") for k in label_first),
            "platform_by_human": any(k.startswith("platform/") and not v[2] for k, v in label_first.items()),
            "confirmed_or_reviewed": any(k in label_first for k in ("status/confirmed", "status/reviewed")),
            "triaged_h": round(min(hours(created, label_first[k][0]) for k in ("status/confirmed", "status/reviewed")
                                   if k in label_first), 2)
            if any(k in label_first for k in ("status/confirmed", "status/reviewed")) else None,
            "duplicate": issue["stateReason"] == "DUPLICATE" or "duplicate" in label_first
            or any(event["__typename"] == "MarkedAsDuplicateEvent" for event in events),
            "dup_comment": any((comment["authorAssociation"] in MAINT or (comment["author"] or {}).get("login") in WG_LOGINS)
                               and re.search(r"duplicate|same .* as #|in favou?r of|previous debugging work|potentially related", comment["body"] or "", re.I)
                               for comment in issue["comments"]["nodes"]),
            "closed_need_repro_bot": any(event["__typename"] == "ClosedEvent" and (event["actor"] or {}).get("login") == "electron-issue-triage"
                                         for event in events),
            "closed_with_pr": any(event["__typename"] == "ClosedEvent" and event.get("closer") and event["closer"].get("__typename") == "PullRequest"
                                  for event in events),
            "claude_xref": any(event["__typename"] == "CrossReferencedEvent" and (event["actor"] or {}).get("login") == "claude"
                               for event in events),
            "labels_now": "|".join(labels_now),
        })

    with open(HERE / "issues_table.csv", "w", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(table[0].keys()))
        writer.writeheader()
        writer.writerows(sorted(table, key=lambda x: x["number"]))

    outside_issues = [row for row in table if row["outside"]]
    # Cohort for response time: outside issues that were not auto-closed by the template bot
    eligible_issues = [row for row in outside_issues if not row["template_closed"]]
    bug_reports = [row for row in eligible_issues if row["bug_form"]]

    def pct(n, d):
        return f"{n}/{d} ({100 * n / d:.0f}%)" if d else "0/0"

    response_hours = [row["first_human_h"] for row in eligible_issues if row["first_human_h"] is not None]
    comment_hours = [row["first_comment_h"] for row in eligible_issues if row["first_comment_h"] is not None]
    # censoring-safe: response within 7 days, all issues have >= 23 days of follow-up
    within_seven_days = sum(1 for row in eligible_issues if row["first_human_h"] is not None and row["first_human_h"] <= 168)
    within_one_day = sum(1 for row in eligible_issues if row["first_human_h"] is not None and row["first_human_h"] <= 24)
    component_hours = [row["component_h"] for row in eligible_issues if row["component_h"] is not None]
    repro_hours = [row["need_repro_h"] for row in eligible_issues if row["need_repro_h"] is not None]
    triage_hours = [row["triaged_h"] for row in eligible_issues if row["triaged_h"] is not None]

    # who does the human triage labelling
    labelers = Counter()
    for issue in rows:
        author = (issue["author"] or {}).get("login")
        for event in issue["timelineItems"]["nodes"]:
            if event["__typename"] in ACTION_TYPES and event.get("actor") and not is_bot(event["actor"]) and event["actor"]["login"] != author:
                labelers[event["actor"]["login"]] += 1
    bot_labels = Counter()
    for issue in rows:
        for event in issue["timelineItems"]["nodes"]:
            if event["__typename"] == "LabeledEvent" and is_bot(event.get("actor")):
                bot_labels[event["label"]["name"]] += 1

    metrics = {
        "window": manifest["window"], "retrieved_at": manifest["retrieved_at"],
        "all_issues": len(table),
        "outside_issues": len(outside_issues),
        "maintainer_or_bot_issues": len(table) - len(outside_issues),
        "outside_template_closed": pct(sum(row["template_closed"] for row in outside_issues), len(outside_issues)),
        "live_outside_issues": len(eligible_issues),
        "live_bug_form": pct(len(bug_reports), len(eligible_issues)),
        "bug_form_with_gist_at_open": pct(sum(row["gist_at_open"] for row in bug_reports), len(bug_reports)),
        "first_human_response_hours": {"n": len(response_hours), "median": quantile(response_hours, .5), "p25": quantile(response_hours, .25), "p75": quantile(response_hours, .75), "p90": quantile(response_hours, .9)},
        "first_maintainer_comment_hours": {"n": len(comment_hours), "median": quantile(comment_hours, .5), "p75": quantile(comment_hours, .75)},
        "no_human_response_by_snapshot": pct(sum(row["first_human_h"] is None for row in eligible_issues), len(eligible_issues)),
        "no_maintainer_comment_by_snapshot": pct(sum(row["first_comment_h"] is None for row in eligible_issues), len(eligible_issues)),
        "human_response_within_24h": pct(within_one_day, len(eligible_issues)),
        "human_response_within_7d": pct(within_seven_days, len(eligible_issues)),
        "component_label_ever": pct(sum(row["component_label"] for row in eligible_issues), len(eligible_issues)),
        "component_label_hours": {"n": len(component_hours), "median": quantile(component_hours, .5), "p75": quantile(component_hours, .75)},
        "platform_label_ever": pct(sum(row["platform_label"] for row in eligible_issues), len(eligible_issues)),
        "platform_label_added_by_human": pct(sum(row["platform_by_human"] for row in eligible_issues), len(eligible_issues)),
        "need_repro_label": pct(sum(row["need_repro"] for row in eligible_issues), len(eligible_issues)),
        "need_repro_hours": {"n": len(repro_hours), "median": quantile(repro_hours, .5), "p75": quantile(repro_hours, .75)},
        "need_repro_of_bugs_without_gist": pct(sum(row["need_repro"] for row in bug_reports if not row["gist_at_open"]),
                                               sum(1 for row in bug_reports if not row["gist_at_open"])),
        "need_info_label": pct(sum(row["need_info"] for row in eligible_issues), len(eligible_issues)),
        "need_info_by_bot_unsupported_version": pct(sum(row["need_info_by_bot"] for row in eligible_issues), len(eligible_issues)),
        "closed_by_need_repro_or_stale_bot": pct(sum(row["closed_need_repro_bot"] for row in eligible_issues), len(eligible_issues)),
        "status_confirmed_or_reviewed": pct(sum(row["confirmed_or_reviewed"] for row in eligible_issues), len(eligible_issues)),
        "triage_status_hours": {"n": len(triage_hours), "median": quantile(triage_hours, .5), "p75": quantile(triage_hours, .75)},
        "duplicate_marked": pct(sum(row["duplicate"] for row in eligible_issues), len(eligible_issues)),
        "maintainer_comment_mentions_duplicate": pct(sum(row["dup_comment"] for row in eligible_issues), len(eligible_issues)),
        "closed_by_pr": pct(sum(row["closed_with_pr"] for row in eligible_issues), len(eligible_issues)),
        "claude_crossref": pct(sum(row["claude_xref"] for row in eligible_issues), len(eligible_issues)),
        "open_at_snapshot": pct(sum(row["state"] == "OPEN" for row in eligible_issues), len(eligible_issues)),
        "open_and_no_human_response": pct(sum(row["state"] == "OPEN" and row["first_human_h"] is None for row in eligible_issues), len(eligible_issues)),
        "human_triage_actions_by_actor": labelers.most_common(12),
        "human_triage_actions_total": sum(labelers.values()),
        "bot_labels_applied": bot_labels.most_common(25),
        "state_reason_live": Counter(f'{row["state"]}/{row["stateReason"]}' for row in eligible_issues).most_common(),
        "closed_by_live": Counter(row["closed_by"] for row in eligible_issues if row["closed_by"]).most_common(10),
    }
    (HERE / "issue_metrics.json").write_text(json.dumps(metrics, indent=1, ensure_ascii=False))
    print(json.dumps(metrics, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
