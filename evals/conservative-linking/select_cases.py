#!/usr/bin/env python3
"""Select fresh Q2 opening-state inputs without reading outputs or later history.

Run before annotation; refuses to overwrite any selected case input. Only the
saved opening-state JSONL and prior case input.json identifiers are read.
"""
import datetime
import hashlib
import json
import pathlib
import random
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).resolve().parent
SOURCE = ROOT / "evals/data/electron_issues.jsonl"
SEED = 4672026
MONTHS = ("2026-04", "2026-05", "2026-06")


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def main():
    previous = set()
    inspected_inputs = []
    for path in sorted((ROOT / "evals").rglob("input.json")):
        if OUT in path.parents or {"actual", "results", "logs"} & set(path.parts):
            continue
        case = json.loads(path.read_text())
        match = re.search(r"electron/electron/issues/(\d+)", case.get("source", ""))
        if match:
            previous.add(int(match.group(1)))
        elif re.fullmatch(r"e\d+", case.get("id", "")):
            previous.add(int(case["id"][1:]))
        inspected_inputs.append(str(path.relative_to(ROOT)))
    rows = [json.loads(line) for line in SOURCE.read_text().splitlines()]
    by_number = {row["number"]: row for row in rows}
    rng = random.Random(SEED)
    months = {}
    selected = []
    for month in MONTHS:
        eligible = sorted(row["number"] for row in rows
                          if row["created_at"].startswith(month)
                          and row.get("author_type") != "Bot"
                          and not (row.get("author") or "").lower().endswith("[bot]")
                          and row["author_association"].upper() not in {"MEMBER", "OWNER", "COLLABORATOR"}
                          and row["number"] not in previous)
        sample = rng.sample(eligible, 8)
        months[month] = {"eligible_sorted": eligible, "selected_in_draw_order": sample}
        selected.extend(sample)
    targets = [OUT / "cases" / f"e{number}" / "input.json" for number in selected]
    if any(path.exists() for path in targets) or (OUT / "selection.json").exists():
        raise SystemExit("Refusing to overwrite the existing selection")
    for number, target in zip(selected, targets):
        row = by_number[number]
        target.parent.mkdir(parents=True, exist_ok=True)
        dump(target, {"id": f"e{number}", "set": "fresh-q2-real",
                      "source": f"https://github.com/electron/electron/issues/{number}",
                      "as_of": row["created_at"], "author_association": row["author_association"],
                      "title": row["title"], "body": row["body"],
                      "labels_at_open": row["labels_at_open"], "body_source": row["body_source"]})
    dump(OUT / "selection.json", {
        "selected_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "seed": SEED, "algorithm": "one random.Random(4672026), sample(sorted(eligible_issue_numbers), 8) for April, May, June in that order",
        "source": str(SOURCE.relative_to(ROOT)), "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "previous_case_inputs_inspected": inspected_inputs,
        "previous_real_numbers_excluded": sorted(previous), "months": months,
        "case_order": [f"e{number}" for number in selected],
        "retention": "All selected cases retained regardless of difficulty; no redraws",
        "author_metadata": {f"e{n}": {key: by_number[n].get(key) for key in ("author", "author_type", "edit_count")} for n in selected},
    })
    print(json.dumps({month: detail["selected_in_draw_order"] for month, detail in months.items()}, indent=2))


if __name__ == "__main__":
    main()
