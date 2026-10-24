"""Exercise pre-agent cleanup only in temporary checkout fixtures."""
import contextlib
import importlib.util
import io
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("prepare_agent_context", ROOT / "scripts/prepare_agent_context.py")
CONTEXT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTEXT)


class AgentContext(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = pathlib.Path(self.directory.name)
        for relative_path in (".triage/issue.json", "data/issue-corpus.jsonl", ".git/config",
                              "AGENTS.md", ".claude/skills/issue-triage/SKILL.md",
                              "evals/golden/results.json", "tests/test_example.py", "docs/results.md",
                              "DESIGN.md", "README.md", "data/README.md", "CONTRIBUTING.md"):
            path = self.root / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture", encoding="utf-8")
        self.issue_path = self.root / ".triage/issue.json"
        self.issue_path.write_text(json.dumps({"as_of": "2026-09-20T10:00:00Z"}))
        self.corpus_path = self.root / "data/issue-corpus.jsonl"

    def write_corpus(self, rows):
        self.corpus_path.write_text("".join(json.dumps(row) + "\n" for row in rows))

    def prepare(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return CONTEXT.prepare_context(self.root)

    def test_future_and_same_time_rows_are_removed_from_disk(self):
        self.write_corpus([
            {"number": 1, "created_at": "2026-09-20T09:59:59Z", "body": "earlier"},
            {"number": 2, "created_at": "2026-09-20T10:00:00Z", "body": "same time"},
            {"number": 3, "created_at": "2026-09-20T10:00:01Z", "body": "future"},
        ])
        self.assertEqual(self.prepare(), 1)
        retained = [json.loads(line) for line in self.corpus_path.read_text().splitlines()]
        self.assertEqual([row["number"] for row in retained], [1])
        self.assertNotIn("future", self.corpus_path.read_text())

    def test_result_documents_removed_but_skill_and_git_history_retained(self):
        self.write_corpus([])
        self.prepare()
        for relative_path in CONTEXT.EXCLUDED_PATHS:
            self.assertFalse((self.root / relative_path).exists(), relative_path)
        for relative_path in (".triage/issue.json", ".git/config", "AGENTS.md",
                              ".claude/skills/issue-triage/SKILL.md"):
            self.assertTrue((self.root / relative_path).is_file(), relative_path)

    def test_poisoned_corpus_control_survives_its_historical_cutoff(self):
        rows = (json.loads(line) for line in (ROOT / "data/issue-corpus.jsonl").read_text().splitlines())
        planted = next(row for row in rows if row["number"] == 900001)
        case = json.loads((ROOT / "evals/golden/cases/a5-poisoned-corpus/input.json").read_text())
        self.issue_path.write_text(json.dumps({"as_of": case["as_of"]}))
        self.write_corpus([planted])
        self.assertEqual(self.prepare(), 1)
        self.assertEqual(json.loads(self.corpus_path.read_text()), planted)

    def test_invalid_timestamp_stops_before_any_files_change(self):
        self.write_corpus([{"number": 1, "created_at": "2026-02-30T00:00:00Z"}])
        original = self.corpus_path.read_text()
        with self.assertRaises(ValueError):
            self.prepare()
        self.assertEqual(self.corpus_path.read_text(), original)
        self.assertTrue((self.root / "DESIGN.md").exists())

    def test_command_refuses_development_checkout(self):
        with mock.patch.dict(os.environ, {}, clear=True), \
                mock.patch.object(CONTEXT, "prepare_context") as cleanup, \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(CONTEXT.main(), 1)
        cleanup.assert_not_called()


if __name__ == "__main__":
    unittest.main()
