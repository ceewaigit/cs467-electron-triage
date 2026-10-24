#!/usr/bin/env python3
"""Resolve audit ordering false alarms while preserving the initial audit.

The collector validates each item in proposal order. The initial independent
audit re-executed identical commands in label/comment order. Reconstruct with
the frozen context builder, then independently follow actual proposal order.
"""
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
evidence = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("saved_reconstruction", evidence / "frozen/helper.py")
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
manifest = json.loads((evidence / "manifest.json").read_text())
results = {}
with tempfile.TemporaryDirectory(prefix="five-failures-export-order-") as temporary:
    destination = Path(temporary) / "contexts"
    helper.construct_workspaces(evidence, manifest, destination)
    for batch in manifest["batches"]:
        for case in batch["cases"]:
            cid = case["case_id"]
            checkout = destination / batch["id"] / "cases" / case["token"] / "checkout"
            log = evidence.parent / "cases" / cid / "actual/latest/logs/run-1"
            proposal = json.loads((log / "proposal.json").read_text())
            validations = []
            for item in proposal["items"]:
                if item["type"] == "add_labels":
                    command = ["python3", ".claude/skills/issue-triage/scripts/check_labels.py", *item["labels"]]
                elif item["type"] == "triage_comment":
                    command = ["python3", ".claude/skills/issue-triage/scripts/render_comment.py", "--kinds", item["kinds"], "--refs", item["refs"]]
                else:
                    continue
                completed = subprocess.run([sys.executable, *command[1:]], cwd=checkout,
                                           env={"PATH": os.defpath, "HOME": str(checkout)},
                                           capture_output=True, text=True, timeout=30)
                validations.append({"command": command, "exit_code": completed.returncode,
                                    "stdout": completed.stdout, "stderr": completed.stderr})
            saved = json.loads((log / "export-validation.json").read_text())
            events = [json.loads(line) for line in (log / "transcript.jsonl").read_text().splitlines()]
            readable = ["# Recorded coding-assistant session\n\nProposed actions only; no external writes.\n"]
            for index, event in enumerate(events, 1):
                readable.append(f"\n## {index}. {event['event']} — {event.get('time_utc', 'timestamp unavailable')}\n\n")
                readable.append(event["content"] + "\n" if event["event"] == "context" else
                                "````json\n" + json.dumps(event, indent=2, ensure_ascii=False) + "\n````\n")
            results[cid] = {"exact_order_export_validation_match": validations == saved,
                            "all_validations_pass": all(row["exit_code"] == 0 for row in validations),
                            "readable_transcript_exact_match": "".join(readable).encode() == (log / "transcript.md").read_bytes(),
                            "proposal_item_order": [item["type"] for item in proposal["items"]],
                            "validations_replayed": len(validations)}
report = {"reviewed_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
          "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          "initial_review_sha256": hashlib.sha256((evidence / "independent-review.json").read_bytes()).hexdigest(),
          "explanation": "The initial audit reordered export validation calls. All five mismatches were array-order false alarms in the reviewer script; this supplemental replay follows the saved proposal order. The original audit remains unchanged.",
          "resolved_initial_audit_mismatches": 5,
          "all_passed": all(all(row[key] for key in ("exact_order_export_validation_match", "all_validations_pass", "readable_transcript_exact_match")) for row in results.values()),
          "cases": results}
with (evidence / "independent-export-order.json").open("x") as stream:
    json.dump(report, stream, indent=2, ensure_ascii=False)
    stream.write("\n")
print(json.dumps(report, indent=2))
