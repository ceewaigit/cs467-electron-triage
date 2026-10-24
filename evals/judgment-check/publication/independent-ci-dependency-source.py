#!/usr/bin/env python3
"""Reproduce the original test's unhandled absent-baseline dependency synthetically."""
import hashlib
import io
import json
import pathlib
import subprocess
import types
import unittest
from unittest import mock

root = pathlib.Path(__file__).resolve().parents[3]
source = root / "evals/judgment-check/evidence/frozen/tests/test_judgment_experiment.py"
module = types.ModuleType("publication_original_test")
# Preserve original test path resolution while traceback lines reference the frozen source.
module.__file__ = str(root / "tests/test_judgment_experiment.py")
exec(compile(source.read_bytes(), str(source), "exec"), module.__dict__)
original = subprocess.check_output
calls = []


def missing_baseline(command, *args, **kwargs):
    if command[:2] == ["git", "show"] and command[2].startswith(module.EXP.BASELINE + ":"):
        calls.append(command)
        raise subprocess.CalledProcessError(128, command, output=b"", stderr=b"fatal: baseline absent")
    return original(command, *args, **kwargs)


stream = io.StringIO()
with mock.patch.object(subprocess, "check_output", side_effect=missing_baseline):
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.TestSuite([
        module.JudgmentGateTests("test_both_arms_missing_required_component_fail_designated_control")]))
report = {"kind": "Synthetic missing-baseline condition, not an actual GitHub Actions run",
          "test_source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
          "test_runs": result.testsRun, "failures": len(result.failures), "errors": len(result.errors),
          "baseline_git_reads": calls, "expected_failure_confirmed": len(result.errors) == 1,
          "output": stream.getvalue(),
          "correction": "v1 compiled frozen bytes under the maintained test filename; concurrent edits affected displayed traceback source. v2 uses the actual frozen source filename."}
with pathlib.Path(__file__).with_name("independent-ci-dependency-reproduction-v2.json").open("x") as output:
    json.dump(report, output, indent=2)
    output.write("\n")
print(json.dumps({key: value for key, value in report.items() if key != "output"}, indent=2))
