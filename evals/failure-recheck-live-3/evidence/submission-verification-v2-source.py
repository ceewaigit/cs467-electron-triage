#!/usr/bin/env python3
"""Verify saved submission evidence offline; never call GitHub or a provider.

Compare earlier tracked content with the evaluated commit, allowing only the five
current documentation updates. Distinguish raw bytes from historical CRLF/LF
normalisation. Preserve two explicitly identified non-runnable auditor drafts.
Check frozen data, runtime hashes, current syntax, links and credential patterns. Write a new report
only; a pattern scan is not a guarantee that every possible secret is absent.
"""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
ATTEMPT = HERE.parent
ROOT = ATTEMPT.parents[1]
DOCS = ["README.md", "DESIGN.md", "docs/AUDIT.md", "docs/CODEBASE.md",
        "evals/golden/README.md"]


def read(path):
    return json.loads(path.read_text())


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_files(commit):
    """Return recorded blob hashes without changing the index or checkout."""
    data = subprocess.check_output(["git", "ls-tree", "-rz", commit], cwd=ROOT)
    files = {}
    for row in data.split(b"\0"):
        if row:
            metadata, name = row.split(b"\t", 1)
            files[name.decode()] = metadata.split()[2].decode()
    return files


def blob_digest(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def git_blob(path):
    return blob_digest(path.read_bytes())


def document_anchors(path):
    """Recognise the simple Markdown headings and explicit IDs used in these guides."""
    text = path.read_text()
    anchors = set(re.findall(r'<a id="([^"]+)"', text))
    for heading in re.findall(r"^#{1,6}\s+(.+)$", text, flags=re.MULTILINE):
        plain = re.sub(r"[^\w\s-]", "", heading.lower())
        anchors.add(plain.replace(" ", "-"))
    return anchors


def main():
    manifest = read(ATTEMPT / "manifest.json")
    checks = {}
    old_files = git_files(manifest["source_commit"])
    historical_crlf = []
    for name, expected in old_files.items():
        if name not in DOCS:
            path = ROOT / name
            exact = path.is_file() and git_blob(path) == expected
            normalized = (not exact and name.endswith("/agent-stdio.log") and path.is_file()
                          and blob_digest(path.read_bytes().replace(b"\r\n", b"\n")) == expected)
            checks[f"preserved:{name}"] = exact or normalized
            if normalized:
                historical_crlf.append({"file": name, "raw_sha256": sha256(path),
                                        "committed_blob": expected, "difference": "CRLF only"})
    frozen = git_files("4baa2cb")
    frozen_names = [name for name in frozen if name in
                    ("evals/golden/RUBRIC.md", "evals/tools/score.py")
                    or re.fullmatch(r"evals/golden/cases/[^/]+/(input|expected)\.json", name)]
    checks["frozen-file-count"] = len(frozen_names) == 62
    for name in frozen_names:
        checks[f"frozen:{name}"] = git_blob(ROOT / name) == frozen[name]
    for name, expected in manifest["runtime_sha256"].items():
        checks[f"runtime:{name}"] = sha256(ROOT / name) == expected
    checks["design-max-150-lines"] = len((ROOT / "DESIGN.md").read_text().splitlines()) <= 150

    files = [p for p in ATTEMPT.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    syntax_counts = {"json": 0, "jsonl": 0, "python": 0}
    archived_drafts = {"independent-aggregate-v2-source.py", "independent-aggregate-v3-source.py"}
    draft_errors = []
    for path in files:
        name = str(path.relative_to(ROOT))
        try:
            if path.suffix == ".json":
                read(path)
                syntax_counts["json"] += 1
            elif path.suffix == ".jsonl":
                for line in path.read_text().splitlines():
                    if line.strip():
                        json.loads(line)
                syntax_counts["jsonl"] += 1
            elif path.suffix == ".py":
                ast.parse(path.read_text())
                syntax_counts["python"] += 1
            else:
                continue
            checks[f"syntax:{name}"] = True
        except (ValueError, SyntaxError, UnicodeError) as error:
            if path.parent == HERE and path.name in archived_drafts and isinstance(error, SyntaxError):
                draft_errors.append({"file": name, "line": error.lineno, "error": error.msg,
                                     "sha256": sha256(path)})
            else:
                checks[f"syntax:{name}"] = False
    checks["two-explicit-archived-draft-errors-recorded"] = len(draft_errors) == 2

    docs = [ROOT / name for name in DOCS] + [ATTEMPT / "README.md"]
    for path in docs:
        for target in re.findall(r"\]\(([^\s)]+)(?:\s+[^)]*)?\)", path.read_text()):
            if re.match(r"[a-z]+://", target):
                continue
            relative, _, anchor = target.partition("#")
            destination = path.parent / relative if relative else path
            valid = destination.exists()
            if valid and anchor:
                valid = destination.is_file() and anchor in document_anchors(destination)
            checks[f"local-link:{path.relative_to(ROOT)}:{target}"] = valid

    patterns = {
        "anthropic-key": rb"sk-ant-[A-Za-z0-9_-]{20,}",
        "github-token": rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})",
        "private-key": rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        "bearer-value": rb"(?i)authorization[\"\s:=]+bearer\s+[A-Za-z0-9_.-]{30,}",
    }
    findings = []
    for path in files:
        for label, pattern in patterns.items():
            if re.search(pattern, path.read_bytes()):
                findings.append({"file": str(path.relative_to(ROOT)), "pattern": label})
    checks["credential-patterns"] = not findings
    summary = read(ATTEMPT / "result.json")
    independent = read(HERE / "independent-aggregate-results.json")
    checks["independent-score-agreement"] = (summary["passes"] == independent["passed_cases"]
        and summary["weighted_error_cost_total"] == independent["rubric_error_cost_total"]
        and summary["recorded_total_usd_estimate"] == independent["combined_estimate_usd"])
    unit_log = (HERE / "unit-tests.txt").read_text()
    checks["saved-103-tests-pass"] = "Ran 103 tests" in unit_log and unit_log.rstrip().endswith("OK")
    report = {"source_commit": manifest["source_commit"], "all_passed": all(checks.values()),
              "check_count": len(checks), "failed_checks": [k for k, v in checks.items() if not v],
              "preserved_tracked_files": len(old_files) - len(DOCS),
              "raw_byte_matches": len(old_files) - len(DOCS) - len(historical_crlf),
              "historical_crlf_only_files": historical_crlf,
              "archived_nonrunnable_drafts": draft_errors,
              "allowed_document_updates": DOCS, "frozen_files": len(frozen_names),
              "runtime_files": len(manifest["runtime_sha256"]), "syntax_counts": syntax_counts,
              "new_files_scanned": len(files), "credential_findings_paths_only": findings,
              "document_sha256": {str(p.relative_to(ROOT)): sha256(p) for p in docs},
              "verifier_sha256": sha256(Path(__file__)), "checks": checks,
              "limits": "Offline saved-evidence verification; no invoice or provider request. "
                        "Credential-pattern scanning is heuristic, not a proof of absence."}
    with (HERE / "submission-verification-results-v2.json").open("x") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(json.dumps({k: v for k, v in report.items() if k not in ("checks", "document_sha256", "historical_crlf_only_files")}, indent=2))
    if not report["all_passed"]:
        raise SystemExit("Review failed checks; preserve this first report.")


if __name__ == "__main__":
    main()
