#!/usr/bin/env python3
"""Offline consistency checks for the final documentation review; exclusive output."""
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ATTEMPT = HERE.parent
DOCS = ["README.md", "DESIGN.md", "docs/AUDIT.md", "docs/CODEBASE.md",
        "evals/golden/README.md", "evals/failure-recheck-live-3/README.md"]


def main():
    result = json.loads((ATTEMPT / "result.json").read_text())
    independent = json.loads((HERE / "independent-aggregate-results.json").read_text())
    docs = {name: (ROOT / name).read_text() for name in DOCS}
    checks = {
        "source_matches": result["source_commit"] == independent["source_commit"],
        "five_outputs": result["valid_live_outputs"] == independent["valid_scored_cases"] == 5,
        "three_passes": result["passes"] == independent["passed_cases"] == 3,
        "rubric_cost_four": result["weighted_error_cost_total"] == independent["rubric_error_cost_total"] == 4,
        "zero_scored_safety_failures": result["safety_failures"] == 0 and not independent["safety_failures"],
        "agent_estimate_matches": result["recorded_usd_estimate_by_phase"]["agent"] == independent["agent_estimate_usd"] == "0.7156697",
        "detector_estimate_matches": result["recorded_usd_estimate_by_phase"]["detection"] == independent["detector_estimate_usd"] == "0.5370030",
        "combined_estimate_matches": result["recorded_total_usd_estimate"] == independent["combined_estimate_usd"] == "1.2526727",
        "phase_sum": sum(map(Decimal, result["recorded_usd_estimate_by_phase"].values())) == Decimal("1.2526727"),
        "design_150_lines": len(docs["DESIGN.md"].splitlines()) == 150,
        "fallback_anchor_preserved": '<a id="latest-configuration-coding-assistant-dry-run"></a>' in docs["evals/golden/README.md"],
        "fallback_heading_historical": "## Historical coding-assistant dry run" in docs["evals/golden/README.md"],
        "103_test_log": "Ran 103 tests" in (HERE / "unit-tests.txt").read_text() and "\nOK\n" in (HERE / "unit-tests.txt").read_text(),
        "no_claimed_invoice": independent["invoice_total"] is None,
    }
    for row in independent["cases"]:
        case = row["case"]
        reported = result["cases"][case]
        checks[f"{case}:score_matches"] = reported["score"] == {
            "pass": row["pass"], "fails": row["failure_reasons"],
            "cost": row["rubric_error_cost"], "safety": row["safety_failure"]}
        checks[f"{case}:provenance_matches"] = (reported["run_id"], reported["issue"]) == (row["run_id"], row["issue"])
        checks[f"{case}:cost_matches"] = Decimal(reported["recorded_usd_estimate"]) == Decimal(str(row["combined_estimate_usd"]))
        checks[f"{case}:selected_review_exists"] = (ATTEMPT / reported["independent_review"]).is_file()
    links = []
    for name, text in docs.items():
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
            if re.match(r"[a-z]+://", target):
                continue
            base = unquote(target.split("#", 1)[0])
            if not base:
                continue
            path = (ROOT / name).parent / base
            links.append({"document": name, "target": target, "exists": path.exists()})
    checks["all_local_markdown_link_targets_exist"] = all(link["exists"] for link in links)
    for path, digest in independent["audited_files_sha256"].items():
        checks[f"prior_audit_preserved:{path}"] = hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest
    files = DOCS + [str((ATTEMPT / "result.json").relative_to(ROOT)),
                    str((HERE / "independent-aggregate-results.json").relative_to(ROOT)),
                    str(Path(__file__).resolve().relative_to(ROOT))]
    report = {
        "scope": "Offline numeric/provenance/link consistency and preservation checks accompanying human-readable independent documentation review; no external calls.",
        "checks": checks, "all_checks_passed": all(checks.values()),
        "local_links": links,
        "reviewed_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in files},
        "limits": "Content and readiness judgments are in independent-documentation-review.md. Local link existence does not verify remote URLs or all heading anchors. No runtime or historical evidence is changed by this script."
    }
    with (HERE / "independent-documentation-results.json").open("x") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"checks": len(checks), "passed": sum(checks.values()), "local_links": len(links), "all_checks_passed": report["all_checks_passed"]}))


if __name__ == "__main__":
    main()
