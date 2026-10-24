#!/usr/bin/env python3
"""Independent read-only checks of the pre-execution dataset; exclusive report output.

No policy, proposal, historical output, or maintainer-label events are consulted.
Run from any directory with --out pointing to a new JSON report.
"""
import argparse
import hashlib
import importlib.util
import json
import pathlib
import random
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[3]
BASE = ROOT / "evals/judgment-check"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def check():
    errors = []
    dataset = read(BASE / "dataset.json")
    selection = read(BASE / "selection.json")
    opening_source = ROOT / selection["source"]
    rows = [json.loads(line) for line in opening_source.read_text().splitlines() if line]
    by_number = {row["number"]: row for row in rows}
    prior = set()
    inspected = {}
    for path in sorted((ROOT / "evals").rglob("input.json")):
        if BASE in path.parents:
            continue
        item = read(path)
        numbers = set()
        match = re.search(r"electron/electron/issues/(\d+)", item.get("source", ""))
        if match:
            numbers.add(int(match.group(1)))
        if re.fullmatch(r"e\d+", item.get("id", "")):
            numbers.add(int(item["id"][1:]))
        if isinstance(item.get("source_number"), int):
            numbers.add(item["source_number"])
        prior.update(numbers)
        inspected[str(path.relative_to(ROOT))] = (sha(path), sorted(numbers))
    recorded = {item["path"]: (item["sha256"], item["excluded_numbers"])
                for item in selection["previous_case_inputs_inspected"]}
    if inspected != recorded or sorted(prior) != selection["previous_real_numbers_excluded"]:
        errors.append("prior-input exclusion set or bytes differ")
    if sha(opening_source) != selection["source_sha256"]:
        errors.append("opening dataset hash differs")
    rng = random.Random(4672028)
    months = {}
    selected = []
    for month in ("2026-04", "2026-05", "2026-06"):
        eligible = sorted(row["number"] for row in rows
                          if row["created_at"].startswith(month)
                          and row.get("author_type") != "Bot"
                          and not (row.get("author") or "").lower().endswith("[bot]")
                          and row["author_association"].upper() not in {"MEMBER", "OWNER", "COLLABORATOR"}
                          and row["number"] not in prior)
        drawn = rng.sample(eligible, 4)
        if selection["months"][month] != {"eligible_sorted": eligible, "selected_in_draw_order": drawn}:
            errors.append(f"selection differs for {month}")
        selected.extend(drawn)
        months[month] = {"eligible_count": len(eligible), "selected": drawn}
    if selection["case_order"] != [f"e{number}" for number in selected]:
        errors.append("historical case order differs")
    raw_openings = {}
    for path in sorted((ROOT / "evals/data/raw").glob("2026-0[456]-*.json")):
        for row in read(path)["data"]["search"]["nodes"]:
            if row["number"] not in selected:
                continue
            # Deliberately do not read labeledAtOpen; it includes later labels.
            edits = sorted(row["userContentEdits"]["nodes"], key=lambda item: item["editedAt"])
            renames = sorted(row["timelineItems"]["nodes"], key=lambda item: item["createdAt"])
            raw_openings[row["number"]] = {
                "body": edits[0]["diff"] if edits else row["body"],
                "title": renames[0]["previousTitle"] if renames else row["title"],
                "edited_revision_at_creation": edits[0]["editedAt"] == row["createdAt"] if edits else None,
            }
    commit_corpus = subprocess.check_output(
        ["git", "show", dataset["runtime_commit"] + ":data/issue-corpus.jsonl"], cwd=ROOT)
    if hashlib.sha256(commit_corpus).hexdigest() != dataset["provenance"]["base_corpus_sha256"]:
        errors.append("baseline commit corpus hash differs")
    corpus_lines = commit_corpus.decode().splitlines()
    allowed = set((ROOT / ".claude/skills/issue-triage/assets/allowed-labels.txt").read_text().splitlines())
    spec = importlib.util.spec_from_file_location("frozen_score", ROOT / "evals/tools/score.py")
    scorer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scorer)
    summaries = []
    for case in dataset["cases"]:
        case_dir = BASE / "cases" / case["id"]
        inp, exp, annotation = (read(case_dir / name) for name in ("input.json", "expected.json", "annotation.json"))
        for name, metadata in case["files"].items():
            if sha(BASE / metadata["path"]) != metadata["sha256"]:
                errors.append(f"{case['id']}: {name} hash differs")
        if annotation["acceptable_outcomes"] != {key: exp[key] for key in ("labels", "comment", "decision")}:
            errors.append(f"{case['id']}: annotation and expected disagree")
        accepted_labels = set(exp["labels"]["required"] + exp["labels"]["acceptable"]
                              + sum(exp["labels"]["one_of"], []))
        if accepted_labels - allowed:
            errors.append(f"{case['id']}: unexpected allowed label")
        additions = case_dir / "corpus-additions.jsonl"
        corpus = "".join(line + "\n" for line in corpus_lines
                         if line.strip() and json.loads(line)["created_at"] < inp["as_of"])
        if additions.exists():
            corpus += additions.read_text()
        corpus_rows = [json.loads(line) for line in corpus.splitlines() if line.strip()]
        numbers = {row["number"] for row in corpus_rows}
        if hashlib.sha256(corpus.encode()).hexdigest() != case["corpus_sha256"]:
            errors.append(f"{case['id']}: corpus hash differs")
        if len(corpus_rows) != case["corpus_rows"] or len(numbers) != len(corpus_rows):
            errors.append(f"{case['id']}: corpus count or uniqueness differs")
        if any(row["created_at"] >= inp["as_of"] for row in corpus_rows):
            errors.append(f"{case['id']}: future corpus row")
        supported = case["coverage_supported_refs"] + case["acceptable_optional_refs"] + case["semantic_supported_refs"]
        if set(supported) - numbers:
            errors.append(f"{case['id']}: missing supported reference")
        if case["group"] == "historical":
            row = by_number[int(case["id"][1:])]
            for key in ("title", "body", "author_association", "labels_at_open", "body_source"):
                if inp[key] != row[key]:
                    errors.append(f"{case['id']}: opening field {key} differs")
            raw = raw_openings[row["number"]]
            if inp["as_of"] != row["created_at"] or inp["body"] != raw["body"] or inp["title"] != raw["title"]:
                errors.append(f"{case['id']}: raw opening text/time differs")
            if raw["edited_revision_at_creation"] is False:
                errors.append(f"{case['id']}: oldest edited body is later than creation")
        kinds = exp["comment"]["required_kinds"]
        comment = ("triage: kinds=" + ",".join(kinds) + " refs="
                   + ",".join("#" + str(ref) for ref in exp["comment"]["refs_any"][:1])) if kinds else None
        ideal = {"labels_added": exp["labels"]["required"] + [group[0] for group in exp["labels"]["one_of"]],
                 "comment": comment, "other_writes": []}
        if not scorer.score_run(exp, ideal)["pass"]:
            errors.append(f"{case['id']}: minimal expected output cannot pass frozen scorer")
        summaries.append({"id": case["id"], "group": case["group"], "decision": exp["decision"],
                          "repro": case["repro_expectation"], "required_link_refs": case["coverage_supported_refs"],
                          "input_sha256": sha(case_dir / "input.json"), "expected_sha256": sha(case_dir / "expected.json")})
    revisions = read(BASE / "selection/preexecution-revisions.json")
    for item in revisions["files"]:
        if sha(BASE / item["path"]) != item["revised_sha256"] or sha(BASE / item["preserved_draft"]) != item["original_sha256"]:
            errors.append(f"revision preservation mismatch: {item['path']}")
    return {"passed": not errors, "errors": errors, "dataset_sha256": sha(BASE / "dataset.json"),
            "selection_sha256": sha(BASE / "selection.json"), "runtime_commit": dataset["runtime_commit"],
            "months": months, "prior_identifiers": len(prior), "cases": summaries,
            "scorer_sha256": sha(ROOT / "evals/tools/score.py"), "audit_source_sha256": sha(pathlib.Path(__file__))}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=pathlib.Path)
    args = parser.parse_args()
    result = check()
    with args.out.open("x") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"passed": result["passed"], "errors": result["errors"], "dataset_sha256": result["dataset_sha256"]}))
