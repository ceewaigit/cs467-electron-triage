#!/usr/bin/env python3
"""Held-out check of the component keyword table (references/components.json).

The table was written after the golden inputs had been read, so its hit rate on the golden
cases may be optimistic. This measures it on Q3 2026 outside issues that are NOT golden cases
and that a maintainer gave a component label within 14 days (labels from the extract below).

    python3 evals/tools/hint_holdout.py evals/need/raw/issues

This diagnostic uses the research snapshot's current title/body, which may
include later edits. It is a sanity check of the keyword table, not an
opening-state historical evaluation or a held-out test of the full agent.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".claude/skills/issue-triage/scripts"))
sys.path.insert(0, str(ROOT / "evals/tools"))
from agreement import extract  # noqa: E402

comp_map = json.loads((ROOT / ".claude/skills/issue-triage/references/components.json").read_text())
golden = {int(json.loads((d / "input.json").read_text())["source"].rsplit("/", 1)[1])
          for d in (ROOT / "evals/golden/cases").iterdir() if not d.name.startswith("a")}
nodes = {}
for f in pathlib.Path(sys.argv[1]).glob("*.json"):
    for n in json.loads(f.read_text())["data"]["search"]["nodes"]:
        if n["authorAssociation"] not in ("MEMBER", "OWNER", "COLLABORATOR") and n["number"] not in golden:
            nodes[n["number"]] = n
acts = extract(sys.argv[1], set(nodes))
# Only issues with an observed human component label can supply a comparison.
# The two counts distinguish a usable first suggestion from a broad candidate list.
top1 = any1 = total = 0
for num, a in acts.items():
    truth = {x["label"] for x in a["maintainer_labels"] if x["label"].startswith("component/")}
    if not truth:
        continue
    n = nodes[int(num)]
    title, text = n["title"].lower(), (n["title"] + "\n" + (n["body"] or "")).lower()
    hits = []
    for lab, kws in comp_map.items():
        if lab.startswith("_"):
            continue
        m = [k for k in kws if k.lower() in text]
        if m:
            hits.append((not any(k.lower() in title for k in m), -len(m), lab))
    hits = [h[2] for h in sorted(hits)]
    total += 1
    top1 += bool(hits[:1] and hits[0] in truth)
    any1 += bool(set(hits[:6]) & truth)
print(json.dumps({"held_out_issues_with_maintainer_component": total,
                  "top_hint_correct": top1, "truth_in_top6_hints": any1}, indent=1))
