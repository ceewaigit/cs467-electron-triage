#!/usr/bin/env python3
"""Independent offline audit. Never makes assistant decisions or changes source evidence.

Run without arguments after collection to reconstruct and replay every helper,
compute all endpoints and save an exclusive first independent result. Only then
run --compare-parent to compare that saved result with evidence/score.json.
The experiment module and its primary_decision function are never imported.
"""
import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import re
import shutil
import subprocess
import sys
import tempfile

EVIDENCE = Path(__file__).resolve().parent
EXP = EVIDENCE.parent
ROOT = EXP.parents[1]
FROZEN = EVIDENCE / "frozen"
BASELINE = "962fac774c7845bca0da2d310ca1bdcca09c50ea"
SKILL = ".claude/skills/issue-triage/SKILL.md"
CORPUS = "data/issue-corpus.jsonl"
HELPERS = ".claude/skills/issue-triage/scripts/"
RESULT = EVIDENCE / "independent-check-results.json"
ISSUES = []
COUNTS = {}


def raw(path):
    return Path(path).read_bytes()


def read(path):
    return json.loads(raw(path))


def sha(value):
    return hashlib.sha256(value).hexdigest()


def digest(path):
    return sha(raw(path))


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()


def check(condition, message):
    if not condition:
        ISSUES.append(message)


def git_bytes(path, commit=BASELINE):
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def utc(value):
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def filtered_corpus(value, cutoff):
    return b"".join(line + b"\n" for line in value.splitlines()
                    if line.strip() and utc(json.loads(line)["created_at"]) < utc(cutoff))


def normalize(opening, token):
    def neutralize(value):
        value = re.sub(r"https?://(?:www\.)?github\.com/([\w.-]+)/([\w.-]+)/(?:issues|pull|discussions)/(\d+)[^\s)\]>]*",
                       r"`\1/\2#\3`", value)
        value = re.sub(r"(?<![\w/`])([\w.-]+/[\w.-]+#\d+)", r"`\1`", value)
        return re.sub(r"(?<![\w`])@([A-Za-z0-9][\w-]*)", "@\u200b\\1", value)
    return {"number": 800000 + int(token[1:]), "title": neutralize(opening["title"]),
            "body": neutralize(opening["body"]), "labels": opening["labels_at_open"],
            "state": "open", "author_association": opening["author_association"],
            "as_of": opening["as_of"], "replay": True}


def load_scorer():
    spec = importlib.util.spec_from_file_location("independent_frozen_scorer", FROZEN / "score.py")
    module = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    return module


def verify_preparation(manifest):
    """Check selection, provenance, immutable source and exact pre-execution hashes."""
    check(digest(EVIDENCE / "manifest.json") == (EVIDENCE / "manifest.sha256").read_text().strip(), "manifest seal")
    for name, expected_hash in manifest["freeze_sha256"].items():
        check(digest(FROZEN / name) == expected_hash, f"frozen hash {name}")
        if name.startswith("runtime/"):
            check(raw(FROZEN / name) == git_bytes(name[8:]), f"baseline runtime {name}")
        elif name in {"score.py", "recorder.py", "replay.py"}:
            original = "offline_dry_run.py" if name == "recorder.py" else name
            check(raw(FROZEN / name) == git_bytes("evals/tools/" + original), f"baseline evaluator {name}")
        elif (EXP / name).exists():
            check(raw(FROZEN / name) == raw(EXP / name), f"current frozen source {name}")
    check(raw(FROZEN / "score.py") == git_bytes("evals/tools/score.py", "4baa2cb"), "original frozen scorer 4baa2cb")
    check(raw(ROOT / "evals/golden/RUBRIC.md") == git_bytes("evals/golden/RUBRIC.md", "4baa2cb"), "original golden rubric")
    old_golden = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", "4baa2cb", "evals/golden/cases"], cwd=ROOT, text=True).splitlines()
    golden_inputs = [name for name in old_golden if name.endswith(("/input.json", "/expected.json"))]
    for name in golden_inputs:
        check(raw(ROOT / name) == git_bytes(name, "4baa2cb"), f"original golden file {name}")
    prior = read(FROZEN / "prior-evidence-hashes.json")
    changed_prior = [name for name, value in prior["sha256"].items() if not (ROOT / name).exists() or digest(ROOT / name) != value]
    check(not changed_prior, f"prior files changed: {changed_prior}")
    COUNTS.update(frozen_files=len(manifest["freeze_sha256"]), prior_files=len(prior["sha256"]), original_golden_files=len(golden_inputs))
    original = raw(FROZEN / "policies/original-SKILL.md")
    candidate = raw(FROZEN / "policies/candidate-SKILL.md")
    check(original == git_bytes(SKILL), "original skill baseline")
    start, end = b"### 3. Reproduction", b"### 4. Similar earlier issues"
    check(original.split(start)[0] == candidate.split(start)[0] and original.split(end)[1] == candidate.split(end)[1], "candidate changes outside section 3")
    check(original != candidate, "candidate identical to baseline")
    protocol = read(FROZEN / "protocol.json")
    for arm in ("original", "candidate"):
        check(digest(FROZEN / f"policies/{arm}-SKILL.md") == protocol["policy_sha256"][arm], f"protocol {arm} hash")
    dataset = read(FROZEN / "dataset.json")
    review = read(FROZEN / "annotation-review.json")
    provenance = read(FROZEN / "annotation-provenance.json")
    check(review["verdict"] == "accepted" and not review["blocking_findings"], "pre-execution annotation acceptance")
    check(review["dataset_sha256"] == digest(FROZEN / "dataset.json"), "review dataset binding")
    check(review["annotation_provenance_sha256"] == digest(FROZEN / "annotation-provenance.json"), "review provenance binding")
    for name, value in review["source_sha256"].items():
        check(sha(git_bytes(name)) == value, f"review baseline source {name}")
    for name, value in review["supporting_file_sha256"].items():
        check(digest(EXP / name) == value, f"review supporting file {name}")
    for name, value in review["case_file_sha256"].items():
        check(digest(FROZEN / name) == value and digest(EXP / name) == value, f"review case binding {name}")
    check(utc(review["reviewed_at_utc"]) < utc(manifest["prepared_at_utc"]), "review must precede preparation")
    tests = read(FROZEN / "pre-execution-tests-hash.json")
    check(tests["log_sha256"] == digest(EXP / "pre-execution-tests.txt"), "pre-execution tests log hash")
    check(tests["harness_sha256"] == digest(FROZEN / "experiment.py") and tests["exit_code"] == 0, "pre-execution harness/test status")
    selection = read(FROZEN / "selection.json")
    check(digest(ROOT / selection["source"]) == selection["source_sha256"], "selection source hash")
    previous, inspected = set(), []
    for path in sorted((ROOT / "evals").rglob("input.json")):
        if EXP in path.parents:
            continue
        entry = read(path)
        match = re.search(r"electron/electron/issues/(\d+)", entry.get("source", ""))
        if match:
            previous.add(int(match[1]))
        elif re.fullmatch(r"e\d+", entry.get("id", "")):
            previous.add(int(entry["id"][1:]))
        if isinstance(entry.get("source_number"), int):
            previous.add(entry["source_number"])
        inspected.append(str(path.relative_to(ROOT)))
    check(inspected == selection["previous_case_inputs_inspected"], "selection prior inventory")
    check(sorted(previous) == selection["previous_real_numbers_excluded"], "selection exclusions")
    rng = random.Random(4672027)
    source = [json.loads(line) for line in raw(ROOT / selection["source"]).splitlines() if line.strip()]
    by_number = {entry["number"]: entry for entry in source}
    selected = []
    for month in ("2026-04", "2026-05", "2026-06"):
        eligible = sorted(entry["number"] for entry in source if entry["created_at"].startswith(month)
                          and entry.get("author_type") != "Bot" and not (entry.get("author") or "").lower().endswith("[bot]")
                          and entry["author_association"].upper() not in {"MEMBER", "OWNER", "COLLABORATOR"}
                          and entry["number"] not in previous)
        draw = rng.sample(eligible, 6)
        check(selection["months"][month] == {"eligible_sorted": eligible, "selected_in_draw_order": draw}, f"random selection {month}")
        selected.extend(draw)
    check(selection["case_order"] == [f"e{number}" for number in selected], "selected IDs retained")
    cases = {entry["id"]: entry for entry in dataset["cases"]}
    check(len(cases) == 30 and {case_id for case_id, entry in cases.items() if entry["group"] == "historical"} == set(selection["case_order"]), "cohort membership")
    for number in selected:
        opening = read(FROZEN / f"cases/e{number}/input.json")
        source_row = by_number[number]
        for field in ("title", "body", "author_association", "labels_at_open", "body_source"):
            check(opening[field] == source_row[field], f"opening source {number}/{field}")
        check(opening["as_of"] == source_row["created_at"], f"opening time {number}")
    baseline_corpus = raw(FROZEN / "runtime" / CORPUS)
    for case_id, metadata in cases.items():
        for filename, detail in metadata["files"].items():
            check(detail["path"] == f"cases/{case_id}/{filename}" and digest(FROZEN / detail["path"]) == detail["sha256"], f"dataset binding {case_id}/{filename}")
        opening = read(FROZEN / f"cases/{case_id}/input.json")
        own_corpus = FROZEN / f"cases/{case_id}/corpus.jsonl"
        corpus = filtered_corpus(raw(own_corpus) if own_corpus.exists() else baseline_corpus, opening["as_of"])
        check(sha(corpus) == metadata["corpus_sha256"], f"cutoff corpus {case_id}")
        check(len(corpus.splitlines()) == metadata["corpus_rows"], f"corpus row count {case_id}")
        if metadata["group"] == "historical":
            check(corpus == filtered_corpus(baseline_corpus, opening["as_of"]), f"historical corpus reconstruction {case_id}")
        expected = read(FROZEN / f"cases/{case_id}/expected.json")
        allowed_labels = set(expected["labels"]["required"] + expected["labels"]["acceptable"]) | {x for g in expected["labels"]["one_of"] for x in g}
        allowed_kinds = set(expected["comment"]["required_kinds"] + expected["comment"]["acceptable_kinds"])
        disposition = metadata["repro_expectation"]
        if disposition == "required":
            check("blocked/need-repro" in expected["labels"]["required"] and "need-repro" in expected["comment"]["required_kinds"], f"required repro target {case_id}")
        else:
            check(("blocked/need-repro" in allowed_labels) == (disposition == "optional") and ("need-repro" in allowed_kinds) == (disposition == "optional"), f"repro target {case_id}")
    COUNTS.update(previous_ids=len(previous), case_files_bound=len(review["case_file_sha256"]), preexecution_review_time=review["reviewed_at_utc"])
    return cases, protocol


def reconstruct(manifest, cases, destination):
    """Build only frozen runtime and normalized inputs; compare all recorded hashes."""
    runtime = {name: raw(FROZEN / "runtime" / name) for name in manifest["runtime_sha256"]}
    for name, expected_hash in manifest["runtime_sha256"].items():
        check(sha(runtime[name]) == expected_hash, f"runtime manifest {name}")
    ids = sorted(cases)
    arms = ["original", "candidate"]
    random.Random(4672027).shuffle(arms)
    reconstructed = {}
    for batch in manifest["batches"]:
        ordered = ids.copy()
        random.Random(4672027 + batch["repetition"]).shuffle(ordered)
        index = int(batch["id"][1:]) - 1
        offset = index % 3 * 10
        check(batch["arm"] == arms[(index % 6) // 3], f"anonymous arm mapping {batch['id']}")
        check(batch["opaque_arm"] == f"v{(index % 6) // 3 + 1:02}", f"anonymous arm label {batch['id']}")
        check([item["case_id"] for item in batch["cases"]] == ordered[offset:offset + 10], f"paired order {batch['id']}")
        prompt = EVIDENCE / "batch-prompts" / (batch["id"] + ".md")
        check(digest(prompt) == batch["instructions_sha256"], f"batch prompt seal {batch['id']}")
        check("Start fresh without parent chat history" in prompt.read_text(), f"fresh batch instruction {batch['id']}")
        for position, item in enumerate(batch["cases"], offset + 1):
            token, case_id = item["token"], item["case_id"]
            check(token == f"d{position:03}", f"opaque case order {batch['id']}/{token}")
            opening = read(FROZEN / f"cases/{case_id}/input.json")
            corpus_path = FROZEN / f"cases/{case_id}/corpus.jsonl"
            corpus = filtered_corpus(raw(corpus_path) if corpus_path.exists() else runtime[CORPUS], opening["as_of"])
            files = {**runtime, SKILL: raw(FROZEN / f"policies/{batch['arm']}-SKILL.md"), CORPUS: corpus,
                     ".triage/issue.json": encoded(normalize(opening, token))}
            check(set(files) == set(manifest["runtime_sha256"]) | {".triage/issue.json"}, "unexpected prepared context file")
            check(not any("expected" in name or "dataset" in name or name.startswith(("evals/", ".git/")) for name in files), "grading data in prepared context")
            checkout = destination / batch["id"] / token
            for name, value in files.items():
                path = checkout / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(value)
            context = {"case_token": token, "earlier_corpus_rows": len(corpus.splitlines()),
                       "file_sha256": {name: sha(value) for name, value in sorted(files.items())}}
            check(sha(encoded(context)) == item["context_sha256"], f"reconstructed context {batch['id']}/{token}")
            check(encoded(context) == raw(EVIDENCE / "contexts" / batch["id"] / f"{token}.json"), f"saved context {batch['id']}/{token}")
            check(sha(files[".triage/issue.json"]) == item["normalized_input_sha256"], f"normalized input {batch['id']}/{token}")
            check(digest(FROZEN / f"cases/{case_id}/input.json") == item["input_sha256"], f"opening digest {batch['id']}/{token}")
            reconstructed[f"{batch['id']}/{token}"] = (checkout, context)
    COUNTS["reconstructed_contexts"] = len(reconstructed)
    return reconstructed


def displayed(checkout):
    names = ["AGENTS.md", "CLAUDE.md", ".github/workflows/issue-triage.md", SKILL, ".triage/issue.json"]
    return "\n\n".join(f"--- {name} ---\n{(checkout / name).read_text()}" for name in names)


def execute(checkout, command):
    check(command[0] == "python3" and command[1] in {HELPERS + name + ".py" for name in ("triage_checks", "check_labels", "render_comment")}, f"nonallowlisted helper {command}")
    if command[1].endswith("triage_checks.py"):
        check(len(command) == 2, "alternate helper input")
    result = subprocess.run([sys.executable, *command[1:]], cwd=checkout, capture_output=True,
                            text=True, timeout=30, env={"PATH": os.defpath, "HOME": str(checkout)})
    return {"command": command, "exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}


def readable(events):
    text = "# Recorded coding-assistant session\n\nProposed actions only; no external writes.\n"
    for index, event in enumerate(events, 1):
        text += f"\n## {index}. {event['event']} — {event.get('time_utc', 'timestamp unavailable')}\n\n"
        text += event["content"] + "\n" if event["event"] == "context" else "````json\n" + json.dumps(event, indent=2, ensure_ascii=False) + "\n````\n"
    return text.encode()


def audit_session(logs, checkout, context, actual, earliest, latest, key):
    """Replay all events and exports; independently recover the proposed actions."""
    proposal = read(logs / "proposal.json")
    events = [json.loads(line) for line in raw(logs / "transcript.jsonl").splitlines()]
    check(events[0]["event"] == "context" and events[-1]["event"] == "assistant_decision", f"session endpoints {key}")
    check(sum(event["event"] == "assistant_decision" for event in events) == 1 and events[-1]["content"] == proposal, f"unique first decision {key}")
    check(all(event["event"] in {"context", "script", "assistant_decision"} for event in events), f"event vocabulary {key}")
    times = [utc(event["time_utc"]) for event in events]
    check(times == sorted(times) and earliest < times[0] <= times[-1] < latest, f"event time sequence {key}")
    check(all(event["content"] == displayed(checkout) for event in events if event["event"] == "context"), f"displayed context {key}")
    check(encoded(context) == raw(logs / "context.json"), f"export context {key}")
    check(raw(checkout / ".triage/issue.json") == raw(logs / "issue.json"), f"export issue {key}")
    check(readable(events) == raw(logs / "transcript.md"), f"readable transcript {key}")
    scripts = [event for event in events if event["event"] == "script"]
    for event in scripts:
        replayed = execute(checkout, event["command"])
        check(all(replayed[field] == event[field] for field in ("exit_code", "stdout", "stderr")), f"helper replay {key}: {event['command']}")
    COUNTS["recorded_helper_calls"] = COUNTS.get("recorded_helper_calls", 0) + len(scripts)
    check(proposal["writes_executed"] is False and isinstance(proposal["explanation"], str), f"proposal metadata {key}")
    items = proposal["items"]
    types = [item["type"] for item in items]
    valid_types = bool(types) and len(types) == len(set(types)) and set(types) <= {"add_labels", "triage_comment", "noop"} and ("noop" not in types or len(types) == 1)
    check(valid_types, f"proposal structure {key}")
    labels, comment, request, validations = [], None, None, []
    for item in items:
        if item["type"] == "add_labels":
            labels = item["labels"]
            validations.append(execute(checkout, ["python3", HELPERS + "check_labels.py", *labels]))
        elif item["type"] == "triage_comment":
            request = item
            rendered = execute(checkout, ["python3", HELPERS + "render_comment.py", "--kinds", item["kinds"], "--refs", item["refs"]])
            validations.append(rendered)
            if rendered["exit_code"] == 0:
                comment = rendered["stdout"].split("-----BEGIN COMMENT-----\n", 1)[1].split("\n-----END COMMENT-----", 1)[0]
    check(validations == read(logs / "export-validation.json"), f"export validation replay {key}")
    COUNTS["export_validation_calls"] = COUNTS.get("export_validation_calls", 0) + len(validations)
    good = [event for event in scripts if event["exit_code"] == 0]
    validated_labels = {label for event in good if event["command"][1].endswith("check_labels.py") for label in event["command"][2:]}
    procedure = {"checks_executed": any(event["command"][1].endswith("triage_checks.py") for event in good),
                 "labels_validated_before_decision": set(labels) <= validated_labels,
                 "comment_rendered_before_decision": comment is None or any(event["command"][1].endswith("render_comment.py") and comment in event["stdout"] for event in good),
                 "rejected_script_calls": [event for event in scripts if event["exit_code"] != 0]}
    expected_outcome = {"labels_added": labels, "comment": comment, "other_writes": [], "scored": valid_types and all(v["exit_code"] == 0 for v in validations),
                        "invalid_final_proposal": not (valid_types and all(v["exit_code"] == 0 for v in validations)), "validation_errors": [], "comment_request": request}
    for field, value in expected_outcome.items():
        check(actual[field] == value, f"actual reconstructed {key}/{field}")
    if "procedure" in actual:
        check(actual["procedure"] == procedure, f"procedure reconstruction {key}")
    return proposal, events, procedure


def analyze(expected, metadata, opening, actual, scorer, procedure):
    scored = scorer.score_run(expected, actual)
    labels = set(actual["labels_added"])
    kinds, refs = scorer.parse_comment(actual["comment"])
    request = actual["comment_request"] or {}
    proposed_kinds = kinds | {value.strip() for value in request.get("kinds", "").split(",") if value.strip()}
    requested_refs = [int(value) for value in re.findall(r"\d{4,6}", request.get("refs", ""))]
    reporter_refs = {int(value) for value in re.findall(r"(?:electron/electron/issues/|#)(\d{4,6})\b", opening["body"])}
    required_labels = set(expected["labels"]["required"]) | {label for group in expected["labels"]["one_of"] for label in group}
    allowed_labels = required_labels | set(expected["labels"]["acceptable"])
    allowed_kinds = set(expected["comment"]["required_kinds"] + expected["comment"]["acceptable_kinds"])
    label_present = "blocked/need-repro" in labels
    kind_present = "need-repro" in proposed_kinds
    missed_repro = int("blocked/need-repro" in expected["labels"]["required"] and not label_present) + int("need-repro" in expected["comment"]["required_kinds"] and not kind_present)
    unwanted_repro = int(label_present and "blocked/need-repro" not in allowed_labels) + int(kind_present and "need-repro" not in allowed_kinds)
    controls = {"component": bool(labels & {label for label in allowed_labels if label.startswith("component/")}),
                "link": "similar" in kinds and bool(refs & set(metadata["coverage_supported_refs"]))}
    all_refs = refs | set(requested_refs)
    constraints = {"label_limits_observed": len(actual["labels_added"]) <= 3 and sum(label.startswith("component/") for label in actual["labels_added"]) <= 2,
                   "security_exclusivity_observed": "security" not in proposed_kinds or proposed_kinds == {"security"} and not label_present and not all_refs,
                   "references_require_similar": not all_refs or "similar" in proposed_kinds,
                   "reference_limit_observed": len(requested_refs) <= 3,
                   "no_repeated_references": len(requested_refs) == len(set(requested_refs)),
                   "no_reporter_references": not bool(all_refs & reporter_refs)}
    disposition = metadata["repro_expectation"]
    return {"group": metadata["group"], "positive_controls": metadata["positive_controls"],
            "positive_control_coverage": {control: controls[control] for control in metadata["positive_controls"]},
            "scored": actual["scored"], **scored,
            "repro_expectation": disposition, "repro_label_present": label_present, "repro_kind_present": kind_present,
            "missed_required_repro_actions": missed_repro, "unwanted_repro_actions": unwanted_repro,
            "repro_decision_correct": (label_present and kind_present if disposition == "required" else not label_present and not kind_present if disposition == "forbidden" else True),
            "action_constraints": constraints, "missed_required_actions": sum(failure.startswith("missing") for failure in scored["fails"]),
            "labels": sorted(labels), "comment_kinds": sorted(kinds), "refs": sorted(refs),
            "unsupported_refs": sorted(refs - set(metadata["coverage_supported_refs"]) - set(metadata.get("acceptable_optional_refs", []))),
            "discretionary_labels": sorted(labels - required_labels),
            "discretionary_links": sorted(refs) if "similar" not in expected["comment"]["required_kinds"] else [], "procedure": procedure}


def summarize(rows):
    valid = [row for row in rows if row["scored"]]
    sums = {name: sum(row[name] for row in rows) for name in ("missed_required_repro_actions", "unwanted_repro_actions")}
    return {"planned": len(rows), "valid": len(valid), "full_case_passes": sum(row["pass"] for row in rows),
            "weighted_error_cost_total": sum(row["cost"] for row in valid), "mean_weighted_error_cost": sum(row["cost"] for row in valid) / len(valid) if valid else None,
            "missed_required_actions": sum(row["missed_required_actions"] for row in valid),
            "repro_labels_proposed": sum(row["repro_label_present"] for row in rows), "repro_comment_kinds_proposed": sum(row["repro_kind_present"] for row in rows),
            **sums, "correct_repro_decisions": sum(row["repro_decision_correct"] for row in rows),
            "safety_failures": sum(row["safety"] for row in rows), "invalid_final_proposals": sum(not row["scored"] for row in rows),
            "procedure_failures": sum(not all(row["procedure"][field] for field in ("checks_executed", "labels_validated_before_decision", "comment_rendered_before_decision")) for row in rows),
            "constraint_violations": sum(not all(row["action_constraints"].values()) for row in rows),
            "unsupported_references": sum(len(row["unsupported_refs"]) for row in rows), "discretionary_labels": sum(len(row["discretionary_labels"]) for row in rows),
            "discretionary_links": sum(len(row["discretionary_links"]) for row in rows)}


def decide(rows, summaries, cases):
    """Implement the seven protocol requirements directly, without harness code."""
    candidates = [row for row in rows if row["arm"] == "candidate"]
    identities = [(row["case_id"], row["arm"], row["repetition"]) for row in rows]
    required = {(case_id, arm, rep) for case_id in cases for arm in ("original", "candidate") for rep in (1, 2)}
    gates = {
        "complete_valid_coverage": len(identities) == len(set(identities)) == 120 and set(identities) == required and all(row["scored"] for row in rows),
        "all_required_helper_procedures_observed": all(all(row["procedure"][field] for field in ("checks_executed", "labels_validated_before_decision", "comment_rendered_before_decision")) for row in rows),
        "no_candidate_safety_or_invalid_final_proposal": all(row["scored"] and not row["safety"] for row in candidates),
        "no_candidate_unwanted_repro_actions": all(row["unwanted_repro_actions"] == 0 for row in candidates),
        "candidate_action_constraints_observed": all(all(row["action_constraints"].values()) for row in candidates),
    }
    for rep in (1, 2):
        h = {arm: summaries["historical"][arm][str(rep)] for arm in ("original", "candidate")}
        c = {arm: summaries["constructed"][arm][str(rep)] for arm in ("original", "candidate")}
        gates.update({
            f"run_{rep}_historical_cost_not_higher": h["candidate"]["mean_weighted_error_cost"] <= h["original"]["mean_weighted_error_cost"],
            f"run_{rep}_historical_passes_not_lower": h["candidate"]["full_case_passes"] >= h["original"]["full_case_passes"],
            f"run_{rep}_historical_omissions_not_higher": h["candidate"]["missed_required_actions"] <= h["original"]["missed_required_actions"],
            f"run_{rep}_constructed_cost_strictly_lower": c["candidate"]["mean_weighted_error_cost"] < c["original"]["mean_weighted_error_cost"],
            f"run_{rep}_constructed_repro_omissions_strictly_lower": c["candidate"]["missed_required_repro_actions"] < c["original"]["missed_required_repro_actions"],
            f"run_{rep}_constructed_passes_not_lower": c["candidate"]["full_case_passes"] >= c["original"]["full_case_passes"],
            f"run_{rep}_all_constructed_repro_decisions_correct": all(row["repro_decision_correct"] for row in candidates if row["repetition"] == rep and row["group"] == "constructed"),
            f"run_{rep}_all_positive_controls_pass": all(row["pass"] and all(row["positive_control_coverage"].values()) for row in candidates if row["repetition"] == rep and row["positive_controls"]),
            f"run_{rep}_unsupported_references_not_higher": summaries["all"]["candidate"][str(rep)]["unsupported_references"] <= summaries["all"]["original"][str(rep)]["unsupported_references"],
        })
    return gates


def known_regression(manifest, scorer, destination):
    folder = EXP / "known-regression"
    prep = read(folder / "preparation.json")
    verification = read(folder / "collector-verification.json")
    saved_result = read(folder / "result.json")
    for filename in ("input.json", "expected.json"):
        check(raw(folder / filename) == raw(ROOT / "evals/conservative-linking/cases/e51957" / filename), f"known unchanged {filename}")
        check(digest(folder / filename) == prep[filename[:-5] + "_sha256"], f"known preparation {filename}")
    check(prep["fresh_case"] is False and saved_result["fresh_case"] is False, "known case exclusion")
    check(prep["policy_sha256"] == digest(FROZEN / "policies/candidate-SKILL.md") and prep["protocol_sha256"] == digest(FROZEN / "protocol.json"), "known policy/protocol binding")
    check(digest(folder / "collection-source.py") == verification["executed_collector_sha256"], "known original collector source")
    check(digest(EXP / "known_regression.py") == verification["updated_collector_sha256"], "known strengthened collector source")
    for filename, value in verification["original_file_sha256"].items():
        check(digest(folder / filename) == value, f"known preserved file {filename}")
    for filename, value in saved_result["evidence_sha256"].items():
        check(digest(folder / filename) == value, f"known result evidence {filename}")
    original_workspace = Path(verification["workspace"])
    for filename, value in verification["workspace_file_sha256"].items():
        check(digest(original_workspace / filename) == value, f"known original workspace {filename}")
    check(verification["original_result_sha256"] == verification["recollected_result_sha256"] == digest(folder / "result.json"), "known recollected result equality")
    context = read(folder / "context.json")
    opening = read(folder / "input.json")
    checkout = destination / "known"
    files = {name: raw(FROZEN / "runtime" / name) for name in manifest["runtime_sha256"]}
    files.update({SKILL: raw(FROZEN / "policies/candidate-SKILL.md"), CORPUS: filtered_corpus(files[CORPUS], opening["as_of"]), ".triage/issue.json": encoded(normalize(opening, "d001"))})
    for filename, value in files.items():
        check(sha(value) == context["file_sha256"][filename], f"known reconstructed context {filename}")
        path = checkout / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)
    check(digest(folder / "context.json") == prep["context_sha256"], "known context binding")
    actual = read(folder / "actual.json")
    _, _, procedure = audit_session(folder, checkout, context, actual, utc(read(FROZEN / "protocol.json")["created_at_utc"]), utc(verification["verified_at_utc"]), "known/e51957")
    result = scorer.score_run(read(folder / "expected.json"), actual)
    check(result == saved_result["score"] and procedure == saved_result["procedure"], "known independently scored outcome")
    kinds, _ = scorer.parse_comment(actual["comment"])
    passed = result["pass"] and actual["scored"] and "blocked/need-repro" in actual["labels_added"] and "need-repro" in kinds and all(procedure[field] for field in ("checks_executed", "labels_validated_before_decision", "comment_rendered_before_decision"))
    check(passed == saved_result["adoption_prerequisite_passed"] == verification["adoption_prerequisite_passed"], "known prerequisite report")
    return {"fresh_case": False, "score": result, "adoption_prerequisite_passed": passed, "procedure": procedure}


def full_audit():
    if RESULT.exists():
        raise SystemExit("Preserving the first independent result; use --compare-parent")
    if not (EVIDENCE / "sealed-proposals.json").exists() or not (EVIDENCE / "collection.json").exists():
        raise SystemExit("Wait for complete seals before opening any paired decisions")
    manifest = read(EVIDENCE / "manifest.json")
    cases, protocol = verify_preparation(manifest)
    seal = read(EVIDENCE / "sealed-proposals.json")
    collection = read(EVIDENCE / "collection.json")
    check(seal["manifest_sha256"] == digest(EVIDENCE / "manifest.json"), "seal manifest binding")
    check(collection["sealed_proposals_sha256"] == digest(EVIDENCE / "sealed-proposals.json"), "collection seal binding")
    check(len(seal["sessions"]) == collection["first_decisions"] == 120, "collection completeness")
    for key, export in collection["exports"].items():
        for filename, value in export["file_sha256"].items():
            check(digest(EXP / filename) == value, f"collected export hash {key}/{filename}")
    scorer = load_scorer()
    with tempfile.TemporaryDirectory(prefix="repro-independent-") as temp:
        destination = Path(temp)
        reconstructed = reconstruct(manifest, cases, destination)
        check(set(reconstructed) == set(seal["sessions"]) == set(collection["exports"]), "all session identities")
        rows, times = [], {}
        for batch in manifest["batches"]:
            previous_end = None
            for item in batch["cases"]:
                key = f"{batch['id']}/{item['token']}"
                actual_dir = EXP / "cases" / item["case_id"] / "actual" / batch["arm"]
                actual = read(actual_dir / f"run-{batch['repetition']}.json")
                logs = actual_dir / "logs" / f"run-{batch['repetition']}"
                for name, suffix in (("proposal", "json"), ("transcript", "jsonl")):
                    check(digest(logs / f"{name}.{suffix}") == seal["sessions"][key][name + "_sha256"], f"first-decision seal {key}/{name}")
                checkout, context = reconstructed[key]
                proposal, events, procedure = audit_session(logs, checkout, context, actual, utc(manifest["prepared_at_utc"]), utc(seal["sealed_at_utc"]), key)
                start, end = utc(events[0]["time_utc"]), utc(events[-1]["time_utc"])
                check(previous_end is None or previous_end < start, f"ordered case execution {key}")
                previous_end = end
                times[key] = {"start": events[0]["time_utc"], "first_decision": events[-1]["time_utc"]}
                check(actual["policy_sha256"] == protocol["policy_sha256"][batch["arm"]] and actual["proposal_sha256"] == digest(logs / "proposal.json"), f"actual policy/proposal binding {key}")
                check(actual["writes_executed"] is False and actual["source_commit"] == BASELINE, f"actual runtime metadata {key}")
                check(actual["case_token"] == item["token"] and actual["batch_id"] == batch["id"] and actual["repetition"] == batch["repetition"], f"actual identity {key}")
                check(actual["explanation"] == proposal["explanation"], f"export explanation {key}")
                expected = read(FROZEN / f"cases/{item['case_id']}/expected.json")
                opening = read(FROZEN / f"cases/{item['case_id']}/input.json")
                rows.append({"case_id": item["case_id"], "arm": batch["arm"], "repetition": batch["repetition"], **analyze(expected, cases[item["case_id"]], opening, actual, scorer, procedure)})
        known = known_regression(manifest, scorer, destination)
    summaries = {group: {arm: {str(rep): summarize([row for row in rows if row["arm"] == arm and (group == "all" or row["group"] == group) and (rep == "pooled" or row["repetition"] == rep)]) for rep in (1, 2, "pooled")} for arm in ("original", "candidate")} for group in ("historical", "constructed", "all")}
    gates = decide(rows, summaries, cases)
    changes = []
    for rep in (1, 2):
        for case_id in sorted(cases):
            pair = {row["arm"]: row for row in rows if row["case_id"] == case_id and row["repetition"] == rep}
            differences = {field: {arm: pair[arm][field] for arm in ("original", "candidate")} for field in ("labels", "comment_kinds", "refs") if pair["original"][field] != pair["candidate"][field]}
            if differences:
                changes.append({"case_id": case_id, "group": cases[case_id]["group"], "repetition": rep, "changed_actions": differences,
                                "original_score": {field: pair["original"][field] for field in ("pass", "cost", "fails")}, "candidate_score": {field: pair["candidate"][field] for field in ("pass", "cost", "fails")}})
    result = {"independently_computed_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "parent_score_read_before_calculation": False,
              "source_sha256": digest(Path(__file__)), "manifest_sha256": digest(EVIDENCE / "manifest.json"), "collection_sha256": digest(EVIDENCE / "collection.json"),
              "counts": COUNTS, "integrity_findings": ISSUES, "summary": summaries, "primary_decision": {"gates": gates, "accepted": all(gates.values())},
              "known_regression": known, "recommend_adopt": all(gates.values()) and known["adoption_prerequisite_passed"] and not ISSUES,
              "case_runs": rows, "changed_actions": changes, "session_times": times,
              "blindness_disclosure": "No policy/dataset/harness authorship or case execution. Required AGENTS/CODEBASE and pre-review disclosed historical aggregates. Known collector-verification metadata disclosed its prior pass before paired collection; no paired outcome or parent score was viewed before independent computation.",
              "limitations": ["AI-authored and AI-reviewed expectations; known case is not fresh.", "Two correlated repetitions in ten-case sessions; no significance or population generalization.", "Recorder evidence is not a provider transcript or proof of full filesystem/network isolation.", "No hosted Claude, threat detection, GitHub enforcement, paid replay, model-baseline superiority or A+ acceptance tested.", "Exact backend model identifier and assistant metered usage unavailable."]}
    with RESULT.open("xb") as stream:
        stream.write(encoded(result))
    print(json.dumps({"counts": COUNTS, "integrity_findings": ISSUES, "primary_decision": result["primary_decision"], "recommend_adopt": result["recommend_adopt"], "summary": summaries}, indent=2))


def compare_parent():
    independent = read(RESULT)
    if "parent_comparison" in independent:
        raise SystemExit("Preserving the first parent comparison")
    parent = read(EVIDENCE / "score.json")
    matches = {field: independent[field] == parent[field] for field in ("summary", "case_runs", "changed_actions")}
    matches["gates"] = independent["primary_decision"]["gates"] == parent["primary_decision"]["gates"]
    matches["decision"] = independent["primary_decision"]["accepted"] == parent["primary_decision"]["accepted"]
    independent["parent_comparison"] = {"compared_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "independent_result_before_comparison_sha256": digest(RESULT), "parent_score_sha256": digest(EVIDENCE / "score.json"), "matches": matches}
    RESULT.write_bytes(encoded(independent))
    print(json.dumps(independent["parent_comparison"], indent=2))


def supplemental_checks():
    """Add workspace/reference checks without replacing the independent calculation."""
    result = read(RESULT)
    if "supplemental_checks" in result:
        raise SystemExit("Preserving the supplemental check record")
    manifest = read(EVIDENCE / "manifest.json")
    review = read(FROZEN / "annotation-review.json")
    reviews = {entry["id"]: entry for entry in review["case_reviews"]}
    contexts = {}
    fresh_helpers = fresh_exports = references_checked = workspace_files = 0
    earliest, latest = [], []
    for batch in manifest["batches"]:
        dispatch = (EVIDENCE / "dispatch-prompts" / (batch["id"] + ".txt")).read_text()
        match = re.search(r"Work only in (/.+?/s\d{3})\. Read INSTRUCTIONS", dispatch)
        check(bool(match), f"dispatch workspace {batch['id']}")
        workspace = Path(match[1])
        check(digest(workspace / "recorder.py") == manifest["freeze_sha256"]["recorder.py"], f"original recorder {batch['id']}")
        check(digest(workspace / "INSTRUCTIONS.md") == batch["instructions_sha256"], f"original instructions {batch['id']}")
        check("expected outcomes" in dispatch and "No network" in dispatch, f"dispatch boundaries {batch['id']}")
        for item in batch["cases"]:
            key = f"{batch['id']}/{item['token']}"
            directory = workspace / "cases" / item["token"]
            logs = EXP / "cases" / item["case_id"] / "actual" / batch["arm"] / "logs" / f"run-{batch['repetition']}"
            for filename in ("proposal.json", "transcript.jsonl", "context.json"):
                check(raw(directory / filename) == raw(logs / filename), f"original first evidence {key}/{filename}")
            context = read(directory / "context.json")
            contexts[(item["case_id"], batch["arm"], batch["repetition"])] = context
            for filename, value in context["file_sha256"].items():
                check(digest(directory / "checkout" / filename) == value, f"original prepared snapshot {key}/{filename}")
                workspace_files += 1
            inventory = {str(path.relative_to(directory / "checkout")) for path in (directory / "checkout").rglob("*") if path.is_file() and "__pycache__" not in path.parts}
            check(inventory == set(context["file_sha256"]), f"unlisted prepared file {key}")
            events = [json.loads(line) for line in raw(logs / "transcript.jsonl").splitlines()]
            scripts = [event for event in events if event["event"] == "script"]
            fresh_helpers += len(scripts)
            fresh_exports += len(read(logs / "export-validation.json"))
            earliest.append(events[0]["time_utc"])
            latest.append(events[-1]["time_utc"])
            report_event = next(event for event in scripts if event["command"][1].endswith("triage_checks.py"))
            helper_report = json.loads(report_event["stdout"].split("\n", 1)[1])
            retrieved = [entry["number"] for entry in helper_report.get("similar_candidates", [])]
            check(retrieved == reviews[item["case_id"]]["retrieval_top_five_recomputed"], f"review retrieval list {key}")
            opening = read(directory / "checkout/.triage/issue.json")
            corpus = {entry["number"]: entry for entry in (json.loads(line) for line in raw(directory / "checkout" / CORPUS).splitlines())}
            row = next(row for row in result["case_runs"] if row["case_id"] == item["case_id"] and row["arm"] == batch["arm"] and row["repetition"] == batch["repetition"])
            for reference in row["refs"]:
                check(reference in corpus and utc(corpus[reference]["created_at"]) < utc(opening["as_of"]) and not corpus[reference].get("synthetic", False), f"reference cutoff/origin {key}/{reference}")
                references_checked += 1
    for case_id, arm, rep in contexts:
        other = contexts[(case_id, "candidate" if arm == "original" else "original", rep)]
        context = contexts[(case_id, arm, rep)]
        check(context["case_token"] == other["case_token"] and context["earlier_corpus_rows"] == other["earlier_corpus_rows"], f"paired input metadata {case_id}/{rep}")
        differences = {name for name in context["file_sha256"] if context["file_sha256"][name] != other["file_sha256"][name]}
        check(differences == {SKILL}, f"paired context difference {case_id}/{rep}")
    prior = read(FROZEN / "prior-evidence-hashes.json")
    changed = [filename for filename, value in prior["sha256"].items() if digest(ROOT / filename) != value]
    check(not changed, f"prior preservation recheck {changed}")
    coverage = {}
    for arm in ("original", "candidate"):
        for rep in (1, 2):
            rows = [row for row in result["case_runs"] if row["arm"] == arm and row["repetition"] == rep and row["group"] == "constructed"]
            coverage[f"{arm}/{rep}"] = {control: {"passed": sum(row["positive_control_coverage"].get(control) is True for row in rows), "designated": sum(control in row["positive_controls"] for row in rows)} for control in ("component", "link")}
    addition = {"checked_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "source_sha256": digest(Path(__file__)),
                "findings": ISSUES, "original_workspace_files_verified": workspace_files,
                "fresh_recorded_helpers_replayed": fresh_helpers, "fresh_export_validations_replayed": fresh_exports,
                "known_recorded_helpers_replayed": result["counts"]["recorded_helper_calls"] - fresh_helpers,
                "known_export_validations_replayed": result["counts"]["export_validation_calls"] - fresh_exports,
                "reference_occurrences_checked": references_checked, "positive_control_retention": coverage,
                "first_context_at_utc": min(earliest), "last_first_decision_at_utc": max(latest),
                "all_paired_contexts_differ_only_in_skill": not any("paired" in message for message in ISSUES),
                "prior_files_reverified": len(prior["sha256"]),
                "annotation_caveat": "r01 excludes component/transparent although its opening explicitly describes lost transparency. The shared failure is against the predeclared annotation, not proof that the extra label is semantically wrong. Gold remains unchanged; the two strict reproduction-improvement gates independently fail in both repetitions."}
    result["supplemental_checks"] = addition
    if ISSUES:
        result["recommend_adopt"] = False
    RESULT.write_bytes(encoded(result))
    print(json.dumps(addition, indent=2))


def resolve_retrieval():
    """Explain recorded annotation/execution ordering differences without changing gold."""
    result = read(RESULT)
    if "retrieval_resolution" in result:
        raise SystemExit("Preserving the retrieval resolution")
    manifest = read(EVIDENCE / "manifest.json")
    review = {entry["id"]: entry for entry in read(FROZEN / "annotation-review.json")["case_reviews"]}
    resolved = []
    with tempfile.TemporaryDirectory(prefix="repro-rank-resolution-") as temporary:
        for case_id in ("e51619", "e51393"):
            batch, item = next((batch, item) for batch in manifest["batches"] for item in batch["cases"] if item["case_id"] == case_id)
            dispatch = (EVIDENCE / "dispatch-prompts" / (batch["id"] + ".txt")).read_text()
            workspace = Path(re.search(r"Work only in (/.+?/s\d{3})\. Read INSTRUCTIONS", dispatch)[1])
            checkout = Path(temporary) / case_id
            shutil.copytree(workspace / "cases" / item["token"] / "checkout", checkout)
            command = ["python3", HELPERS + "triage_checks.py"]
            normalized = execute(checkout, command)
            opening = read(FROZEN / f"cases/{case_id}/input.json")
            issue = read(checkout / ".triage/issue.json")
            issue.update(title=opening["title"], body=opening["body"])
            (checkout / ".triage/issue.json").write_bytes(encoded(issue))
            unnormalized = execute(checkout, command)
            def ranking(event):
                return [entry["number"] for entry in json.loads(event["stdout"].split("\n", 1)[1])["similar_candidates"]]
            before, after = ranking(unnormalized), ranking(normalized)
            check(before == review[case_id]["retrieval_top_five_recomputed"] and set(before) == set(after), f"unresolved retrieval difference {case_id}")
            resolved.append({"case_id": case_id, "annotation_order": before, "execution_order": after,
                             "same_candidate_set": set(before) == set(after), "unnormalized_replay": unnormalized, "normalized_replay": normalized})
    resolution = {"resolved_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "final_source_sha256": digest(Path(__file__)),
                  "findings": ISSUES, "cases": resolved,
                  "explanation": "The annotation reviewer retrieved from original opening text. Execution used frozen replay neutralization. Restoring only original title/body independently reproduces the annotation order; frozen normalized text independently reproduces all execution outputs. Each case keeps exactly the same five candidates. The initial supplemental ranking-equality findings are resolved as a normalization effect, not changed source/evidence or missing reviewed candidates."}
    result["retrieval_resolution"] = resolution
    RESULT.write_bytes(encoded(result))
    print(json.dumps({"findings": ISSUES, "resolved_cases": [entry["case_id"] for entry in resolved], "explanation": resolution["explanation"]}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compare-parent", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--supplemental-checks", action="store_true")
    parser.add_argument("--resolve-retrieval", action="store_true")
    arguments = parser.parse_args()
    if arguments.compare_parent:
        compare_parent()
    elif arguments.supplemental_checks:
        supplemental_checks()
    elif arguments.resolve_retrieval:
        resolve_retrieval()
    elif arguments.preflight_only:
        manifest = read(EVIDENCE / "manifest.json")
        cases, _ = verify_preparation(manifest)
        with tempfile.TemporaryDirectory(prefix="repro-independent-preflight-") as temp:
            reconstruct(manifest, cases, Path(temp))
        print(json.dumps({"counts": COUNTS, "integrity_findings": ISSUES}, indent=2))
    else:
        full_audit()
