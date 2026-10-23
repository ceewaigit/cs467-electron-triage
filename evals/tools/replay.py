#!/usr/bin/env python3
"""Replay the golden cases in the sandbox repository and collect what the agent did.

    python3 evals/tools/replay.py labels                 # create the labels the cases use
    python3 evals/tools/replay.py file --k 3             # one sandbox issue per case per run
    python3 evals/tools/replay.py dispatch               # start the workflow for each issue
    python3 evals/tools/replay.py collect                # wait, then write actual/agent/run-*.json

`--variant obey` runs the control workflow (issue-triage-obey, which tells the model to obey the
issue text) on its own sandbox issues and writes actual/obey/ instead. `--variant agent-v2`
re-runs the main workflow after the repo-link fix and writes actual/agent-v2/.

Every run gets its own sandbox issue, so a later run never sees the labels or comment of an
earlier one. Sandbox issues are filed by the repository owner; the live `issues: opened` run
that this triggers must be skipped (owner), and `collect` records that as a control test.
The replay itself uses workflow_dispatch with the original opening time and author association.

Issue bodies are neutralised before filing so nothing reaches another repository:
  @user                          -> @<zero-width space>user   (no notification)
  github.com/o/r/issues/N, pull  -> `o/r#N` in a code span    (no cross-reference)
  o/r#N                          -> `o/r#N`
The text the agent saw is saved in replay/issues.json next to the original.

`--cases e52232,a1-close-stale` limits any step to some cases. Needs `gh` logged in as the owner.
"""
import argparse
import datetime as dt
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "evals" / "golden"
STATE = GOLDEN / "replay"
REPO = "ceewaigit/cs467-electron-triage"
# agent-v2: the same workflow after the triage_checks repo-link fix, re-run on the affected cases.
# final: the submitted configuration (template-only comments via the triage-comment job).
WORKFLOWS = {"agent": "issue-triage.lock.yml", "agent-v2": "issue-triage.lock.yml",
             "final": "issue-triage.lock.yml", "obey": "issue-triage-obey.lock.yml"}
BOT = "github-actions[bot]"
VARIANT, WORKFLOW = "agent", WORKFLOWS["agent"]
KEEP_LOGS = ("aw_info.json", "agent_output.json", "safe_output.jsonl", "skill_inventory.json",
             "agent-stdio.log", "agent-session.jsonl", "prompt.txt", "detection.log")


def gh(*args, input=None, check=True):
    p = subprocess.run(["gh", *args], capture_output=True, text=True, input=input)
    if check and p.returncode:
        sys.exit(f"gh {' '.join(args[:3])} failed: {p.stderr.strip()}")
    return p.stdout


def api(path, *args, method="GET", paginate=False):
    extra = ["--paginate", "--slurp"] if paginate else []
    out = gh("api", "-X", method, path, *extra, *args)
    data = json.loads(out) if out.strip() else None
    return [x for page in data for x in page] if paginate else data


def neutralise(text):
    text = re.sub(r"https?://(?:www\.)?github\.com/([\w.-]+)/([\w.-]+)/(?:issues|pull|discussions)/(\d+)[^\s)\]>]*",
                  r"`\1/\2#\3`", text)
    text = re.sub(r"(?<![\w/`])([\w.-]+/[\w.-]+#\d+)", r"`\1`", text)
    return re.sub(r"(?<![\w`])@([A-Za-z0-9][\w-]*)", "@​\\1", text)


def cases(selected):
    out = []
    for d in sorted((GOLDEN / "cases").iterdir()):
        if not selected or d.name in selected:
            out.append((d.name, json.loads((d / "input.json").read_text())))
    return out


def load(name, default):
    p = STATE / name.replace(".json", f"-{VARIANT}.json")
    return json.loads(p.read_text()) if p.exists() else default


def save(name, data):
    STATE.mkdir(exist_ok=True)
    (STATE / name.replace(".json", f"-{VARIANT}.json")).write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")


def cmd_labels(a):
    allowed = (ROOT / ".claude/skills/issue-triage/assets/allowed-labels.txt").read_text().split("\n")
    meta = {l["name"]: l for l in json.loads((ROOT / "data" / "labels.json").read_text())}
    wanted = {l for l in allowed if l} | {l for _, c in cases(a.cases) for l in c["labels_at_open"]}
    have = {l["name"] for l in api(f"repos/{REPO}/labels", paginate=True)}
    for name in sorted(wanted - have):
        m = meta.get(name, {})
        api(f"repos/{REPO}/labels", "-f", f"name={name}", "-f", f"color={m.get('color', 'ededed')}",
            "-f", f"description={(m.get('description') or '')[:100]}", method="POST")
        print("created label", name)


def cmd_file(a):
    issues = load("issues.json", {})
    for cid, c in cases(a.cases):
        entry = issues.setdefault(cid, {"title": neutralise(c["title"]), "body": neutralise(c["body"]),
                                        "labels_at_open": c["labels_at_open"], "issues": []})
        while len(entry["issues"]) < a.k:
            args = ["-f", f"title={entry['title']}", "-f", f"body={entry['body']}"]
            for lab in entry["labels_at_open"]:
                args += ["-f", f"labels[]={lab}"]
            n = api(f"repos/{REPO}/issues", *args, method="POST")["number"]
            entry["issues"].append(n)
            save("issues.json", issues)
            print(f"{cid}: filed #{n}")
            time.sleep(2)  # stay under GitHub's content-creation rate limit


def cmd_dispatch(a):
    issues, runs = load("issues.json", {}), load("runs.json", {})
    for cid, c in cases(a.cases):
        for k, n in enumerate(issues.get(cid, {}).get("issues", [])[:a.k], 1):
            key = str(n)
            if key in runs:
                continue
            seen = {r["databaseId"] for r in json.loads(gh(
                "run", "list", "-R", REPO, "-w", WORKFLOW, "-e", "workflow_dispatch", "-L", "20",
                "--json", "databaseId"))}
            gh("workflow", "run", WORKFLOW, "-R", REPO, "-f", f"issue_number={n}",
               "-f", f"as_of={c['as_of']}", "-f", f"author_association={c['author_association']}")
            for _ in range(30):
                time.sleep(3)
                new = [r for r in json.loads(gh("run", "list", "-R", REPO, "-w", WORKFLOW, "-e",
                       "workflow_dispatch", "-L", "20", "--json", "databaseId"))
                       if r["databaseId"] not in seen]
                if new:
                    break
            else:
                sys.exit(f"no run appeared for #{n}")
            runs[key] = {"case": cid, "run": k, "run_id": new[0]["databaseId"],
                         "dispatched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
            save("runs.json", runs)
            print(f"{cid} run {k}: issue #{n} -> run {new[0]['databaseId']}")


def outcome(n, labels_at_open):
    """What happened to sandbox issue n, read back from GitHub itself."""
    events = api(f"repos/{REPO}/issues/{n}/timeline", "-H", "Accept: application/vnd.github+json",
                 paginate=True)
    labels, comments, other = [], [], []
    for e in events:
        actor = (e.get("actor") or e.get("user") or {}).get("login")
        kind = e.get("event")
        if actor != BOT:
            if kind in ("labeled",) and e["label"]["name"] in labels_at_open:
                continue
            if kind not in ("labeled", "commented", "cross-referenced", "mentioned", "subscribed"):
                other.append(f"{kind} by {actor}")
            continue
        if kind == "labeled":
            labels.append(e["label"]["name"])
        elif kind == "commented":
            comments.append(e["body"])
        else:
            other.append(f"{kind} by {BOT}")
    if len(comments) > 1:
        other.append(f"{len(comments)} comments")
    state = api(f"repos/{REPO}/issues/{n}")["state"]
    if state != "open":
        other.append(f"issue state {state}")
    return {"labels_added": labels, "comment": comments[-1] if comments else None, "other_writes": other}


def cmd_collect(a):
    issues, runs = load("issues.json", {}), load("runs.json", {})
    selected = {cid for cid, _ in cases(a.cases)}
    live = load("live-skips.json", {})
    for key, r in sorted(runs.items(), key=lambda kv: (kv[1]["case"], kv[1]["run"])):
        if r["case"] not in selected:
            continue
        out_dir = GOLDEN / "cases" / r["case"] / "actual" / VARIANT
        dest = out_dir / f"run-{r['run']}.json"
        if dest.exists() and not a.force:
            continue
        while True:
            v = json.loads(gh("run", "view", str(r["run_id"]), "-R", REPO, "--json", "status,conclusion"))
            if v["status"] == "completed":
                break
            print(f"waiting for run {r['run_id']} ({v['status']})")
            time.sleep(20)
        result = outcome(int(key), issues[r["case"]]["labels_at_open"])
        result |= {"issue": int(key), "run_id": r["run_id"], "conclusion": v["conclusion"],
                   "run_url": f"https://github.com/{REPO}/actions/runs/{r['run_id']}"}
        out_dir.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n")
        logs = out_dir / "logs" / f"run-{r['run']}"
        with tempfile.TemporaryDirectory() as tmp:
            gh("run", "download", str(r["run_id"]), "-R", REPO, "-D", tmp, check=False)
            for f in pathlib.Path(tmp).rglob("*"):
                if f.is_file() and f.name in KEEP_LOGS:
                    logs.mkdir(parents=True, exist_ok=True)
                    shutil.copy(f, logs / f.name)
        print(f"{r['case']} run {r['run']}: {v['conclusion']} labels={result['labels_added']} "
              f"comment={'yes' if result['comment'] else 'no'} other={result['other_writes']}")
    # The issues: opened run each sandbox issue triggered must have been skipped (owner).
    pending = [(cid, entry, n) for cid, entry in issues.items() for n in entry["issues"] if str(n) not in live]
    if pending:
        all_runs = json.loads(gh("run", "list", "-R", REPO, "-w", WORKFLOWS["agent"], "-e", "issues",
                                 "-L", "500", "--json", "databaseId,conclusion,displayTitle"))
        for cid, entry, n in pending:
            found = [x for x in all_runs if x["displayTitle"] == entry["title"]]
            live[str(n)] = {"case": cid, "runs": [(x["databaseId"], x["conclusion"]) for x in found]}
    save("live-skips.json", live)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["labels", "file", "dispatch", "collect"])
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--cases", type=lambda s: set(s.split(",")), default=None)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--variant", choices=sorted(WORKFLOWS), default="agent")
    a = ap.parse_args()
    global VARIANT, WORKFLOW
    VARIANT, WORKFLOW = a.variant, WORKFLOWS[a.variant]
    {"labels": cmd_labels, "file": cmd_file, "dispatch": cmd_dispatch, "collect": cmd_collect}[a.step](a)


if __name__ == "__main__":
    main()
