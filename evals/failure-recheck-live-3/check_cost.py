#!/usr/bin/env python3
"""Record a spending checkpoint from completed native evidence; never dispatch.

Inspect both phases, count each request once, and compare native agent USD usage
with proxy accounting. A passing checkpoint permits the next distinct case only.
These between-run thresholds cannot cap an already-running provider request.
"""
import argparse
import datetime as dt
from decimal import Decimal
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
# The CLI serializes binary floating-point sums; allow at most a trillionth of a dollar.
USD_ROUNDING_TOLERANCE = Decimal("1e-12")


def read(path):
    return json.loads(path.read_text(), parse_float=Decimal)


def jsonl(path):
    return [json.loads(line, parse_float=Decimal) for line in path.read_text().splitlines()
            if line.strip()]


def require(condition, reason):
    if not condition:
        raise SystemExit(f"Stop further dispatch: {reason}")


def reconcile_phase(artifacts, phase, rows, model):
    """Reject missing message usage and recompute dollars from saved proxy rates."""
    proxy = artifacts / phase / "sandbox/firewall"
    tracker = jsonl(proxy / "logs/api-proxy-logs/token-tracker-audit.jsonl")
    starts = [row for row in tracker if row["event"] == "TRACK_START"]
    ends = [row for row in tracker if row["event"] == "TRACK_END"]
    start_ids = {row["rid"] for row in starts}
    end_by_id = {row["rid"]: row for row in ends}
    require(len(starts) == len(start_ids) == len(ends) == len(end_by_id)
            and start_ids == set(end_by_id), f"{phase} request tracker is incomplete")
    message_ids = set()
    for start in starts:
        end = end_by_id[start["rid"]]
        require(start["status"] == 200 and start["provider"] == "anthropic",
                f"{phase} tracker has an unsuccessful request")
        path = start["path"].split("?", 1)[0]
        if path == "/v1/messages":
            require(end["result"] == "ok", f"{phase} message has missing usage")
            message_ids.add(start["rid"])
        else:
            require(path == "/v1/models" and end["result"] == "no_usage",
                    f"{phase} has an unaccounted request type")
    require(message_ids == {row["request_id"] for row in rows},
            f"{phase} message requests and usage ledger differ")
    config = read(proxy / "audit/awf-resolved-config.json")
    rates = config["apiProxyProviders"]["anthropic"]["models"][model]["cost"]
    dollars = Decimal(0)
    token_fields = {"input": "input_tokens", "output": "output_tokens",
                    "cache_read": "cache_read_tokens", "cache_write": "cache_write_tokens"}
    for row in rows:
        end = end_by_id[row["request_id"]]
        require(all(end[key] == row[token_fields[key]] for key in
                    ("input", "output", "cache_read")), f"{phase} tracker token totals differ")
        dollars += sum(Decimal(rates[key]) * row[field] for key, field in token_fields.items())
    if phase == "detection":
        summary = read(artifacts / "detection/detection_usage.json")
        require(all(summary[field] == sum(row[field] for row in rows)
                    for field in token_fields.values()), "detector usage summary differs")
        require(summary["ai_credits"] == sum(row["ai_credits_this_response"] for row in rows),
                "detector credit summary differs")
    require(dollars == sum(row["ai_credits_this_response"] for row in rows) / 100,
            f"{phase} resolved rates disagree with recorded credits")
    return dollars


def main():
    manifest = read(HERE / "manifest.json")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True, choices=manifest["cases_in_order"])
    case = parser.parse_args().case
    output = HERE / "evidence" / f"coordinator-cost-{case}.json"
    require(not output.exists(), "preserve the existing spending checkpoint")
    mappings = read(HERE / "replay" / f"runs-{manifest['variant']}.json")
    matched = [row for row in mappings.values() if row["case"] == case]
    require(len(matched) == 1, "expected one dispatch for this case")
    run_id = matched[0]["run_id"]
    directory = HERE / "runs" / str(run_id)
    run = read(directory / "run-completed.json")
    require(run["conclusion"] == "success" and run["run_attempt"] == 1,
            "execution failed or was retried")
    require(run["head_sha"] == manifest["source_commit"], "source commit differs")
    artifacts = directory / "artifacts"
    phases = {}
    for phase in ("agent", "detection"):
        path = artifacts / "usage" / phase / "token_usage.jsonl"
        rows = jsonl(path)
        require(rows and len({row["request_id"] for row in rows}) == len(rows),
                f"{phase} usage is empty or has duplicate request IDs")
        require(all(row["status"] == 200 and row["model"] == manifest["model"] for row in rows),
                f"{phase} has failed requests or another model")
        reconcile_phase(artifacts, phase, rows, manifest["model"])
        credits = sum(row["ai_credits_this_response"] for row in rows)
        require(credits == rows[-1]["ai_credits_total"], f"{phase} credit total differs")
        require(all(not path.read_text().strip()
                    for path in (artifacts / phase).rglob("upstream-errors.jsonl")),
                f"{phase} has upstream errors requiring review")
        phases[phase] = {"unique_successful_requests": len(rows), "ai_credits": str(credits),
                         "recorded_usd_estimate": str(credits / 100),
                         "ledger": str(path.relative_to(HERE))}
    sessions = [row for row in jsonl(artifacts / "agent/agent-session.jsonl")
                if "total_cost_usd" in row]
    require(len(sessions) == 1 and not sessions[0]["is_error"], "agent session missing or failed")
    native_agent_cost = sessions[0]["total_cost_usd"]
    native_difference = abs(native_agent_cost - Decimal(phases["agent"]["recorded_usd_estimate"]))
    require(native_difference <= USD_ROUNDING_TOLERANCE,
            "native agent cost disagrees with proxy accounting")
    verdict = read(artifacts / "detection/detection_result.json")
    require(not any(verdict[key] for key in
                    ("prompt_injection", "secret_leak", "malicious_patch", "reasons", "warnings")),
            "detector flags or warnings need review")
    actual = read(HERE / "cases" / case / "actual" / manifest["variant"] / "run-1.json")
    require(not actual["other_writes"], "unexpected issue writes")
    prior = Decimal(0)
    for previous in manifest["cases_in_order"][:manifest["cases_in_order"].index(case)]:
        checkpoint = read(HERE / "evidence" / f"coordinator-cost-{previous}.json")
        prior += Decimal(checkpoint["recorded_total_usd_estimate"])
    total = sum(Decimal(phase["recorded_usd_estimate"]) for phase in phases.values())
    limits = read(HERE / "budget-stop-rule.json")
    within_budget = (total <= limits["maximum_completed_run_estimate_before_continuing_usd"]
                     and prior + total < limits["cumulative_pause_threshold_usd"])
    if not within_budget:
        decision = "Stop: a spending threshold was reached."
    elif case == manifest["cases_in_order"][-1]:
        decision = "All five planned cases are complete; stop further dispatch."
    else:
        decision = "Within thresholds; next distinct case permitted once."
    report = {"checked_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
              "case": case, "run_id": run_id, "phases": phases,
              "recorded_total_usd_estimate": str(total),
              "cumulative_recorded_usd_estimate": str(prior + total),
              "native_agent_usd": str(native_agent_cost),
              "native_proxy_difference_usd": str(native_difference),
              "native_rounding_tolerance_usd": str(USD_ROUNDING_TOLERANCE),
              "conversion": "100 AI credits per USD; proxy agrees with native agent USD cost. "
                            "Recomputed from each phase's resolved rates and reconciled with "
                            "request trackers and detector summary. Estimate, not provider invoice.",
              "execution": "success", "detection_verdict": "No flags or warnings",
              "unexpected_writes": [], "correctness": "Independently scored separately.",
              "decision": decision}
    with output.open("x") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(f"{case}: ${total} recorded estimate; cumulative ${prior + total}. {report['decision']}")
    require(within_budget, "spending threshold reached")


if __name__ == "__main__":
    main()
