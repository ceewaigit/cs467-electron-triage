#!/usr/bin/env python3
"""Record a coding assistant's local use of the three triage scripts.

This recorder never calls a provider or GitHub. Each case needs a prepared
checkout/ and context.json under WORKSPACE/cases/TOKEN/. Preparation and scoring
belong to the evaluator; the assistant sees only the prepared case and instructions.

    python3 offline_dry_run.py --workspace DIR --case d001 start
    python3 offline_dry_run.py --workspace DIR --case d001 run triage_checks
    python3 offline_dry_run.py --workspace DIR --case d001 run check_labels component/tray
    python3 offline_dry_run.py --workspace DIR --case d001 finish --labels component/tray --reason 'Tray API report.'

The JSONL transcript contains the actual displayed context, script commands and
results, and the assistant's proposed outputs with a brief explanation. It is not
a provider session log and does not contain private model reasoning. This is an
instrumented dry run, not enforcement of the assistant's wider tool permissions.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys

SCRIPTS = ("triage_checks", "check_labels", "render_comment")
SKILL = pathlib.Path(".claude/skills/issue-triage")


def record(directory, event):
    """Append one observed interaction; never rewrite earlier transcript entries."""
    event = {"time_utc": dt.datetime.now(dt.timezone.utc).isoformat(), **event}
    with (directory / "transcript.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, ensure_ascii=False) + "\n")


def verify_snapshot(directory):
    """Stop if any prepared source or input changed during the exercise."""
    context = json.loads((directory / "context.json").read_text())
    checkout = directory / "checkout"
    for name, expected in context["file_sha256"].items():
        actual = hashlib.sha256((checkout / name).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"prepared file changed: {name}")
    return checkout


def start(directory, checkout):
    """Display the actual instructions and input, and retain exactly that text."""
    paths = ["AGENTS.md", "CLAUDE.md", ".github/workflows/issue-triage.md",
             str(SKILL / "SKILL.md"), ".triage/issue.json"]
    text = "\n\n".join(f"--- {name} ---\n{(checkout / name).read_text()}" for name in paths)
    record(directory, {"event": "context", "role": "user", "content": text})
    print(text)


def run_script(directory, checkout, script, arguments):
    """Run an unchanged allowlisted helper with no inherited API credentials."""
    if script == "triage_checks" and arguments:
        raise ValueError("triage_checks uses the prepared issue; no alternate input is allowed")
    relative = SKILL / "scripts" / f"{script}.py"
    command = [sys.executable, str(relative), *arguments]
    result = subprocess.run(command, cwd=checkout, capture_output=True, text=True,
                            env={"PATH": os.defpath, "HOME": str(checkout)}, timeout=30)
    record(directory, {"event": "script", "command": ["python3", str(relative), *arguments],
                       "exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
    print(result.stdout, end="")
    print(result.stderr, end="", file=sys.stderr)
    return result.returncode


def finish(directory, args):
    """Freeze the assistant's first decision without correcting it against the gold."""
    items = []
    if args.kinds:
        items.append({"type": "triage_comment", "kinds": args.kinds, "refs": args.refs})
    if args.labels:
        items.append({"type": "add_labels", "labels": args.labels})
    if not items:
        items.append({"type": "noop", "message": args.reason})
    proposal = {"execution_mode": "coding-assistant-dry-run", "writes_executed": False,
                "items": items, "explanation": args.reason}
    # Exclusive creation prevents a second decision from replacing the first.
    with (directory / "proposal.json").open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(proposal, indent=2, ensure_ascii=False) + "\n")
    record(directory, {"event": "assistant_decision", "role": "assistant", "content": proposal})
    print(json.dumps(proposal, indent=2, ensure_ascii=False))


def main():
    """Expose only transcript capture, the three scripts and simulated safe outputs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=pathlib.Path, required=True)
    parser.add_argument("--case", required=True)
    commands = parser.add_subparsers(dest="step", required=True)
    commands.add_parser("start")
    run = commands.add_parser("run")
    run.add_argument("script", choices=SCRIPTS)
    run.add_argument("arguments", nargs=argparse.REMAINDER)
    done = commands.add_parser("finish")
    done.add_argument("--labels", nargs="*", default=[])
    done.add_argument("--kinds", default="")
    done.add_argument("--refs", default="")
    done.add_argument("--reason", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"d\d{3}", args.case):
        parser.error("case must be an opaque token such as d001")
    directory = args.workspace.resolve() / "cases" / args.case
    if (directory / "proposal.json").exists():
        parser.error("this case already has a frozen decision")
    checkout = verify_snapshot(directory)
    if args.step != "start" and not (directory / "transcript.jsonl").exists():
        parser.error("read the case instructions with start first")
    if args.step == "start":
        start(directory, checkout)
    elif args.step == "run":
        return run_script(directory, checkout, args.script, args.arguments)
    else:
        finish(directory, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
