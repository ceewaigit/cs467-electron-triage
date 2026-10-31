#!/usr/bin/env python3
"""Alert the owner when a finished triage run's requested writes are not on its issue.

Run by .github/workflows/triage-watchdog.yml after every triage run. No model is involved.
Environment: GH_TOKEN, REPO, RUN_ID, optional ISSUE (else read from the run title
"Issue triage #N"), ALERT_ASSIGNEE and GITHUB_STEP_SUMMARY.

A run can succeed while its writes never land: gh-aw withholds labels when threat detection
cannot reach a verdict, and GitHub keeps labels below HIGH confidence as suggestions
(evals/golden/results/delivery-final.md). This script compares what the agent requested
with what the issue shows and opens one alert issue, assigned to the owner, when they
differ. A reviewer's rejection in the `triage-writes` environment is reported, not alerted.
Exit status 1 means an alert was opened, so the watchdog run also shows as failed.
"""
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile

BOT = "github-actions[bot]"


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
    """Labels and comment the agent asked for, from its safe-output file."""
    labels, comment = [], False
    for item in (agent_output or {}).get("items", []):
        if item.get("type") == "add_labels":
            labels += [label if isinstance(label, str) else label["name"] for label in item.get("labels", [])]
        elif item.get("type") == "triage_comment":
            comment = True
    return labels, comment


def check(run, agent_ran, approvals, agent_output, detection, issue_labels, comments):
    """Return (problems, notes) for one finished run; problems mean the owner must look."""
    problems, notes = [], [f"Run conclusion: {run.get('conclusion')}."]
    if not agent_ran:
        # A maintainer's own issue, the daily credit cap or a rejected start: no decision was made.
        notes.append("The agent job did not run, so no writes were requested.")
        return problems, notes
    if any(a.get("state") == "rejected" for a in approvals):
        notes.append("A reviewer rejected the writes in `triage-writes`; nothing was expected to land.")
        return problems, notes
    if agent_output is None:
        if run.get("conclusion") == "success":
            problems.append("The run succeeded but left no agent output to check.")
        return problems, notes
    labels, comment = requested_writes(agent_output)
    missing = [label for label in labels if label not in issue_labels]
    if missing:
        problems.append("Requested labels are not on the issue (withheld by gh-aw, or held by GitHub "
                        "as suggestions): " + ", ".join(f"`{label}`" for label in missing) + ".")
    run_link = f"/actions/runs/{run['id']}"
    if comment and not any(c["user"]["login"] == BOT and run_link in c["body"] for c in comments):
        problems.append("The requested triage comment is not on the issue.")
    if detection is None:
        notes.append("Threat detection left no verdict file.")
    elif any(detection.get(k) for k in ("prompt_injection", "secret_leak", "malicious_patch")):
        problems.append(f"Threat detection flagged the output: {detection.get('reasons')}.")
    notes.append(f"Requested: labels {labels or 'none'}, comment {'yes' if comment else 'no'}.")
    return problems, notes


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
    agent_ran = any(job["name"] == "agent" and job["conclusion"] not in ("skipped", None) for job in jobs)
    problems, notes = check(
        run, agent_ran, api(f"repos/{repo}/actions/runs/{run_id}/approvals"),
        artifact_json(repo, run_id, "agent", "agent_output.json"),
        artifact_json(repo, run_id, "detection", "detection_result.json"),
        {label["name"] for label in api(f"repos/{repo}/issues/{issue}/labels")},
        api(f"repos/{repo}/issues/{issue}/comments"))
    report = [f"Triage run [{run_id}]({run['html_url']}) on issue #{issue}.", ""]
    report += [f"- {p}" for p in problems] or ["- Every requested write is on the issue."]
    report += [""] + notes
    text = "\n".join(report)
    print(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as summary:
            summary.write(text + "\n")
    if not problems:
        return 0
    args = ["-f", f"title=Triage run {run_id}: requested writes did not land on #{issue}",
            "-f", "body=" + text + "\n\nCheck the run, then apply or discard the writes by hand.",
            "-f", "labels[]=triage-alert"]
    if os.environ.get("ALERT_ASSIGNEE"):
        args += ["-f", f"assignees[]={os.environ['ALERT_ASSIGNEE']}"]
    gh("api", "-X", "POST", f"repos/{repo}/issues", *args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
