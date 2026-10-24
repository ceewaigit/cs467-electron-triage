#!/usr/bin/env python3
"""Save completed-run artifacts and raw issue evidence without dispatching a run.

The replay helper exports outcomes separately. This reader retains the complete
usage artifacts that helper does not keep. It refuses to overwrite a run bundle.
"""
import argparse
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
MANIFEST = json.loads((HERE / "manifest.json").read_text())
REPO = MANIFEST["repository"]


def github(*arguments):
    """Return GitHub CLI output; none of the callers performs a remote write."""
    return subprocess.check_output(["gh", *map(str, arguments)])


def api(path):
    return json.loads(github("api", f"repos/{REPO}/{path}"))


def save(directory, name, value):
    with (directory / name).open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True, choices=MANIFEST["cases_in_order"])
    args = parser.parse_args()
    state = json.loads((HERE / "replay" / f"runs-{MANIFEST['variant']}.json").read_text())
    matches = [(issue, row) for issue, row in state.items() if row["case"] == args.case]
    if len(matches) != 1:
        raise SystemExit("Expected exactly one dispatched run for the selected case.")
    issue, mapping = matches[0]
    run_id = mapping["run_id"]
    run = api(f"actions/runs/{run_id}")
    if run["status"] != "completed" or run["head_sha"] != MANIFEST["source_commit"]:
        raise SystemExit("Run is unfinished or evaluated the wrong commit.")
    directory = HERE / "runs" / str(run_id)
    directory.mkdir(parents=True, exist_ok=False)
    save(directory, "run-completed.json", run)
    save(directory, "jobs-completed.json", api(f"actions/runs/{run_id}/jobs?per_page=100"))
    artifacts = api(f"actions/runs/{run_id}/artifacts?per_page=100")
    if artifacts["total_count"] != len(artifacts["artifacts"]):
        raise SystemExit("Artifact pagination requires inspection before collection.")
    save(directory, "artifacts-completed.json", artifacts)
    for artifact in artifacts["artifacts"]:
        name = artifact["name"]
        if Path(name).name != name or name in (".", "..") or artifact["expired"]:
            raise SystemExit("Invalid or expired artifact; preserve partial collection.")
        github("run", "download", run_id, "-R", REPO, "-n", name,
               "-D", directory / "artifacts" / name)
    (directory / "workflow.log").write_bytes(github("run", "view", run_id, "-R", REPO, "--log"))
    save(directory, "issue-after-run.json", api(f"issues/{issue}"))
    timeline = json.loads(github("api", f"repos/{REPO}/issues/{issue}/timeline?per_page=100",
                                "--paginate", "--slurp", "-H", "Accept: application/vnd.github+json"))
    save(directory, "issue-timeline-pages.json", timeline)
    print(f"Saved completed {args.case} run {run_id}: {run['conclusion']}; "
          f"{len(artifacts['artifacts'])} complete artifact bundles.")


if __name__ == "__main__":
    main()
