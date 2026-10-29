#!/usr/bin/env python3
"""Build a copy of a run set that scores what the agent asked for instead of what landed.

The recorded runs (cases/*/actual/<runs>/run-*.json) hold the issue's state after the run.
In a few runs a label the agent requested never reached the issue for reasons outside the
model (see results/delivery-final.md). This script reads each run's agent_output.json, puts
the requested labels in labels_added, and writes the result to actual/<runs>-requested/ so
the frozen score.py can score it unchanged. Comments are left as recorded: in every template
run the posted comment matched the requested kinds and references.

    python3 evals/tools/requested_view.py --runs final
    python3 evals/tools/score.py --runs final-requested

Side effects: overwrites cases/*/actual/<runs>-requested/ and prints each changed run.
"""
import argparse
import json
import pathlib

GOLDEN = pathlib.Path(__file__).resolve().parents[1] / "golden"


def requested_labels(agent_output):
    """Every label named in the agent's add_labels calls, plain or {name, rationale} form."""
    labels = []
    for item in agent_output.get("items", []):
        if item.get("type") == "add_labels":
            for label in item.get("labels", []):
                name = label["name"] if isinstance(label, dict) else label
                if name not in labels:
                    labels.append(name)
    return labels


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True)
    a = ap.parse_args()
    for run in sorted(GOLDEN.glob(f"cases/*/actual/{a.runs}/run-*.json")):
        record = json.loads(run.read_text())
        output = run.parent / "logs" / run.stem / "agent_output.json"
        if output.exists():
            wanted = requested_labels(json.loads(output.read_text()))
            if set(wanted) != set(record.get("labels_added") or []):
                print(f"{run.parts[-4]} {run.stem}: delivered {record.get('labels_added')}, requested {wanted}")
            record = record | {"labels_added": wanted, "source": f"requested view of {a.runs}"}
        dest = run.parent.parent / f"{a.runs}-requested" / run.name
        dest.parent.mkdir(exist_ok=True)
        dest.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
