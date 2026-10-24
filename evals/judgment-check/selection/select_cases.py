#!/usr/bin/env python3
"""Freeze an independent, stratified Q2 opening-state sample; never read outcomes."""
import datetime
import hashlib
import json
import pathlib
import random
import re

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = ROOT / "evals/judgment-check"
SOURCE = ROOT / "evals/data/electron_issues.jsonl"
BASELINE = "90724fea4152861499063b4f163d84c28348b0d3"
SEED = 4672028


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main():
    prior, sources = set(), []
    for path in sorted((ROOT / "evals").rglob("input.json")):
        if OUT in path.parents:
            continue
        raw = path.read_bytes()
        item = json.loads(raw)
        numbers = set()
        match = re.search(r"electron/electron/issues/(\d+)", item.get("source", ""))
        if match:
            numbers.add(int(match.group(1)))
        if re.fullmatch(r"e\d+", item.get("id", "")):
            numbers.add(int(item["id"][1:]))
        if isinstance(item.get("source_number"), int):
            numbers.add(item["source_number"])
        prior.update(numbers)
        sources.append({"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(raw).hexdigest(),
                        "excluded_numbers": sorted(numbers)})
    raw = SOURCE.read_bytes()
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    by_number = {row["number"]: row for row in rows}
    rng = random.Random(SEED)
    months, selected = {}, []
    for month in ("2026-04", "2026-05", "2026-06"):
        eligible = sorted(row["number"] for row in rows if row["created_at"].startswith(month)
                          and row.get("author_type") != "Bot"
                          and not (row.get("author") or "").lower().endswith("[bot]")
                          and row["author_association"].upper() not in {"MEMBER", "OWNER", "COLLABORATOR"}
                          and row["number"] not in prior)
        chosen = rng.sample(eligible, 4)
        months[month] = {"eligible_sorted": eligible, "selected_in_draw_order": chosen}
        selected.extend(chosen)
    selection = OUT / "selection.json"
    targets = [OUT / "cases" / f"e{n}" / "input.json" for n in selected]
    if selection.exists() or any(path.exists() for path in targets):
        raise SystemExit("Refusing to overwrite the frozen selection or opening inputs")
    dump(selection, {
        "selected_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "runtime_commit": BASELINE, "seed": SEED,
        "algorithm": "one random.Random(4672028), sample(sorted(eligible_issue_numbers), 4) for April, May, June in order",
        "source": str(SOURCE.relative_to(ROOT)), "source_sha256": hashlib.sha256(raw).hexdigest(),
        "exclusion_scope": "All input.json under evals outside this namespace; only source/id/source_number identifiers inspected, including golden, all rechecks, both earlier fresh experiments, frozen copies and known regressions",
        "eligibility": "Q2 2026 creation date; non-bot author; association not MEMBER, OWNER, COLLABORATOR; no prior input identifier",
        "previous_case_inputs_inspected": sources, "previous_real_numbers_excluded": sorted(prior),
        "months": months, "case_order": [f"e{n}" for n in selected],
        "retention": "All 12 selected opening inputs retained without redraw, including ambiguous cases",
        "author_metadata": {f"e{n}": {key: by_number[n].get(key) for key in ("author", "author_type", "edit_count")} for n in selected},
    })
    for n, target in zip(selected, targets):
        row = by_number[n]
        dump(target, {"id": f"e{n}", "set": "fresh-q2-real", "source": f"https://github.com/electron/electron/issues/{n}",
                      "as_of": row["created_at"], "author_association": row["author_association"],
                      "title": row["title"], "body": row["body"], "labels_at_open": row["labels_at_open"],
                      "body_source": row["body_source"]})
    print(json.dumps({month: value["selected_in_draw_order"] for month, value in months.items()}, indent=2))


if __name__ == "__main__":
    main()
