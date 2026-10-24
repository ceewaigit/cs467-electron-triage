#!/usr/bin/env python3
"""Read-only publication audit; writes one new result file beside this source."""
import collections
import datetime
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).with_name("independent-publication-check.json")
DOCS = {"DESIGN.md", "README.md", "data/README.md", "docs/CODEBASE.md"}
READ_ME = "evals/judgment-check/README.md"


def read_json(path):
    return json.loads((ROOT / path).read_text())


def digest(data):
    return hashlib.sha256(data).hexdigest()


def compare(entries):
    missing = [name for name in entries if not (ROOT / name).is_file()]
    changed = [name for name, expected in entries.items()
               if (ROOT / name).is_file() and digest((ROOT / name).read_bytes()) != expected]
    return {"count": len(entries), "missing": missing, "changed": changed}


report = {"checked_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "scope": "Documentation publication, file preservation, saved runtime and publication safety; no new evaluation",
          "network_calls": 0, "provider_calls": 0, "workflow_dispatches": 0}
prior = read_json("evals/judgment-check/prior-evidence-hashes.json")
report["prior_files"] = compare(prior["tracked_worktree_sha256"])
report["prior_files"]["only_authorized_documentation_changed"] = (
    not report["prior_files"]["missing"] and set(report["prior_files"]["changed"]) == DOCS)
before = read_json("evals/judgment-check/publication/inventory-before.json")
report["experiment_files"] = compare(before["sha256"])
report["experiment_files"]["only_publication_readme_changed"] = (
    not report["experiment_files"]["missing"] and set(report["experiment_files"]["changed"]) == {READ_ME})

# Independently establish that the supplied old inventory describes its named commit.
archive = subprocess.check_output(["git", "archive", prior["source_commit"]], cwd=ROOT)
with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as saved:
    commit_hashes = {m.name: digest(saved.extractfile(m).read()) for m in saved if m.isfile()}
report["prior_inventory_matches_named_commit"] = commit_hashes == prior["tracked_worktree_sha256"]

live = read_json("evals/failure-recheck-live-3/manifest.json")
report["live_runtime"] = compare(live["runtime_sha256"])
report["preparation_script_sha256"] = digest((ROOT / "scripts/prepare_agent_context.py").read_bytes())
report["live_source_commit"] = live["source_commit"]
report["live_outcomes"] = []
for path in sorted((ROOT / "evals/failure-recheck-live-3/cases").glob("*/actual/failure-recheck-live-3/run-1.json")):
    row = json.loads(path.read_text())
    report["live_outcomes"].append({"case": path.parents[2].name, "conclusion": row["conclusion"],
                                    "head_sha": row["head_sha"], "run_id": row["run_id"]})

design = (ROOT / "DESIGN.md").read_text()
report["design"] = {"line_count": len(design.splitlines()), "last_section": design.rsplit("\n## ", 1)[-1].splitlines()[0]}
report["candidate_rejected"] = read_json("evals/judgment-check/evidence/decision.json")["accepted"] is False
report["first_decision_counts"] = {}
for namespace, path in [("fresh", "evals/judgment-check/evidence/score.json"),
                        ("known", "evals/judgment-check/known-cases/evidence/score.json")]:
    score = read_json(path)
    rows = score["case_runs"]
    report["first_decision_counts"][namespace] = {"total": len(rows), "policies": {}}
    for arm in ["original", "candidate"]:
        selected = [r for r in rows if r["arm"] == arm]
        report["first_decision_counts"][namespace]["policies"][arm] = {
            "count": len(selected), "passes": sum(r["pass"] for r in selected),
            "weighted_cost": sum(r["cost"] for r in selected)}

docs = sorted(DOCS | {READ_ME, "docs/DRIFT_REVIEW.md", "evals/judgment-check/PUBLICATION.md"})
broken = []
for name in docs:
    path = ROOT / name
    for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", path.read_text()):
        if "://" in link or link.startswith("#"):
            continue
        target = link.split("#", 1)[0]
        if target and not (path.parent / target).exists():
            broken.append({"file": name, "target": target})
report["broken_relative_file_links"] = broken

# Do not expose matching contents. This is a bounded heuristic, not a secret-free guarantee.
patterns = {"private_key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
            "github_token": re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b"),
            "provider_key": re.compile(rb"\bsk-(?:ant-[A-Za-z0-9_-]{25,}|[A-Za-z0-9_-]{35,})\b"),
            "aws_access_key": re.compile(rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")}
candidate_paths = sorted(set(before["sha256"]) | set(docs))
matches, symlinks, binary_files, large_files = [], [], [], []
for name in candidate_paths:
    path = ROOT / name
    if path.is_symlink():
        symlinks.append(name)
    raw = path.read_bytes()
    if b"\0" in raw:
        binary_files.append(name)
    if len(raw) > 50 * 1024 * 1024:
        large_files.append(name)
    for category, pattern in patterns.items():
        if pattern.search(raw):
            matches.append({"file": name, "category": category})
report["publication_scan"] = {"file_count": len(candidate_paths), "credential_pattern_matches": matches,
                              "symlinks": symlinks, "binary_files": binary_files, "over_50_mib": large_files,
                              "limits": "Pattern scan only; existing public issue bodies and local path provenance remain visible."}
unit = (ROOT / "evals/judgment-check/publication/unit-tests.txt").read_text()
report["saved_full_history_unit_log"] = {"sha256": digest(unit.encode()), "tail": unit.splitlines()[-5:]}
report["ci_dependency_finding"] = {
    "status": "blocker", "test": "tests/test_judgment_experiment.py",
    "source": "evals/judgment-check/experiment.py:33-34",
    "reason": "Tests require git show of baseline 90724fe, unavailable after publication in checks.yml's default single-commit checkout.",
    "validation": "Read the test call sites and unchanged checkout configuration; a full-history local pass cannot resolve this."}
with OUT.open("x") as output:
    json.dump(report, output, indent=2)
    output.write("\n")
print(json.dumps(report, indent=2))
