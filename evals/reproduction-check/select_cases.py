#!/usr/bin/env python3
"""Freeze fresh Q2 IDs before an annotator sees selected opening text.

Only opening-state rows and prior input identifiers are read; no prior expected
outcome, actual output, score or maintainer history is inspected. Existing
selection and input files are never overwritten.
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
SEED = 4672027
MONTHS = ("2026-04", "2026-05", "2026-06")


def dump(path, value):
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def main():
    previous = set()
    inspected = []
    for path in sorted((ROOT / "evals").rglob("input.json")):
        if OUT in path.parents:
            continue
        case = json.loads(path.read_text())
        match = re.search(r"electron/electron/issues/(\d+)", case.get("source", ""))
        if match:
            previous.add(int(match.group(1)))
        elif re.fullmatch(r"e\d+", case.get("id", "")):
            previous.add(int(case["id"][1:]))
        if isinstance(case.get("source_number"), int):
            previous.add(case["source_number"])
        inspected.append(str(path.relative_to(ROOT)))
    raw = SOURCE.read_bytes()
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    by_number = {row["number"]: row for row in rows}
    rng = random.Random(SEED)
    months, selected = {}, []
    for month in MONTHS:
        eligible = sorted(row["number"] for row in rows
                          if row["created_at"].startswith(month)
                          and row.get("author_type") != "Bot"
                          and not (row.get("author") or "").lower().endswith("[bot]")
                          and row["author_association"].upper() not in {"MEMBER", "OWNER", "COLLABORATOR"}
                          and row["number"] not in previous)
        sample = rng.sample(eligible, 6)
        months[month] = {"eligible_sorted": eligible, "selected_in_draw_order": sample}
        selected.extend(sample)
    targets = [OUT / "cases" / f"e{n}" / "input.json" for n in selected]
    if any(path.exists() for path in targets) or (OUT / "selection.json").exists():
        raise SystemExit("Refusing to overwrite the frozen selection")
    # Persist selection before emitting or presenting any selected opening text.
    dump(OUT / "selection.json", {
        "selected_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "seed": SEED,
        "algorithm": "one random.Random(4672027), sample(sorted(eligible_issue_numbers), 6) for April, May, June in that order",
        "source": str(SOURCE.relative_to(ROOT)),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "previous_case_inputs_inspected": inspected,
        "previous_real_numbers_excluded": sorted(previous),
        "exclusion_scope": "All input.json files anywhere under evals, including conservative-linking and frozen copies; only identifiers extracted",
        "months": months,
        "case_order": [f"e{n}" for n in selected],
        "retention": "All 18 selected cases retained without redraw or replacement",
        "author_metadata": {f"e{n}": {key: by_number[n].get(key) for key in ("author", "author_type", "edit_count")} for n in selected},
    })
    for number, target in zip(selected, targets):
        row = by_number[number]
        target.parent.mkdir(parents=True, exist_ok=True)
        dump(target, {"id": f"e{number}", "set": "fresh-q2-real",
                      "source": f"https://github.com/electron/electron/issues/{number}",
                      "as_of": row["created_at"], "author_association": row["author_association"],
                      "title": row["title"], "body": row["body"],
                      "labels_at_open": row["labels_at_open"], "body_source": row["body_source"]})
    print(json.dumps({m: d["selected_in_draw_order"] for m, d in months.items()}, indent=2))


if __name__ == "__main__":
    main()
