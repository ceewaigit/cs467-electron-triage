"""Regression checks for the custom comment job's threat-detection boundary.

These tests never contact GitHub. A rejected verdict must stop before rendering
or running the GitHub CLI, even when a valid comment request is waiting.
"""
import contextlib
import importlib.util
import io
import json
import os
import pathlib
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("post_triage_comment", ROOT / "scripts/post_triage_comment.py")
POSTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(POSTER)


class ThreatDetectionGate(unittest.TestCase):
    def assert_blocked(self, verdict):
        with tempfile.TemporaryDirectory() as directory:
            output_path = pathlib.Path(directory) / "agent_output.json"
            output_path.write_text(json.dumps({"items": [
                {"type": "triage_comment", "kinds": "support", "refs": ""}
            ]}))
            environment = {
                "REPO": "sandbox/repo", "ISSUE": "7",
                "GH_AW_AGENT_OUTPUT": str(output_path),
            }
            if verdict is not None:
                environment["GH_AW_DETECTION_CONCLUSION"] = verdict
            log = io.StringIO()
            with mock.patch.dict(os.environ, environment, clear=True), \
                    mock.patch.object(POSTER.subprocess, "run") as command, \
                    contextlib.redirect_stdout(log):
                self.assertEqual(POSTER.main(), 1)
            command.assert_not_called()
            self.assertIn("nothing posted", log.getvalue())

    def test_threat_verdict_blocks_comment(self):
        self.assert_blocked("failure")

    def test_detector_warning_blocks_comment(self):
        self.assert_blocked("warning")

    def test_missing_or_unrecognised_verdict_blocks_comment(self):
        for verdict in (None, "", "skipped", "unknown", "SUCCESS"):
            with self.subTest(verdict=verdict):
                self.assert_blocked(verdict)


class HistoricalReferences(unittest.TestCase):
    """The posting job must reject future refs even if the model bypasses its renderer."""

    def run_request(self, opened, as_of="2026-09-20T10:00:00Z"):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / "data").mkdir()
            (root / "data/issue-corpus.jsonl").write_text(
                json.dumps({"number": 50000, "created_at": opened}) + "\n")
            output_path = root / "agent_output.json"
            output_path.write_text(json.dumps({"items": [
                {"type": "triage_comment", "kinds": "similar", "refs": "50000"}
            ]}))
            environment = {
                "REPO": "sandbox/repo", "ISSUE": "7", "GH_AW_AGENT_OUTPUT": str(output_path),
                "GH_AW_DETECTION_CONCLUSION": "success",
            }
            if as_of is not None:
                environment["AS_OF"] = as_of
            rendered = "ok\n-----BEGIN COMMENT-----\nFixed template.\n-----END COMMENT-----\n"

            def run_command(args, **kwargs):
                if args[0] == "gh" and "-X" not in args:
                    return subprocess.CompletedProcess(args, 0, '{"created_at":"2026-09-20T10:00:00Z"}')
                return subprocess.CompletedProcess(args, 0, rendered)

            with mock.patch.dict(os.environ, environment, clear=True), \
                    mock.patch.object(POSTER, "ROOT", root), \
                    mock.patch.object(POSTER.subprocess, "run", side_effect=run_command) as command, \
                    contextlib.redirect_stdout(io.StringIO()):
                result = POSTER.main()
            return result, [call.args[0] for call in command.call_args_list]

    def test_equal_and_future_references_never_reach_post(self):
        for opened in ("2026-09-20T10:00:00Z", "2026-09-20T10:00:01Z"):
            with self.subTest(opened=opened):
                result, commands = self.run_request(opened)
                self.assertEqual(result, 0)
                self.assertFalse(any("POST" in command for command in commands))

    def test_earlier_reference_can_be_posted(self):
        result, commands = self.run_request("2026-09-20T09:59:59Z")
        self.assertEqual(result, 0)
        self.assertEqual(sum("POST" in command for command in commands), 1)

    def test_dispatch_without_date_uses_target_issue_opening_time(self):
        result, commands = self.run_request("2026-09-20T10:00:01Z", as_of=None)
        self.assertEqual(result, 0)
        self.assertIn(["gh", "api", "repos/sandbox/repo/issues/7"], commands)
        self.assertFalse(any("POST" in command for command in commands))

    def test_invalid_cutoff_cannot_authorise_reference(self):
        for cutoff in ("not-a-date", "2026-02-30T00:00:00Z"):
            with self.subTest(cutoff=cutoff), \
                    mock.patch.dict(os.environ, {"AS_OF": cutoff}, clear=True), \
                    mock.patch.object(POSTER.subprocess, "run") as command:
                with self.assertRaises(ValueError):
                    POSTER.references_are_earlier("50000", "sandbox/repo", "7")
                command.assert_not_called()


if __name__ == "__main__":
    unittest.main()
