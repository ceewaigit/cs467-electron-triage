"""The drift report must surface every output a human has to look at, and nothing else."""
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "evals" / "tools"))
import drift_report  # noqa: E402


def scored(passes, n, safety=()):
    runs = [{"pass": i < passes, "fails": [] if i < passes else ["wrong label component/app"],
             "safety": list(safety), "cost": 0 if i < passes else 1, "run": f"run-{i + 1}"} for i in range(n)]
    return {"set": "curated", "runs": runs, "passes": passes, "n": n, "any_safety": bool(safety)}


class DriftReport(unittest.TestCase):
    def build(self, root, reference, rerun, outputs):
        (root / "results").mkdir()
        for name, cases in (("ref", reference), ("new", rerun)):
            (root / "results" / f"score-{name}.json").write_text(json.dumps({"summary": {}, "cases": cases}))
        for (case, runs, run), output in outputs.items():
            path = root / "cases" / case / "actual" / runs / f"{run}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(output))

    def test_new_failures_missing_runs_and_changed_outputs_need_review(self):
        same = {"labels_added": ["component/gpu"], "comment": None}
        with tempfile.TemporaryDirectory() as directory, \
                mock.patch.object(drift_report, "ROOT", pathlib.Path(directory)):
            root = pathlib.Path(directory)
            self.build(root,
                       {"steady": scored(3, 3), "broke": scored(3, 3), "fixed": scored(0, 3), "lost": scored(3, 3)},
                       {"steady": scored(1, 1), "broke": scored(0, 1), "fixed": scored(1, 1), "lost": scored(0, 0)},
                       {("steady", "ref", "run-1"): same, ("steady", "new", "run-1"): same,
                        ("broke", "ref", "run-1"): same,
                        ("broke", "new", "run-1"): {"labels_added": ["component/app"], "comment": None}})
            review = drift_report.compare("new", "ref")
        self.assertEqual([item.split(":")[0] for item in review["new failure"]], ["broke"])
        self.assertEqual([item.split(":")[0] for item in review["fixed"]], ["fixed"])
        self.assertEqual([item.split(":")[0] for item in review["missing or failed"]], ["lost"])
        self.assertEqual(len(review["changed output"]), 1)
        self.assertIn("component/app", review["changed output"][0])

    def test_identical_rerun_needs_no_review(self):
        same = {"labels_added": [], "comment": "Thanks.\n\n`triage: kinds=need-repro refs=`"}
        with tempfile.TemporaryDirectory() as directory, \
                mock.patch.object(drift_report, "ROOT", pathlib.Path(directory)):
            self.build(pathlib.Path(directory), {"a": scored(3, 3)}, {"a": scored(1, 1)},
                       {("a", "ref", "run-1"): same, ("a", "new", "run-1"): same})
            review = drift_report.compare("new", "ref")
        self.assertFalse(any(review.values()))


if __name__ == "__main__":
    unittest.main()
