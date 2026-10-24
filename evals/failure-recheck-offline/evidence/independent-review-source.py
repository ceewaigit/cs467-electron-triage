#!/usr/bin/env python3
"""Independent offline audit. Reads no prior score, report or historical output.

Reconstructs bytes directly, uses the frozen scorer only for rubric scoring,
and re-executes all recorded helpers with a credential-free environment.
Creates independent-review.json exclusively; never replaces evidence.
"""
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
EVIDENCE = Path(__file__).resolve().parent
EXPERIMENT = EVIDENCE.parent
REPO = EXPERIMENT.parents[1]
FROZEN = EVIDENCE / "frozen"
SKILL = ".claude/skills/issue-triage/SKILL.md"
CORPUS = "data/issue-corpus.jsonl"
errors = []
checks = []


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def data(path):
    return json.loads(path.read_bytes())


def json_bytes(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()


def verify(name, actual, expected=True):
    passed = actual == expected
    checks.append({"check": name, "passed": passed})
    if not passed:
        errors.append({"check": name, "actual": actual, "expected": expected})


def git_bytes(commit, name):
    return subprocess.check_output(["git", "show", f"{commit}:{name}"], cwd=REPO)


def neutralise(text):
    text = re.sub(r"https?://(?:www\.)?github\.com/([\w.-]+)/([\w.-]+)/(?:issues|pull|discussions)/(\d+)[^\s)\]>]*",
                  r"`\1/\2#\3`", text)
    text = re.sub(r"(?<![\w/`])([\w.-]+/[\w.-]+#\d+)", r"`\1`", text)
    return re.sub(r"(?<![\w`])@([A-Za-z0-9][\w-]*)", "@\u200b\\1", text)


def execute(command, checkout):
    allowed = {f".claude/skills/issue-triage/scripts/{name}.py"
               for name in ("triage_checks", "check_labels", "render_comment")}
    if command[0] != "python3" or command[1] not in allowed:
        raise ValueError(f"Unexpected helper: {command!r}")
    run = subprocess.run([sys.executable, *command[1:]], cwd=checkout,
                         capture_output=True, text=True, timeout=30,
                         env={"PATH": os.defpath, "HOME": str(checkout)})
    return {"command": command, "exit_code": run.returncode,
            "stdout": run.stdout, "stderr": run.stderr}


manifest = data(EVIDENCE / "manifest.json")
source = manifest["source_commit"]
verify("manifest checksum", sha((EVIDENCE / "manifest.json").read_bytes()),
       (EVIDENCE / "manifest.sha256").read_text().strip())
for name, expected in manifest["freeze_sha256"].items():
    verify(f"frozen {name}", sha((FROZEN / name).read_bytes()), expected)
for name, expected in manifest["runtime_sha256"].items():
    verify(f"source commit runtime {name}", sha(git_bytes(source, name)), expected)
for name, path in (("helper.py", "evals/reproduction-check/experiment.py"),
                   ("recorder.py", "evals/tools/offline_dry_run.py"),
                   ("score.py", "evals/tools/score.py")):
    verify(f"source commit evaluator {name}", sha(git_bytes(source, path)),
           sha((FROZEN / name).read_bytes()))
verify("frozen original rubric scorer", sha(git_bytes("4baa2cb", "evals/tools/score.py")),
       sha((FROZEN / "score.py").read_bytes()))
verify("protocol frozen copy", (EXPERIMENT / "PROTOCOL.md").read_bytes() == (FROZEN / "protocol.md").read_bytes())
verify("check script frozen copy", (EXPERIMENT / "check.py").read_bytes() == (FROZEN / "check.py").read_bytes())
seal = data(EVIDENCE / "sealed-proposals.json")
collection = data(EVIDENCE / "collection.json")
verify("seal manifest", seal["manifest_sha256"], sha((EVIDENCE / "manifest.json").read_bytes()))
verify("collection seal", collection["sealed_proposals_sha256"], sha((EVIDENCE / "sealed-proposals.json").read_bytes()))
for identity, export in collection["exports"].items():
    for name, expected in export["file_sha256"].items():
        verify(f"export {name}", sha((EXPERIMENT / name).read_bytes()), expected)
spec = importlib.util.spec_from_file_location("independent_frozen_scorer", FROZEN / "score.py")
scorer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scorer)
runtime = {name: (FROZEN / "runtime" / name).read_bytes() for name in manifest["runtime_sha256"]}
rows = {}
all_times = []
with tempfile.TemporaryDirectory(prefix="five-failures-independent-") as temporary:
    for batch in manifest["batches"]:
        verify(f"batch prompt {batch['id']}", sha((EVIDENCE / "batch-prompts" / f"{batch['id']}.md").read_bytes()),
               batch["instructions_sha256"])
        for case in batch["cases"]:
            identity = f"{batch['id']}/{case['token']}"
            cid = case["case_id"]
            original_raw = (FROZEN / "cases" / cid / "input.json").read_bytes()
            opening = json.loads(original_raw)
            expected_raw = (FROZEN / "cases" / cid / "expected.json").read_bytes()
            for name, raw in (("input.json", original_raw), ("expected.json", expected_raw)):
                verify(f"original frozen commit {cid}/{name}", sha(git_bytes("4baa2cb", f"evals/golden/cases/{cid}/{name}")), sha(raw))
                verify(f"selected copy {cid}/{name}", (EXPERIMENT / "cases" / cid / name).read_bytes() == raw)
            issue = {"number": 800000 + int(case["token"][1:]), "title": neutralise(opening["title"]),
                     "body": neutralise(opening["body"]), "labels": opening["labels_at_open"],
                     "state": "open", "author_association": opening["author_association"],
                     "as_of": opening["as_of"], "replay": True}
            corpus_rows = [line for line in runtime[CORPUS].decode().splitlines() if line.strip()]
            earlier = [line for line in corpus_rows if json.loads(line)["created_at"] < issue["as_of"]]
            files = {**runtime, CORPUS: ("".join(line + "\n" for line in earlier)).encode(),
                     ".triage/issue.json": json_bytes(issue)}
            checkout = Path(temporary) / batch["id"] / case["token"]
            for name, raw in files.items():
                path = checkout / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
            context = {"case_token": case["token"], "earlier_corpus_rows": len(earlier),
                       "file_sha256": {name: sha(raw) for name, raw in sorted(files.items())}}
            verify(f"reconstructed context {identity}", sha(json_bytes(context)), case["context_sha256"])
            verify(f"saved context {identity}", sha((EVIDENCE / "contexts" / batch["id"] / f"{case['token']}.json").read_bytes()), case["context_sha256"])
            verify(f"normalized issue {cid}", sha(json_bytes(issue)), case["normalized_input_sha256"])
            verify(f"case input {cid}", sha(original_raw), case["input_sha256"])
            verify(f"no grading or history paths in context {cid}", not any(
                name.startswith(("evals/", ".git/")) or name.endswith(("expected.json", "DESIGN.md")) for name in files))
            log = EXPERIMENT / "cases" / cid / "actual/latest/logs/run-1"
            actual = data(log.parents[1] / "run-1.json")
            proposal = data(log / "proposal.json")
            events = [json.loads(line) for line in (log / "transcript.jsonl").read_text().splitlines()]
            verify(f"proposal seal {identity}", sha((log / "proposal.json").read_bytes()), seal["sessions"][identity]["proposal_sha256"])
            verify(f"transcript seal {identity}", sha((log / "transcript.jsonl").read_bytes()), seal["sessions"][identity]["transcript_sha256"])
            verify(f"logged context {cid}", (log / "context.json").read_bytes() == json_bytes(context))
            verify(f"logged issue {cid}", (log / "issue.json").read_bytes() == json_bytes(issue))
            names = ("AGENTS.md", "CLAUDE.md", ".github/workflows/issue-triage.md", SKILL, ".triage/issue.json")
            displayed = "\n\n".join(f"--- {name} ---\n{files[name].decode()}" for name in names)
            contexts = [event for event in events if event["event"] == "context"]
            verify(f"context is first event {cid}", events[0]["event"], "context")
            verify(f"displayed context exact {cid}", bool(contexts) and all(event["content"] == displayed for event in contexts))
            decisions = [event for event in events if event["event"] == "assistant_decision"]
            verify(f"one final decision {cid}", len(decisions), 1)
            verify(f"decision final event {cid}", events[-1]["event"], "assistant_decision")
            verify(f"proposal matches first decision {cid}", decisions[0]["content"], proposal)
            verify(f"proposal no executed writes {cid}", proposal["writes_executed"], False)
            times = [event["time_utc"] for event in events]
            verify(f"event timestamps ordered {cid}", times, sorted(times))
            all_times.extend(times)
            scripts = [event for event in events if event["event"] == "script"]
            for index, event in enumerate(scripts, 1):
                replay = execute(event["command"], checkout)
                verify(f"helper replay {cid}/{index}", replay, {key: event[key] for key in replay})
            items = proposal["items"]
            types = [item["type"] for item in items]
            verify(f"action types valid {cid}", len(types) == len(set(types)) and set(types) <= {"add_labels", "triage_comment", "noop"})
            verify(f"noop exclusive {cid}", "noop" not in types or types == ["noop"])
            labels = next((item["labels"] for item in items if item["type"] == "add_labels"), [])
            request = next((item for item in items if item["type"] == "triage_comment"), None)
            validations = []
            if labels:
                validations.append(execute(["python3", ".claude/skills/issue-triage/scripts/check_labels.py", *labels], checkout))
            comment = None
            if request:
                result = execute(["python3", ".claude/skills/issue-triage/scripts/render_comment.py", "--kinds", request["kinds"], "--refs", request["refs"]], checkout)
                validations.append(result)
                if result["exit_code"] == 0:
                    comment = result["stdout"].split("-----BEGIN COMMENT-----\n", 1)[1].split("\n-----END COMMENT-----", 1)[0]
            verify(f"export validation replay {cid}", validations, data(log / "export-validation.json"))
            verify(f"all final validations accepted {cid}", all(result["exit_code"] == 0 for result in validations))
            verify(f"exported labels {cid}", actual["labels_added"], labels)
            verify(f"exported comment {cid}", actual["comment"], comment)
            verify(f"exported comment request {cid}", actual["comment_request"], request)
            verify(f"no other writes {cid}", actual["other_writes"], [])
            verify(f"scorable final proposal {cid}", actual["scored"] and not actual["invalid_final_proposal"])
            verify(f"export source commit {cid}", actual["source_commit"], source)
            verify(f"export proposal checksum {cid}", actual["proposal_sha256"], sha((log / "proposal.json").read_bytes()))
            verify(f"export policy checksum {cid}", actual["policy_sha256"], manifest["runtime_sha256"][SKILL])
            good = [event for event in scripts if event["exit_code"] == 0]
            checked_labels = {label for event in good if event["command"][1].endswith("/check_labels.py") for label in event["command"][2:]}
            procedure = {"checks_executed": any(event["command"][1].endswith("/triage_checks.py") for event in good),
                         "labels_validated_before_decision": set(labels) <= checked_labels,
                         "comment_rendered_before_decision": comment is None or any(event["command"][1].endswith("/render_comment.py") and comment in event["stdout"] for event in good),
                         "rejected_script_calls": [event for event in scripts if event["exit_code"] != 0]}
            verify(f"exported procedure {cid}", actual["procedure"], procedure)
            kinds, refs = scorer.parse_comment(comment)
            corpus = {json.loads(line)["number"]: json.loads(line) for line in earlier}
            future_refs = sorted(ref for ref in refs if ref not in corpus)
            verify(f"references in earlier context {cid}", future_refs, [])
            verify(f"label/action limits {cid}", len(labels) <= 3 and sum(label.startswith("component/") for label in labels) <= 2 and len(refs) <= 3)
            rows[cid] = {"score": scorer.score_run(json.loads(expected_raw), actual), "procedure": procedure,
                         "earlier_corpus_rows": len(earlier), "excluded_equal_or_later_rows": len(corpus_rows) - len(earlier),
                         "as_of": issue["as_of"], "reference_dates": {str(ref): corpus[ref]["created_at"] for ref in sorted(refs) if ref in corpus},
                         "helper_calls_replayed": len(scripts), "export_validations_replayed": len(validations),
                         "labels": labels, "kinds": sorted(kinds), "refs": sorted(refs)}
verify("all decisions precede seal", all(time <= seal["sealed_at_utc"] for time in all_times))
verify("all planned first decisions", len(rows), manifest["planned_first_decisions"])
verify("collected first decisions", collection["first_decisions"], len(rows))
verify("invalid final proposal count", collection["invalid_final_proposals"], 0)
report = {"reviewed_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
          "review_source_sha256": sha(Path(__file__).read_bytes()), "source_commit": source,
          "independence": "Calculated before reading experiment score.json, README, coordinator conclusion, or the five old outputs. Required CODEBASE guide was read and contains the historical aggregate 20/25 result.",
          "case_count": len(rows), "passes": sum(row["score"]["pass"] for row in rows.values()),
          "weighted_error_cost_total": sum(row["score"]["cost"] for row in rows.values()),
          "safety_failures": sum(row["score"]["safety"] for row in rows.values()),
          "checks_run": len(checks), "checks_passed": sum(check["passed"] for check in checks),
          "integrity_or_replay_errors": errors, "checks": checks, "cases": rows,
          "limits": ["One selected known-failure trial per case; cannot establish causality or full-suite improvement.",
                     "Recorder transcript covers declared context and helpers, not all assistant tools or internal reasoning.",
                     "No configured-Claude/provider or GitHub execution; hosted controls and total cost untested."]}
with (EVIDENCE / "independent-review.json").open("xb") as stream:
    stream.write(json_bytes(report))
print(json.dumps({key: report[key] for key in ("case_count", "passes", "weighted_error_cost_total", "safety_failures", "checks_run", "checks_passed", "integrity_or_replay_errors", "cases")}, indent=2))
