"""Opening-state workload metrics must not depend on later edits or bot labels."""
import contextlib
import csv
import importlib.util
import io
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("need_analysis", ROOT / "evals/need/analyze_issues.py")
analysis = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(analysis)

BUG_WITHOUT_GIST = "### Electron Version\n42.0.0\n### Testcase Gist URL\n_No response_\n"
BUG_WITH_GIST = BUG_WITHOUT_GIST.replace("_No response_", "https://gist.github.com/reporter/example")


class OpeningStateMetrics(unittest.TestCase):
    def analyze(self, opening_body, snapshot_body, events=()):
        """Run the real aggregation against one synthetic issue and read its output row."""
        issue = {
            "number": 17, "url": "https://example.invalid/issues/17", "title": "Example bug",
            "author": {"login": "reporter", "__typename": "User"}, "authorAssociation": "NONE",
            "createdAt": "2026-07-01T00:00:00Z", "state": "OPEN", "stateReason": None,
            "closedAt": None, "issueType": None, "body": snapshot_body,
            "labels": {"nodes": []}, "comments": {"nodes": [], "totalCount": 0},
            "timelineItems": {"nodes": list(events)},
        }
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            need = root / "need"
            (need / "raw/issues").mkdir(parents=True)
            (root / "data").mkdir()
            (need / "raw/issues/example.json").write_text(json.dumps({"data": {"search": {"nodes": [issue]}}}))
            (need / "raw/issues_manifest.json").write_text(json.dumps({
                "window": ["2026-07-01", "2026-09-30"], "retrieved_at": "2026-10-23T00:00:00Z",
            }))
            (root / "data/electron_issues.jsonl").write_text(json.dumps({"number": 17, "body": opening_body}) + "\n")
            with patch.object(analysis, "HERE", need), contextlib.redirect_stdout(io.StringIO()):
                analysis.main()
            with (need / "issues_table.csv").open() as table:
                return next(csv.DictReader(table))

    def test_opening_gist_counts_without_a_bot_label(self):
        row = self.analyze(BUG_WITH_GIST, BUG_WITH_GIST)
        self.assertEqual(row["gist_at_open"], "True")

    def test_later_gist_and_label_do_not_rewrite_opening_state(self):
        event = {
            "__typename": "LabeledEvent", "createdAt": "2026-07-02T00:00:00Z",
            "actor": {"login": "github-actions", "__typename": "Bot"},
            "label": {"name": "has-repro-gist"},
        }
        row = self.analyze(BUG_WITHOUT_GIST, BUG_WITH_GIST, [event])
        self.assertEqual(row["gist_at_open"], "False")

    def test_opening_form_survives_later_rewrite(self):
        row = self.analyze(BUG_WITHOUT_GIST, "Rewritten without form headings.")
        self.assertEqual(row["bug_form"], "True")

    def test_later_form_does_not_rewrite_opening_state(self):
        row = self.analyze("Initial free-text issue.", BUG_WITH_GIST)
        self.assertEqual(row["bug_form"], "False")
        self.assertEqual(row["gist_at_open"], "False")

    def test_gist_must_be_in_the_gist_field(self):
        body = BUG_WITHOUT_GIST + "\n### Additional Information\nhttps://gist.github.com/someone/example"
        self.assertFalse(analysis.opening_form_fields(body)["gist_at_open"])
        self.assertTrue(analysis.opening_form_fields(BUG_WITH_GIST + "\nExtra explanation.")["gist_at_open"])


if __name__ == "__main__":
    unittest.main()
