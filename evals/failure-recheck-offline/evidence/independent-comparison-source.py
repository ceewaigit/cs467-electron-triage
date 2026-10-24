#!/usr/bin/env python3
"""Compare the five older outputs only after independent results were saved."""
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
evidence = Path(__file__).resolve().parent
repo = evidence.parents[2]
assert (evidence / "independent-review.json").is_file()
spec = importlib.util.spec_from_file_location("frozen_comparison_scorer", evidence / "frozen/score.py")
scorer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scorer)
rows = {}
for cid in ("e52255", "e52266", "e52385", "e52463", "e53734"):
    old_path = repo / "evals/golden/cases" / cid / "actual/assistant-dry-run/run-1.json"
    new_path = evidence.parent / "cases" / cid / "actual/latest/run-1.json"
    expected = json.loads((evidence / "frozen/cases" / cid / "expected.json").read_text())
    old, new = (json.loads(path.read_text()) for path in (old_path, new_path))
    rows[cid] = {"old_score": scorer.score_run(expected, old), "new_score": scorer.score_run(expected, new),
                 "old_output_sha256": hashlib.sha256(old_path.read_bytes()).hexdigest(),
                 "new_output_sha256": hashlib.sha256(new_path.read_bytes()).hexdigest(),
                 "old_source_commit": old["source_commit"], "new_source_commit": new["source_commit"],
                 "action_fields_unchanged": all(old[key] == new[key] for key in ("labels_added", "comment", "other_writes")),
                 "old_labels": old["labels_added"], "new_labels": new["labels_added"],
                 "old_kinds_and_refs": [sorted(part) for part in scorer.parse_comment(old["comment"])],
                 "new_kinds_and_refs": [sorted(part) for part in scorer.parse_comment(new["comment"])]}
report = {"compared_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
          "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          "independent_review_sha256": hashlib.sha256((evidence / "independent-review.json").read_bytes()).hexdigest(),
          "old_passes": sum(row["old_score"]["pass"] for row in rows.values()),
          "new_passes": sum(row["new_score"]["pass"] for row in rows.values()),
          "old_weighted_error_cost_total": sum(row["old_score"]["cost"] for row in rows.values()),
          "new_weighted_error_cost_total": sum(row["new_score"]["cost"] for row in rows.values()),
          "cases": rows}
with (evidence / "independent-comparison.json").open("x") as stream:
    json.dump(report, stream, indent=2, ensure_ascii=False)
    stream.write("\n")
print(json.dumps(report, indent=2))
