#!/usr/bin/env python3
"""Triage-need metrics for electron/electron issues opened 1 Jul - 30 Sep 2026.

Reads raw/issues/*.json (from fetch_issues.py) and writes issue_metrics.json
plus a per-issue table issues_table.csv. Read-only; no network.

Definitions
- maintainer comment: comment whose authorAssociation is MEMBER/OWNER/COLLABORATOR
  (association is as GitHub reports it at retrieval time, not at comment time).
- maintainer action: a non-bot, non-author account that labels, unlabels,
  closes, assigns, sets the issue type or marks a duplicate. Doing these to
  someone else's issue needs triage permission, so the actor is a triager.
- bot: GraphQL __typename Bot, or login ending in [bot], or github-actions.
- outside issue: author is not MEMBER/OWNER/COLLABORATOR and not a bot.
- first human response: earliest maintainer comment or maintainer action.
"""
import csv
import re
import glob
import json
import pathlib
import statistics as st
from datetime import datetime, timezone

HERE = pathlib.Path(__file__).resolve().parent
MAINT = {"MEMBER", "OWNER", "COLLABORATOR"}
# Working-group members with private org membership (show as CONTRIBUTOR); see A2 report Appendix B.
WG_LOGINS = {"nmggithub", "georgexu99"}
ACTION_TYPES = {"LabeledEvent", "UnlabeledEvent", "ClosedEvent", "AssignedEvent",
                "IssueTypeAddedEvent", "MarkedAsDuplicateEvent"}


def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def is_bot(actor):
    if not actor:
        return True  # ghost / deleted
    login = actor.get("login", "")
    return actor.get("__typename") == "Bot" or login.endswith("[bot]") or login in {
        "github-actions", "electron-issue-triage"}


def hours(a, b):
    return (b - a).total_seconds() / 3600


def q(vals, p):
    vals = sorted(vals)
    if not vals:
        return None
    k = (len(vals) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(vals) - 1)
    return round(vals[lo] + (vals[hi] - vals[lo]) * (k - lo), 2)


def main():
    manifest = json.loads((HERE / "raw/issues_manifest.json").read_text())
    snap = ts(manifest["retrieved_at"])
    rows = []
    for f in sorted(glob.glob(str(HERE / "raw/issues/*.json"))):
        rows += json.loads(pathlib.Path(f).read_text())["data"]["search"]["nodes"]

    table = []
    for r in rows:
        author = (r["author"] or {}).get("login")
        created = ts(r["createdAt"])
        outside = r["authorAssociation"] not in MAINT and not is_bot(r["author"]) and author not in WG_LOGINS
        ev = r["timelineItems"]["nodes"]
        labels_now = [l["name"] for l in r["labels"]["nodes"]]

        human_times, comment_times = [], []
        for c in r["comments"]["nodes"]:
            if c["author"] and not is_bot(c["author"]) and c["author"]["login"] != author \
                    and (c["authorAssociation"] in MAINT or c["author"]["login"] in WG_LOGINS):
                human_times.append(ts(c["createdAt"]))
                comment_times.append(ts(c["createdAt"]))
        label_first = {}   # label -> (time, actor_login, actor_is_bot)
        for e in ev:
            t = e["__typename"]
            a = e.get("actor")
            if t in ACTION_TYPES and a and not is_bot(a) and a["login"] != author:
                human_times.append(ts(e["createdAt"]))
            if t == "LabeledEvent":
                name = e["label"]["name"]
                if name not in label_first:
                    label_first[name] = (ts(e["createdAt"]), (a or {}).get("login"), is_bot(a))

        first_h = min(human_times) if human_times else None
        first_c = min(comment_times) if comment_times else None
        closes = [e for e in ev if e["__typename"] == "ClosedEvent"]
        comp = {k: v for k, v in label_first.items() if k.startswith("component/")}
        comp_human = [v for v in comp.values() if not v[2]]
        template_closed = any(e["__typename"] == "ClosedEvent" and (e["actor"] or {}).get("login") == "github-actions"
                              for e in ev) and "needs-template" in label_first
        body = r["body"] or ""
        table.append({
            "number": r["number"], "url": r["url"], "title": r["title"], "author": author,
            "assoc": r["authorAssociation"], "outside": outside,
            "type": (r["issueType"] or {}).get("name"),
            "created": r["createdAt"], "state": r["state"], "stateReason": r["stateReason"],
            "closedAt": r["closedAt"],
            "closed_by": (closes[-1]["actor"] or {}).get("login") if closes else None,
            "first_human_h": round(hours(created, first_h), 2) if first_h else None,
            "first_comment_h": round(hours(created, first_c), 2) if first_c else None,
            "n_maint_comments": len(comment_times),
            "n_comments": r["comments"]["totalCount"],
            "bug_form": "### Electron Version" in body,
            "gist_at_open": "has-repro-gist" in label_first and label_first["has-repro-gist"][2],
            "template_closed": template_closed,
            "need_repro": "blocked/need-repro" in label_first,
            "need_repro_h": round(hours(created, label_first["blocked/need-repro"][0]), 2)
            if "blocked/need-repro" in label_first else None,
            "need_info": "blocked/need-info ❌" in label_first,
            "need_info_by_bot": label_first.get("blocked/need-info ❌", (0, 0, False))[2],
            "component_label": bool(comp),
            "component_by_human": bool(comp_human),
            "component_h": round(min(hours(created, v[0]) for v in comp.values()), 2) if comp else None,
            "platform_label": any(k.startswith("platform/") for k in label_first),
            "platform_by_human": any(k.startswith("platform/") and not v[2] for k, v in label_first.items()),
            "confirmed_or_reviewed": any(k in label_first for k in ("status/confirmed", "status/reviewed")),
            "triaged_h": round(min(hours(created, label_first[k][0]) for k in ("status/confirmed", "status/reviewed")
                                   if k in label_first), 2)
            if any(k in label_first for k in ("status/confirmed", "status/reviewed")) else None,
            "duplicate": r["stateReason"] == "DUPLICATE" or "duplicate" in label_first
            or any(e["__typename"] == "MarkedAsDuplicateEvent" for e in ev),
            "dup_comment": any((c["authorAssociation"] in MAINT or (c["author"] or {}).get("login") in WG_LOGINS)
                               and re.search(r"duplicate|same .* as #|in favou?r of|previous debugging work|potentially related", c["body"] or "", re.I)
                               for c in r["comments"]["nodes"]),
            "closed_need_repro_bot": any(e["__typename"] == "ClosedEvent" and (e["actor"] or {}).get("login") == "electron-issue-triage"
                                         for e in ev),
            "closed_with_pr": any(e["__typename"] == "ClosedEvent" and e.get("closer") and e["closer"].get("__typename") == "PullRequest"
                                  for e in ev),
            "claude_xref": any(e["__typename"] == "CrossReferencedEvent" and (e["actor"] or {}).get("login") == "claude"
                               for e in ev),
            "labels_now": "|".join(labels_now),
        })

    with open(HERE / "issues_table.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(table[0].keys()))
        w.writeheader()
        w.writerows(sorted(table, key=lambda x: x["number"]))

    out = [t for t in table if t["outside"]]
    # Cohort for response time: outside issues that were not auto-closed by the template bot
    live = [t for t in out if not t["template_closed"]]
    bugs = [t for t in live if t["bug_form"]]

    def pct(n, d):
        return f"{n}/{d} ({100 * n / d:.0f}%)" if d else "0/0"

    fh = [t["first_human_h"] for t in live if t["first_human_h"] is not None]
    fc = [t["first_comment_h"] for t in live if t["first_comment_h"] is not None]
    # censoring-safe: response within 7 days, all issues have >= 23 days of follow-up
    within7 = sum(1 for t in live if t["first_human_h"] is not None and t["first_human_h"] <= 168)
    within1 = sum(1 for t in live if t["first_human_h"] is not None and t["first_human_h"] <= 24)
    comp_h = [t["component_h"] for t in live if t["component_h"] is not None]
    nr_h = [t["need_repro_h"] for t in live if t["need_repro_h"] is not None]
    tri_h = [t["triaged_h"] for t in live if t["triaged_h"] is not None]

    # who does the human triage labelling
    from collections import Counter
    labelers = Counter()
    for r in rows:
        author = (r["author"] or {}).get("login")
        for e in r["timelineItems"]["nodes"]:
            if e["__typename"] in ACTION_TYPES and e.get("actor") and not is_bot(e["actor"]) and e["actor"]["login"] != author:
                labelers[e["actor"]["login"]] += 1
    bot_labels = Counter()
    for r in rows:
        for e in r["timelineItems"]["nodes"]:
            if e["__typename"] == "LabeledEvent" and is_bot(e.get("actor")):
                bot_labels[e["label"]["name"]] += 1

    m = {
        "window": manifest["window"], "retrieved_at": manifest["retrieved_at"],
        "all_issues": len(table),
        "outside_issues": len(out),
        "maintainer_or_bot_issues": len(table) - len(out),
        "outside_template_closed": pct(sum(t["template_closed"] for t in out), len(out)),
        "live_outside_issues": len(live),
        "live_bug_form": pct(len(bugs), len(live)),
        "bug_form_with_gist_at_open": pct(sum(t["gist_at_open"] for t in bugs), len(bugs)),
        "first_human_response_hours": {"n": len(fh), "median": q(fh, .5), "p25": q(fh, .25), "p75": q(fh, .75), "p90": q(fh, .9)},
        "first_maintainer_comment_hours": {"n": len(fc), "median": q(fc, .5), "p75": q(fc, .75)},
        "no_human_response_by_snapshot": pct(sum(t["first_human_h"] is None for t in live), len(live)),
        "no_maintainer_comment_by_snapshot": pct(sum(t["first_comment_h"] is None for t in live), len(live)),
        "human_response_within_24h": pct(within1, len(live)),
        "human_response_within_7d": pct(within7, len(live)),
        "component_label_ever": pct(sum(t["component_label"] for t in live), len(live)),
        "component_label_hours": {"n": len(comp_h), "median": q(comp_h, .5), "p75": q(comp_h, .75)},
        "platform_label_ever": pct(sum(t["platform_label"] for t in live), len(live)),
        "platform_label_added_by_human": pct(sum(t["platform_by_human"] for t in live), len(live)),
        "need_repro_label": pct(sum(t["need_repro"] for t in live), len(live)),
        "need_repro_hours": {"n": len(nr_h), "median": q(nr_h, .5), "p75": q(nr_h, .75)},
        "need_repro_of_bugs_without_gist": pct(sum(t["need_repro"] for t in bugs if not t["gist_at_open"]),
                                               sum(1 for t in bugs if not t["gist_at_open"])),
        "need_info_label": pct(sum(t["need_info"] for t in live), len(live)),
        "need_info_by_bot_unsupported_version": pct(sum(t["need_info_by_bot"] for t in live), len(live)),
        "closed_by_need_repro_or_stale_bot": pct(sum(t["closed_need_repro_bot"] for t in live), len(live)),
        "status_confirmed_or_reviewed": pct(sum(t["confirmed_or_reviewed"] for t in live), len(live)),
        "triage_status_hours": {"n": len(tri_h), "median": q(tri_h, .5), "p75": q(tri_h, .75)},
        "duplicate_marked": pct(sum(t["duplicate"] for t in live), len(live)),
        "maintainer_comment_mentions_duplicate": pct(sum(t["dup_comment"] for t in live), len(live)),
        "closed_by_pr": pct(sum(t["closed_with_pr"] for t in live), len(live)),
        "claude_crossref": pct(sum(t["claude_xref"] for t in live), len(live)),
        "open_at_snapshot": pct(sum(t["state"] == "OPEN" for t in live), len(live)),
        "open_and_no_human_response": pct(sum(t["state"] == "OPEN" and t["first_human_h"] is None for t in live), len(live)),
        "human_triage_actions_by_actor": labelers.most_common(12),
        "human_triage_actions_total": sum(labelers.values()),
        "bot_labels_applied": bot_labels.most_common(25),
        "state_reason_live": Counter(f'{t["state"]}/{t["stateReason"]}' for t in live).most_common(),
        "closed_by_live": Counter(t["closed_by"] for t in live if t["closed_by"]).most_common(10),
    }
    (HERE / "issue_metrics.json").write_text(json.dumps(m, indent=1, ensure_ascii=False))
    print(json.dumps(m, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
