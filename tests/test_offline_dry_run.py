"""The dry-run recorder must preserve evidence and avoid credential inheritance."""
import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import pathlib
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("recorder", ROOT / "evals/tools/offline_dry_run.py")
RECORDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RECORDER)


class DryRunEvidence(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = pathlib.Path(self.temporary.name)
        self.checkout = self.directory / "checkout"
        self.checkout.mkdir()

    def test_changed_input_is_rejected_before_execution(self):
        issue = self.checkout / "issue.json"
        issue.write_text('{"body":"original"}')
        hashes = {"issue.json": hashlib.sha256(issue.read_bytes()).hexdigest()}
        (self.directory / "context.json").write_text(json.dumps({"file_sha256": hashes}))
        self.assertEqual(RECORDER.verify_snapshot(self.directory), self.checkout)
        issue.write_text('{"body":"changed"}')
        with self.assertRaisesRegex(ValueError, "prepared file changed"):
            RECORDER.verify_snapshot(self.directory)

    def test_first_decision_and_transcript_cannot_be_replaced(self):
        args = argparse.Namespace(labels=[], kinds="", refs="", reason="No action is needed.")
        with contextlib.redirect_stdout(io.StringIO()):
            RECORDER.finish(self.directory, args)
        original = {p.name: p.read_bytes() for p in self.directory.iterdir() if p.is_file()}
        args.labels = ["component/tray"]
        with self.assertRaises(FileExistsError):
            RECORDER.finish(self.directory, args)
        self.assertEqual(original, {p.name: p.read_bytes() for p in self.directory.iterdir() if p.is_file()})

    def test_tool_results_and_failures_are_saved_without_api_credentials(self):
        result = subprocess.CompletedProcess([], 1, "rejected label\n", "diagnostic\n")
        with mock.patch.object(RECORDER.subprocess, "run", return_value=result) as command, \
                mock.patch.dict(RECORDER.os.environ, {"ANTHROPIC_API_KEY": "test-only", "GH_TOKEN": "test-only"}), \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            status = RECORDER.run_script(self.directory, self.checkout, "check_labels", ["priority/high"])
        self.assertEqual(status, 1)
        environment = command.call_args.kwargs["env"]
        self.assertNotIn("ANTHROPIC_API_KEY", environment)
        self.assertNotIn("GH_TOKEN", environment)
        event = json.loads((self.directory / "transcript.jsonl").read_text())
        self.assertEqual((event["exit_code"], event["stdout"], event["stderr"]),
                         (1, "rejected label\n", "diagnostic\n"))

    def test_checks_cannot_substitute_another_input(self):
        with mock.patch.object(RECORDER.subprocess, "run") as command:
            with self.assertRaisesRegex(ValueError, "no alternate input"):
                RECORDER.run_script(self.directory, self.checkout, "triage_checks", ["elsewhere.json"])
        command.assert_not_called()


if __name__ == "__main__":
    unittest.main()
