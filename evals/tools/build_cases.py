#!/usr/bin/env python3
"""Write evals/golden/cases/<id>/input.json for every real case.

Inputs are rebuilt from evals/data/electron_issues.jsonl (opening title and
body, labels the issue form and Electron's bots applied in the first two
minutes). Nothing that happened after the issue was opened is copied.

Usage: python3 evals/tools/build_cases.py
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
CASES = ROOT / "golden" / "cases"

CURATED = [52232, 54317, 53213, 53939, 52266, 52385, 52463, 52255, 53610,
           53024, 52821, 53734, 52427, 52643, 53545, 54123, 53175]
# random.Random(467).sample over the 175 Q3 non-bot issues outside CURATED
RANDOM = [52263, 52334, 52383, 52738, 53286, 53376, 53747, 54035]


def main():
    rows = {r["number"]: r for r in map(json.loads, (ROOT / "data" / "electron_issues.jsonl").open())}
    for group, numbers in (("curated", CURATED), ("random", RANDOM)):
        for n in numbers:
            r = rows[n]
            d = CASES / f"e{n}"
            d.mkdir(parents=True, exist_ok=True)
            case = {
                "id": f"e{n}",
                "set": group,
                "source": f"https://github.com/electron/electron/issues/{n}",
                "as_of": r["created_at"],
                "author_association": r["author_association"],
                "title": r["title"],
                "body": r["body"],
                "labels_at_open": r["labels_at_open"],
                "body_source": r["body_source"],
            }
            (d / "input.json").write_text(json.dumps(case, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {len(CURATED) + len(RANDOM)} real cases")


if __name__ == "__main__":
    main()
