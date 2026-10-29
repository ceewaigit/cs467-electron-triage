"""Checks for the requested-label view used to separate decisions from label delivery."""
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "evals/tools"))
import requested_view


class RequestedViewTests(unittest.TestCase):
    def test_reads_plain_and_rationale_label_forms(self):
        output = {"items": [
            {"type": "triage_comment", "kinds": "similar", "refs": "52098"},
            {"type": "add_labels", "labels": [{"name": "component/gpu", "rationale": "r"}, "blocked/need-repro"]},
        ]}
        self.assertEqual(requested_view.requested_labels(output), ["component/gpu", "blocked/need-repro"])

    def test_copy_replaces_labels_and_keeps_comment(self):
        with tempfile.TemporaryDirectory() as tmp:
            golden = pathlib.Path(tmp)
            run_dir = golden / "cases/e1/actual/final"
            (run_dir / "logs/run-1").mkdir(parents=True)
            (run_dir / "run-1.json").write_text(json.dumps({"labels_added": [], "comment": "text"}))
            (run_dir / "logs/run-1/agent_output.json").write_text(json.dumps(
                {"items": [{"type": "add_labels", "labels": ["component/menu"]}]}))
            with mock.patch.object(requested_view, "GOLDEN", golden), \
                    mock.patch.object(sys, "argv", ["requested_view.py", "--runs", "final"]), \
                    mock.patch("builtins.print"):
                requested_view.main()
            copy = json.loads((golden / "cases/e1/actual/final-requested/run-1.json").read_text())
            self.assertEqual(copy["labels_added"], ["component/menu"])
            self.assertEqual(copy["comment"], "text")
            original = json.loads((run_dir / "run-1.json").read_text())
            self.assertEqual(original["labels_added"], [])


if __name__ == "__main__":
    unittest.main()
