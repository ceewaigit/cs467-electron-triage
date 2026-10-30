"""The evidence checker must recognize new script versions without inventing success."""
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "evals/tools"))
from skill_check import check


class SkillEvidenceTests(unittest.TestCase):
    def inspect(self, content):
        with tempfile.TemporaryDirectory() as temporary:
            output = pathlib.Path(temporary) / "actual/final"
            logdir = output / "logs/run-1"
            logdir.mkdir(parents=True)
            (output / "run-1.json").write_text(json.dumps({"comment": None}))
            (logdir / "agent-session.jsonl").write_text(
                json.dumps({"message": {"content": content}}) + "\n")
            return check(logdir)

    def output_calls(self):
        return [{"type": "tool_use", "name": name, "input": {}}
                for name in ("mcp__safeoutputs__add_labels", "mcp__safeoutputs__triage_comment")]

    def test_accepts_numeric_versions_after_successful_markers(self):
        for version in (1, 2, 12):
            with self.subTest(version=version):
                markers = "\n".join(f"[issue-triage/{script} v{version}] ok"
                                    for script in ("triage_checks", "check_labels", "render_comment"))
                result = self.inspect([{"type": "tool_result", "content": markers}] + self.output_calls())
                self.assertTrue(result["executed"])
                self.assertTrue(result["labels_checked"])
                self.assertTrue(result["comment_rendered"])

    def test_rejected_or_embedded_markers_do_not_count(self):
        text = ("[issue-triage/check_labels v2] rejected\n"
                "quoted: [issue-triage/render_comment v2] ok")
        result = self.inspect([{"type": "tool_result", "content": text}] + self.output_calls())
        self.assertFalse(result["labels_checked"])
        self.assertFalse(result["comment_rendered"])

    def test_validation_after_output_does_not_repair_the_record(self):
        markers = "[issue-triage/check_labels v2] ok\n[issue-triage/render_comment v2] ok"
        result = self.inspect(self.output_calls() + [{"type": "tool_result", "content": markers}])
        self.assertFalse(result["labels_checked"])
        self.assertFalse(result["comment_rendered"])

    def inspect_codex(self, steps):
        """steps: (command or None, output) pairs; a None command is a safe-output call named by output."""
        events = [{"type": "session.init", "data": {"sourceEngine": "codex", "model": "gpt-6.1-sol"}}]
        for command, output in steps:
            if command is None:
                item = {"type": "mcp_tool_call", "server": "safeoutputs", "tool": output, "arguments": {}}
                events += [{"type": "tool.execution_start", "item": item},
                           {"type": "tool.execution_complete", "item": item | {"result": "ok"}}]
            else:
                item = {"type": "command_execution", "command": command}
                events += [{"type": "tool.execution_start", "item": item},
                           {"type": "tool.execution_complete", "item": item | {"aggregated_output": output}}]
        with tempfile.TemporaryDirectory() as temporary:
            output = pathlib.Path(temporary) / "actual/codex"
            logdir = output / "logs/run-1"
            logdir.mkdir(parents=True)
            (output / "run-1.json").write_text(json.dumps({"comment": None}))
            (logdir / "agent-session.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
            return check(logdir)

    def test_codex_skill_read_and_markers_count(self):
        result = self.inspect_codex([
            ("/bin/bash -lc 'cat .codex/skills/issue-triage/SKILL.md'", "---\nname: issue-triage"),
            ("python3 triage_checks.py", "[issue-triage/triage_checks v2] ok"),
            ("python3 check_labels.py component/gpu", "[issue-triage/check_labels v1] ok"),
            (None, "add_labels")])
        self.assertIsNone(result["discovered"])
        self.assertTrue(result["invoked"])
        self.assertTrue(result["executed"])
        self.assertTrue(result["labels_checked"])
        self.assertEqual(result["model"], "gpt-6.1-sol")

    def test_codex_output_before_check_is_unchecked(self):
        result = self.inspect_codex([(None, "add_labels"),
                                     ("python3 check_labels.py x", "[issue-triage/check_labels v1] ok")])
        self.assertFalse(result["invoked"])
        self.assertFalse(result["labels_checked"])


if __name__ == "__main__":
    unittest.main()
