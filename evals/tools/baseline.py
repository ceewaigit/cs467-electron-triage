#!/usr/bin/env python3
"""Rule-based baseline: the same deterministic checks the skill runs, with fixed rules
in place of the model. If the agent does not beat this, the model adds nothing.

Rules (fixed before any agent run, not tuned on the golden cases):
  - skip when triage_checks says skip;
  - component: the first hint that matches in the title, else none;
  - need-repro: bug form, no gist, no other repo link, no code block, bot has not asked;
  - similar: the top candidate, only if it shares an error code or hex value and the
    reporter has not linked it;
  - redirect: security / site-policy / support from the keyword hints; upstream only when
    the reporter also answered "Yes" to the Chromium question; never third-party.

    python3 evals/tools/baseline.py   # writes cases/*/actual/baseline/run-1.json
"""
import json
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
CHECKS = ROOT / ".claude/skills/issue-triage/scripts/triage_checks.py"


def decide(r):
    if r["skip"]:
        return [], [], []
    labels, kinds, refs = [], [], []
    title_hits = [c["label"] for c in r["component_hints"] if c["in_title"]]
    if title_hits:
        labels.append(title_hits[0])
    hints = r["redirect_hints"]
    if "security" in hints:
        return labels, ["security"], []
    if (r["issue"]["form"] == "bug" and not r["repro"]["gist"] and not r["repro"]["other_repo_link"]
            and not r["repro"]["code_blocks"] and not r["bot_already"]["asked_for_supported_version"]):
        labels.append("blocked/need-repro")
        kinds.append("need-repro")
    top = r["similar_candidates"][:1]
    if top and not top[0]["already_linked_by_reporter"] and any(
            re.fullmatch(r"-?\d{6,}|0x[0-9a-f]{4,}", t) for t in top[0]["shared_terms"]):
        kinds.append("similar")
        refs.append(top[0]["number"])
    if "site-policy" in hints:
        kinds.append("site-policy")
    chromium = (re.search(r"### Does the issue also appear in Chromium / Google Chrome\?\s*\n\s*(\w+)",
                          r["issue"]["body"]) or [None, ""])[1]
    if "upstream" in hints and chromium == "Yes":
        kinds.append("upstream")
    if "support" in hints and r["issue"]["form"] == "unknown":
        kinds.append("support")
    return labels, kinds, refs


def comment(kinds, refs):
    if not kinds:
        return None
    args = [sys.executable, str(CHECKS.with_name("render_comment.py")), "--kinds", ",".join(kinds)]
    if refs:
        args += ["--refs", ",".join(map(str, refs))]
    out = subprocess.run(args, capture_output=True, text=True, check=True).stdout
    return out.split("-----BEGIN COMMENT-----\n")[1].split("\n-----END COMMENT-----")[0]


def main():
    for d in sorted((ROOT / "evals/golden/cases").iterdir()):
        c = json.loads((d / "input.json").read_text())
        issue = {"number": 0, "title": c["title"], "body": c["body"], "labels": c["labels_at_open"],
                 "state": "open", "author_association": c["author_association"], "as_of": c["as_of"]}
        with tempfile.NamedTemporaryFile("w", suffix=".json") as f:
            json.dump(issue, f)
            f.flush()
            out = subprocess.run([sys.executable, str(CHECKS), f.name], capture_output=True, text=True,
                                 check=True).stdout
        report = json.loads(out.split("\n", 1)[1])
        labels, kinds, refs = decide(report)
        act = {"labels_added": labels, "comment": comment(kinds, refs), "other_writes": []}
        dest = d / "actual" / "baseline"
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "run-1.json").write_text(json.dumps(act, indent=1, ensure_ascii=False) + "\n")
        print(f"{d.name:20} {labels} {kinds} {refs}")


if __name__ == "__main__":
    main()
