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
The default variant is the historical name `agent`; use `--variant final` for
the template-only workflow. The variant selects filenames, not a Git revision:
dispatch runs the default branch unless --ref selects a branch or tag. New
run records retain the requested ref and GitHub's actual head SHA/branch.
Dispatch requires exclusive use of this workflow's manual trigger while the
helper runs. The run list does not expose the issue-number input: matching a
branch cannot distinguish one concurrent manual run on that same branch.

Collection keeps successful executions in actual/<variant>/run-N.json. Failed,
cancelled or skipped executions go in actual/<variant>/failures/ with their own
logs, so the scorer cannot mistake a billing failure for a correct no-action
decision. Observed actions are retained in both kinds of record for audit.
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
# final: the historical template-only configuration; hardened: the audited successor.
WORKFLOWS = {"agent": "issue-triage.lock.yml", "agent-v2": "issue-triage.lock.yml",
             "final": "issue-triage.lock.yml", "hardened": "issue-triage.lock.yml",
             "obey": "issue-triage-obey.lock.yml"}
BOT = "github-actions[bot]"
VARIANT, WORKFLOW = "agent", WORKFLOWS["agent"]
KEEP_LOGS = ("aw_info.json", "agent_output.json", "safe_output.jsonl", "skill_inventory.json",
             "agent-stdio.log", "agent-session.jsonl", "agent-errors.jsonl", "prompt.txt", "detection.log")


def gh(*args, input=None, check=True):
    """Run the GitHub CLI and stop on failure unless the caller allows a missing artifact."""
    p = subprocess.run(["gh", *args], capture_output=True, text=True, input=input)
    if check and p.returncode:
        sys.exit(f"gh {' '.join(args[:3])} failed: {p.stderr.strip()}")
    return p.stdout


def api(path, *args, method="GET", paginate=False):
    """Decode one REST response, or flatten all pages into one list."""
    extra = ["--paginate", "--slurp"] if paginate else []
    out = gh("api", "-X", method, path, *extra, *args)
    data = json.loads(out) if out.strip() else None
    return [x for page in data for x in page] if paginate else data


def neutralise(text):
    """Keep issue references readable while preventing mentions and cross-repository notifications."""
    text = re.sub(r"https?://(?:www\.)?github\.com/([\w.-]+)/([\w.-]+)/(?:issues|pull|discussions)/(\d+)[^\s)\]>]*",
                  r"`\1/\2#\3`", text)
    text = re.sub(r"(?<![\w/`])([\w.-]+/[\w.-]+#\d+)", r"`\1`", text)
    return re.sub(r"(?<![\w`])@([A-Za-z0-9][\w-]*)", "@​\\1", text)


def cases(selected):
    """Read the selected golden inputs in a stable order."""
    out = []
    for d in sorted((GOLDEN / "cases").iterdir()):
        if not selected or d.name in selected:
            out.append((d.name, json.loads((d / "input.json").read_text())))
    return out


def load(name, default):
    """Read replay state for this variant, or return the supplied initial value."""
    p = STATE / name.replace(".json", f"-{VARIANT}.json")
    return json.loads(p.read_text()) if p.exists() else default


def save(name, data):
    """Persist variant-specific replay state after each successful remote operation."""
    STATE.mkdir(exist_ok=True)
    (STATE / name.replace(".json", f"-{VARIANT}.json")).write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")


def cmd_labels(a):
    """Create missing sandbox labels from the allowlist and opening issue labels."""
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
    """Create one independent sandbox issue per repetition and save its issue number."""
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
    """Dispatch each unrecorded repetition and associate it with the newly appearing run."""
    issues, runs = load("issues.json", {}), load("runs.json", {})
    requested_ref = getattr(a, "ref", None)
    expected_branch = (requested_ref.removeprefix("refs/heads/").removeprefix("refs/tags/")
                       if requested_ref else api(f"repos/{REPO}")["default_branch"])
    for cid, c in cases(a.cases):
        for k, n in enumerate(issues.get(cid, {}).get("issues", [])[:a.k], 1):
            key = str(n)
            if key in runs:
                continue
            seen = {r["databaseId"] for r in json.loads(gh(
                "run", "list", "-R", REPO, "-w", WORKFLOW, "-e", "workflow_dispatch", "-L", "20",
                "--json", "databaseId"))}
            ref_args = ["--ref", requested_ref] if requested_ref else []
            gh("workflow", "run", WORKFLOW, "-R", REPO, *ref_args, "-f", f"issue_number={n}",
               "-f", f"as_of={c['as_of']}", "-f", f"author_association={c['author_association']}")
            for _ in range(30):
                time.sleep(3)
                new = [r for r in json.loads(gh("run", "list", "-R", REPO, "-w", WORKFLOW, "-e",
                       "workflow_dispatch", "-L", "20", "--json", "databaseId,headSha,headBranch"))
                       if r["databaseId"] not in seen]
                matching = [run for run in new if run["headBranch"] == expected_branch]
                if len(matching) > 1:
                    sys.exit(f"multiple new runs on {expected_branch!r}; cannot safely pair issue #{n}. "
                             "No association was saved. Inspect the dispatched runs before retrying, "
                             "and use only one dispatcher at a time.")
                if matching:
                    break
            else:
                sys.exit(f"no run on {expected_branch!r} appeared for #{n}; inspect GitHub before retrying")
            matched = matching[0]
            runs[key] = {"case": cid, "run": k, "run_id": matched["databaseId"],
                         "requested_ref": requested_ref, "head_sha": matched["headSha"],
                         "head_branch": matched["headBranch"],
                         "dispatched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
            save("runs.json", runs)
            print(f"{cid} run {k}: issue #{n} -> run {matched['databaseId']}")


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
    """Separate completed model evaluations from execution failures before scoring."""
    issues, runs = load("issues.json", {}), load("runs.json", {})
    selected = {cid for cid, _ in cases(a.cases)}
    live = load("live-skips.json", {})
    for key, r in sorted(runs.items(), key=lambda kv: (kv[1]["case"], kv[1]["run"])):
        if r["case"] not in selected:
            continue
        out_dir = GOLDEN / "cases" / r["case"] / "actual" / VARIANT
        dest = out_dir / f"run-{r['run']}.json"
        failure_dest = out_dir / "failures" / dest.name
        if (dest.exists() or failure_dest.exists()) and not a.force:
            continue
        while True:
            v = json.loads(gh("run", "view", str(r["run_id"]), "-R", REPO, "--json",
                              "status,conclusion,headSha,headBranch"))
            if v["status"] == "completed":
                break
            print(f"waiting for run {r['run_id']} ({v['status']})")
            time.sleep(20)
        # --force may refresh evidence within one category, but cannot turn a
        # previously scored result into a failure (or the reverse) in place.
        # Refuse before touching either record or its logs.
        conflicting = failure_dest if v["conclusion"] == "success" else dest
        if conflicting.exists():
            sys.exit(f"refusing conflicting evidence for {r['case']} run {r['run']}: "
                     f"{conflicting} already exists, but GitHub now reports {v['conclusion']}. "
                     "Existing records and logs were left unchanged. Use a fresh experiment "
                     "namespace and fresh sandbox issues instead of --force.")
        result = outcome(int(key), issues[r["case"]]["labels_at_open"])
        result |= {"issue": int(key), "run_id": r["run_id"], "conclusion": v["conclusion"],
                   "requested_ref": r.get("requested_ref"), "head_sha": v["headSha"],
                   "head_branch": v["headBranch"],
                   "run_url": f"https://github.com/{REPO}/actions/runs/{r['run_id']}"}
        # An unsuccessful execution has no valid decision to score, even when
        # the expected decision was to do nothing. Preserve any partial writes.
        if v["conclusion"] != "success":
            result |= {"scored": False,
                       "exclusion_reason": "Unsuccessful workflow execution; no valid triage result."}
            dest = failure_dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n")
        logs = dest.parent / "logs" / f"run-{r['run']}"
        with tempfile.TemporaryDirectory() as tmp:
            gh("run", "download", str(r["run_id"]), "-R", REPO, "-D", tmp, check=False)
            for f in pathlib.Path(tmp).rglob("*"):
                if f.is_file() and f.name in KEEP_LOGS:
                    logs.mkdir(parents=True, exist_ok=True)
                    shutil.copy(f, logs / f.name)
        print(f"{r['case']} run {r['run']}: {v['conclusion']} labels={result['labels_added']} "
              f"comment={'yes' if result['comment'] else 'no'} other={result['other_writes']} "
              f"{'(excluded from scoring)' if v['conclusion'] != 'success' else ''}")
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
    """Select a replay variant and execute one explicit stage of its lifecycle."""
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["labels", "file", "dispatch", "collect"])
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--cases", type=lambda s: set(s.split(",")), default=None)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--variant", choices=sorted(WORKFLOWS), default="agent")
    ap.add_argument("--ref", help="Branch or tag to dispatch; defaults to the repository's default branch")
    a = ap.parse_args()
    global VARIANT, WORKFLOW
    VARIANT, WORKFLOW = a.variant, WORKFLOWS[a.variant]
    {"labels": cmd_labels, "file": cmd_file, "dispatch": cmd_dispatch, "collect": cmd_collect}[a.step](a)


if __name__ == "__main__":
    main()
