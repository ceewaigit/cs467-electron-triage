#!/usr/bin/env python3
"""Read-only verification of two completed attempts; never dispatch or call APIs.

Output creation is exclusive. The optional framework checkout supports a
network-disabled synthetic environment probe, not a provider/header wire test.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--framework-source", type=Path)
args = parser.parse_args()
EVIDENCE = Path(__file__).resolve().parent
REPO = EVIDENCE.parents[2]
SOURCE = "7debabe981d26af3ff36cc4606f45bc6efb1daf3"
checks = []
errors = []
file_hashes = {}


def read(path):
    raw = path.read_bytes()
    name = str(path.relative_to(REPO)) if path.is_relative_to(REPO) else str(path)
    file_hashes[name] = hashlib.sha256(raw).hexdigest()
    return raw


def data(path):
    return json.loads(read(path))


def jsonl(path):
    return [json.loads(line) for line in read(path).splitlines() if line.strip()]


def check(name, actual, expected=True):
    ok = actual == expected
    checks.append({"check": name, "passed": ok})
    if not ok:
        errors.append({"check": name, "actual": actual, "expected": expected})


def committed(name):
    return subprocess.check_output(["git", "show", f"{SOURCE}:{name}"], cwd=REPO)


offline = data(EVIDENCE / "manifest.json")
attempts = {}
for namespace, rid, issue in (("failure-recheck-live", 40066776440, 217),
                              ("failure-recheck-live-2", 40067336688, 218)):
    experiment = REPO / "evals" / namespace
    run = experiment / "runs" / str(rid)
    artifacts = run / "artifacts"
    manifest = data(experiment / "manifest.json")
    seal = data(experiment / "pre-execution-seal.json")
    for name, expected in seal.items():
        check(f"{namespace} pre-execution seal {name}", hashlib.sha256(read(experiment / name)).hexdigest(), expected)
    check(f"{namespace} source", manifest["source_commit"], SOURCE)
    check(f"{namespace} same runtime as offline", manifest["runtime_sha256"], offline["runtime_sha256"])
    for name, expected in manifest["runtime_sha256"].items():
        check(f"{namespace} committed runtime {name}", hashlib.sha256(committed(name)).hexdigest(), expected)
    for field, name in (("scorer_sha256", "evals/tools/score.py"), ("replay_sha256", "evals/tools/replay.py")):
        check(f"{namespace} committed {name}", hashlib.sha256(committed(name)).hexdigest(), manifest[field])
    for cid, names in manifest["case_sha256"].items():
        for name, expected in names.items():
            check(f"{namespace} case {cid}/{name}", hashlib.sha256(read(experiment / "cases" / cid / name)).hexdigest(), expected)
    metadata = data(run / "run-completed.json")
    for key, expected in (("id", rid), ("head_sha", SOURCE), ("event", "workflow_dispatch"),
                          ("status", "completed"), ("conclusion", "failure"), ("run_attempt", 1)):
        check(f"{namespace} run {key}", metadata[key], expected)
    mapping = data(experiment / "replay/runs-failure-recheck-live.json")
    check(f"{namespace} exactly one dispatched case", set(mapping), {str(issue)})
    check(f"{namespace} dispatched case", mapping[str(issue)]["case"], "e52255")
    check(f"{namespace} dispatched run", mapping[str(issue)]["run_id"], rid)
    jobs = {job["name"]: job["conclusion"] for job in data(run / "jobs-completed.json")["jobs"]}
    check(f"{namespace} agent failed", jobs["agent"], "failure")
    check(f"{namespace} triage comment skipped", jobs["triage_comment"], "skipped")
    info = data(artifacts / "info/aw_info.json")
    for key, expected in (("version", "2.1.300"), ("awf_version", "v0.28.70"),
                          ("model", "claude-sonnet-5-5"), ("sha", SOURCE)):
        check(f"{namespace} runtime info {key}", info[key], expected)
    session = jsonl(artifacts / "agent/agent-session.jsonl")
    results = [event for event in session if event.get("type") == "session.result" and "total_cost_usd" in event]
    check(f"{namespace} two agent session results", len(results), 2)
    check(f"{namespace} zero agent recorded cost", [event["total_cost_usd"] for event in results], [0, 0])
    check(f"{namespace} agent results are API errors", all(event.get("is_error") and event.get("terminal_reason") == "api_error" and event.get("api_error_status") == 400 for event in results))
    token_names = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
    check(f"{namespace} zero agent recorded tokens", all(event["usage"].get(key) == 0 for event in results for key in token_names))
    output = data(artifacts / "agent/agent_output.json")
    check(f"{namespace} only framework incomplete signal", [item["type"] for item in output["items"]], ["report_incomplete"])
    check(f"{namespace} no safe output items", read(artifacts / "safe-outputs-items/safe-output-items.jsonl"), b"")
    rpc = jsonl(artifacts / "agent/mcp-logs/rpc-messages.jsonl")
    check(f"{namespace} no safe output MCP calls", sum(event.get("method") == "tools/call" for event in rpc), 0)
    native = data(experiment / "cases/e52255/actual/failure-recheck-live/failures/run-1.json")
    check(f"{namespace} failure excluded from scoring", native["scored"], False)
    check(f"{namespace} collector no triage labels", native["labels_added"], [])
    check(f"{namespace} collector no triage comment", native["comment"], None)
    check(f"{namespace} collector no other writes", native["other_writes"], [])
    check(f"{namespace} no scored result file", not (experiment / "cases/e52255/actual/failure-recheck-live/run-1.json").exists())
    workflow_log = read(run / "workflow.log").decode()
    check(f"{namespace} detector missing verdict reported", "Threat detection produced no security verdict" in workflow_log)
    check(f"{namespace} detector engine error reported", "Error running detection: engine execution failed" in workflow_log)
    check(f"{namespace} historical context prepared", "809 earlier corpus rows retained" in workflow_log)
    roles = {}
    for role, expected_error_count, expected_post_count, cap in (("agent", 6, 4, 100), ("detection", 4, 2, 400)):
        proxy = artifacts / role / "sandbox/firewall/logs/api-proxy-logs"
        upstream = jsonl(proxy / "upstream-errors.jsonl")
        check(f"{namespace}/{role} rejected request count", len(upstream), expected_error_count)
        check(f"{namespace}/{role} rejected POST count", sum(row["method"] == "POST" for row in upstream), expected_post_count)
        check(f"{namespace}/{role} all missing workspace errors", all(row["status"] == 400 and row["error_type"] == "invalid_request_error" and "anthropic-workspace-id" in row["response_body"] for row in upstream))
        check(f"{namespace}/{role} empty usage ledger", read(proxy / "token-usage.jsonl"), b"")
        resolved = data(artifacts / role / "sandbox/firewall/audit/awf-resolved-config.json")
        check(f"{namespace}/{role} proxy enabled", resolved["enableApiProxy"])
        check(f"{namespace}/{role} actual credit cap", resolved["maxAiCredits"], cap)
        check(f"{namespace}/{role} credentials excluded", "ANTHROPIC_API_KEY" in resolved["excludeEnv"])
        images = data(artifacts / role / "sandbox/firewall/audit/image-manifest.json")
        check(f"{namespace}/{role} image tag and digest pinned", all(":0.28.70@sha256:" in entry["image"] for entry in images.values()))
        compose = read(artifacts / role / "sandbox/firewall/audit/docker-compose.redacted.yml").decode()
        check(f"{namespace}/{role} no configured custom workspace header", "ANTHROPIC_CUSTOM_HEADERS" not in compose and "anthropic-workspace-id" not in compose and "ANTHROPIC_WORKSPACE_ID" not in compose)
        roles[role] = {"rejected_requests": len(upstream), "rejected_POST_messages": expected_post_count,
                       "rejected_GET_models": sum(row["method"] == "GET" for row in upstream),
                       "successful_usage_rows": 0, "max_ai_credits": cap,
                       "upstream_request_ids": [row["request_id"] for row in upstream]}
    usage = data(artifacts / "detection/detection_usage.json")
    check(f"{namespace} detector recorded zero tokens and credits", usage, {"input_tokens": 0, "output_tokens": 0, "ai_credits": 0})
    activity = data(artifacts / "usage/activity/summary.json")
    check(f"{namespace} zero activity safe-output items", activity["safe_outputs"]["total_items"], 0)
    # Preserve a digest inventory of all saved completed-run artifacts. These
    # hashes record the reviewed local bytes, not a remote archive signature.
    for path in sorted(run.rglob("*")):
        if path.is_file():
            read(path)
    attempts[namespace] = {"run_id": rid, "issue": issue, "source_commit": metadata["head_sha"],
                           "conclusion": metadata["conclusion"], "job_conclusions": jobs,
                           "valid_triage_decisions": 0, "agent_sessions": len(results),
                           "agent_recorded_cost_usd_each": [event["total_cost_usd"] for event in results],
                           "detection_recorded_usage": usage, "roles": roles,
                           "observed_triage_writes": {key: native[key] for key in ("labels_added", "comment", "other_writes")}}

framework = {"wire_fix_verified": False, "awf_binary_available": shutil.which("awf") is not None,
             "pinned_local_claude_available": (Path.home() / ".local/share/claude/versions/2.1.300").exists()}
if args.framework_source:
    source = args.framework_source.resolve()
    framework["source_path"] = str(source)
    framework["commit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
    framework["tag"] = subprocess.check_output(["git", "describe", "--tags", "--exact-match"], cwd=source, text=True).strip()
    schema = data(source / "pkg/workflow/schemas/awf-config.schema.json")
    framework["anthropic_target_properties"] = sorted(schema["$defs"]["providerTarget"]["properties"])
    framework["anthropic_target_additional_properties"] = schema["$defs"]["providerTarget"]["additionalProperties"]
    framework["workspace_auth_field_description"] = schema["properties"]["apiProxy"]["properties"]["auth"]["properties"]["anthropicWorkspaceId"]["description"]
    for name in ("actions/setup/js/claude_harness.cjs", "actions/setup/js/awf_reflect.cjs", "pkg/workflow/awf_env.go"):
        read(source / name)
    probe = r'''
global.fetch = async () => { throw new Error('Network forbidden in local probe'); };
for (const name of ['node:http','node:https']) {
  const mod = require(name);
  mod.request = mod.get = () => { throw new Error('Network forbidden in local probe'); };
}
const { buildClaudeChildEnv } = require('./actions/setup/js/claude_harness.cjs');
(async () => {
  const env = { ANTHROPIC_CUSTOM_HEADERS: 'anthropic-workspace-id: synthetic-not-a-real-workspace' };
  const child = await buildClaudeChildEnv(null, env, () => {});
  process.stdout.write(JSON.stringify({ synthetic_header_preserved: child.ANTHROPIC_CUSTOM_HEADERS === env.ANTHROPIC_CUSTOM_HEADERS }));
})().catch(error => { process.stderr.write(error.message); process.exitCode = 1; });
'''
    completed = subprocess.run([shutil.which("node"), "-e", probe], cwd=source,
                               env={"PATH": os.defpath, "HOME": str(EVIDENCE)},
                               capture_output=True, text=True, timeout=30)
    framework["harness_probe"] = {"exit_code": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}
    check("local harness synthetic header preservation", completed.returncode == 0 and json.loads(completed.stdout)["synthetic_header_preserved"])
report = {"reviewed_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
          "verification_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          "checks_run": len(checks), "checks_passed": sum(row["passed"] for row in checks),
          "verification_errors": errors, "checks": checks, "attempts": attempts,
          "local_header_assessment": framework, "reviewed_file_sha256": file_hashes,
          "limits": ["No network or provider calls; no dispatch; no credential value accessed.",
                     "Recorded inference usage is zero; provider invoice and Actions infrastructure cost were not inspected.",
                     "No triage writes are supported by collected summaries and runtime artifacts; raw issue timelines were not separately saved for replay.",
                     "Header preservation in a harness environment is not proof of pinned Claude emission, proxy forwarding, model-list request coverage or provider authorization."]}
with (EVIDENCE / "live-review.json").open("x") as stream:
    json.dump(report, stream, indent=2, ensure_ascii=False)
    stream.write("\n")
print(json.dumps({key: report[key] for key in ("checks_run", "checks_passed", "verification_errors", "attempts", "local_header_assessment")}, indent=2, ensure_ascii=False))
