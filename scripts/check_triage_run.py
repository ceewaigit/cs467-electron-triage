#!/usr/bin/env python3
"""Alert the owner when a finished triage run's requested writes are not on its issue.

Run by .github/workflows/triage-watchdog.yml after every triage run. No model is involved.
Environment: GH_TOKEN, REPO, RUN_ID, optional ISSUE (else read from the run title
"Issue triage #N"), ALERT_ASSIGNEE and GITHUB_STEP_SUMMARY.

An issue can miss its first pass in three ways: the run fails (for example, provider credit
runs out), the daily credit cap skips the agent, or the run succeeds while gh-aw withholds
its labels because threat detection reached no verdict (evals/golden/results/delivery-final.md).
This script opens one alert issue, assigned to the owner, for each failed run or lost write;
issues skipped by the cap are listed on one open issue, the list for the manual sweep.
Reported without an alert: a reviewer's rejection, a cancelled run, and labels below HIGH
confidence that GitHub keeps as suggestions, which is the intended hold for a maintainer.
Exit status 1 means an alert was raised, so the watchdog run also shows as failed.
"""
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

BOT = "github-actions[bot]"
CAP_SKIP = "The daily credit cap skipped the agent, so this issue has had no first pass."
CAP_SKIP_TITLE = "Issues skipped by the daily credit cap"


def gh(*args, check=True):
    """Run the GitHub CLI and return its standard output."""
    p = subprocess.run(["gh", *args], capture_output=True, text=True)
    if check and p.returncode:
        sys.exit(f"gh {' '.join(args[:3])} failed: {p.stderr.strip()}")
    return p.stdout


def api(path, *args):
    """Decode one REST response, flattening paginated lists."""
    out = gh("api", path, "--paginate", "--slurp", *args)
    pages = json.loads(out)
    return [x for page in pages for x in page] if isinstance(pages[0], list) else pages[0]


def artifact_json(repo, run_id, artifact, filename):
    """Read one JSON file from a run artifact, or None when the artifact or file is absent."""
    with tempfile.TemporaryDirectory() as tmp:
        gh("run", "download", str(run_id), "-R", repo, "-n", artifact, "-D", tmp, check=False)
        found = sorted(pathlib.Path(tmp).rglob(filename))
        return json.loads(found[0].read_text()) if found else None


def requested_writes(agent_output):
    """Labels (name to confidence, None if unset) and comment the agent asked for."""
    labels, comment = {}, False
    for item in (agent_output or {}).get("items", []):
        if item.get("type") == "add_labels":
            for label in item.get("labels", []):
                name, confidence = (label, None) if isinstance(label, str) else (label["name"], label.get("confidence"))
                labels[name] = confidence
        elif item.get("type") == "triage_comment":
            comment = True
    return labels, comment


def check(run, jobs, approvals, agent_output, detection, issue_labels, comments):
    """Return (problems, notes) for one finished run; problems mean the owner must look.

    `jobs` maps job name to conclusion.
    """
    conclusion = run.get("conclusion")
    problems, notes = [], [f"Run conclusion: {conclusion}."]
    if any(a.get("state") == "rejected" for a in approvals):
        notes.append("A reviewer rejected the run in `triage-writes`; nothing was expected to land.")
        return problems, notes
    if conclusion == "cancelled":
        notes.append("The run was cancelled; nothing was expected to land.")
        return problems, notes
    if conclusion == "failure":
        problems.append("The run failed, so this issue may have had no first pass. Rerun it or triage by hand.")
    if jobs.get("agent") in ("skipped", None):
        # Activation runs only after pre_activation admits the issue, so a skip after it is the
        # daily cap. A maintainer's own issue stops at pre_activation and needs nothing.
        if conclusion == "success" and jobs.get("activation") == "success":
            problems.append(CAP_SKIP)
        notes.append("The agent job did not run, so no writes were requested.")
        return problems, notes
    if agent_output is None:
        if conclusion == "success":
            problems.append("The run succeeded but left no agent output to check.")
        return problems, notes
    labels, comment = requested_writes(agent_output)
    missing = [label for label in labels if label not in issue_labels]
    # A clean verdict means gh-aw sent the labels, so a missing one below HIGH is GitHub's hold.
    verdict_clean = detection is not None and not any(
        detection.get(k) for k in ("prompt_injection", "secret_leak", "malicious_patch"))
    suggested = [label for label in missing if verdict_clean and labels[label] not in (None, "HIGH")]
    withheld = [label for label in missing if label not in suggested]
    if suggested:
        notes.append("Held by GitHub as suggestions for a maintainer: "
                     + ", ".join(f"`{label}`" for label in suggested) + ".")
    if withheld:
        problems.append("Requested labels are not on the issue: "
                        + ", ".join(f"`{label}`" for label in withheld) + ".")
    run_link = f"/actions/runs/{run['id']}"
    if comment and not any(c["user"]["login"] == BOT and run_link in c["body"] for c in comments):
        problems.append("The requested triage comment is not on the issue.")
    if detection is None:
        notes.append("Threat detection left no verdict file.")
    elif any(detection.get(k) for k in ("prompt_injection", "secret_leak", "malicious_patch")):
        problems.append(f"Threat detection flagged the output: {detection.get('reasons')}.")
    if not problems and not suggested:
        notes.append("Every requested write is on the issue.")
    notes.append(f"Requested: labels {list(labels) or 'none'}, comment {'yes' if comment else 'no'}.")
    return problems, notes


def list_cap_skip(repo, issue, run_url):
    """Add a skipped issue to the one open list, so a burst raises one alert and not hundreds."""
    open_alerts = api(f"repos/{repo}/issues?state=open&labels=triage-alert&per_page=100")
    existing = [i["number"] for i in open_alerts if i["title"] == CAP_SKIP_TITLE]
    line = f"#{issue} ([run]({run_url}))"
    if existing:
        gh("api", "-X", "POST", f"repos/{repo}/issues/{existing[0]}/comments", "-f", f"body={line}")
        return
    args = ["-f", f"title={CAP_SKIP_TITLE}", "-f", "body=Triage these by hand or redispatch them, "
            "then close this issue.\n\n" + line, "-f", "labels[]=triage-alert"]
    if os.environ.get("ALERT_ASSIGNEE"):
        args += ["-f", f"assignees[]={os.environ['ALERT_ASSIGNEE']}"]
    gh("api", "-X", "POST", f"repos/{repo}/issues", *args)


def main():
    """Check one run, write the step summary, and open an alert issue if needed."""
    repo, run_id = os.environ["REPO"], os.environ["RUN_ID"]
    if not re.fullmatch(r"\d{1,20}", run_id):
        sys.exit(f"invalid run id {run_id!r}")
    run = api(f"repos/{repo}/actions/runs/{run_id}")
    issue = os.environ.get("ISSUE") or "".join(re.findall(r"#(\d+)", run.get("display_title", ""))[:1])
    if not re.fullmatch(r"\d{1,7}", issue or ""):
        print(f"run {run_id} names no issue ({run.get('display_title')!r}); nothing to check")
        return 0
    jobs = api(f"repos/{repo}/actions/runs/{run_id}/jobs?per_page=100")["jobs"]
    problems, notes = check(
        run, {job["name"]: job["conclusion"] for job in jobs}, api(f"repos/{repo}/actions/runs/{run_id}/approvals"),
        artifact_json(repo, run_id, "agent", "agent_output.json"),
        artifact_json(repo, run_id, "detection", "detection_result.json"),
        {label["name"] for label in api(f"repos/{repo}/issues/{issue}/labels")},
        api(f"repos/{repo}/issues/{issue}/comments"))
    report = [f"Triage run [{run_id}]({run['html_url']}) on issue #{issue}.", ""]
    report += [f"- {p}" for p in problems] or ["- No alert."]
    report += [""] + notes
    text = "\n".join(report)
    print(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as summary:
            summary.write(text + "\n")
    if not problems:
        return 0
    if problems == [CAP_SKIP]:
        list_cap_skip(repo, issue, run["html_url"])
        return 1
    args = ["-f", f"title=Triage run {run_id}: requested writes did not land on #{issue}",
            "-f", "body=" + text + "\n\nCheck the run, then apply or discard the writes by hand.",
            "-f", "labels[]=triage-alert"]
    if os.environ.get("ALERT_ASSIGNEE"):
        args += ["-f", f"assignees[]={os.environ['ALERT_ASSIGNEE']}"]
    gh("api", "-X", "POST", f"repos/{repo}/issues", *args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
