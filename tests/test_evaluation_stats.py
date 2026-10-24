"""Regression checks for incomplete-evaluation claims, without changing the gold rubric."""
import copy
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "evals/tools"))
import stats


def sample():
    """A complete protocol whose agent beats a deliberately imperfect baseline."""
    cases = {}
    for prefix, size, group in (("e", 25, "curated"), ("a", 5, "adversarial")):
        for number in range(size):
            cases[f"{prefix}{number:02}"] = {
                "set": group, "n": 3, "passes": 3, "any_safety": False,
                "runs": [{"cost": 0} for _ in range(3)],
            }
    score = {"summary": {"real_run_pass_rate": 1.0}, "cases": cases}
    baseline = copy.deepcopy(score)
    for case in baseline["cases"].values():
        case.update(n=1, passes=0, runs=[{"cost": 1}])
    return score, baseline


class EvaluationStatisticsTests(unittest.TestCase):
    def render(self, score, baseline):
        return stats.report(score, baseline, {"e00"}, "test", "baseline")

    def test_complete_protocol_can_meet_thresholds(self):
        text = self.render(*sample())
        self.assertIn("**Protocol complete:** 25/25 real and 5/5 adversarial", text)
        self.assertEqual(text.count("- met:"), 3)

    def test_partial_case_does_not_count_as_three_successes(self):
        score, baseline = sample()
        score["cases"]["e01"].update(n=1, passes=1, runs=[{"cost": 0}])
        text = self.render(score, baseline)
        self.assertIn("**Protocol INCOMPLETE:** 24/25", text)
        self.assertIn("passing every run: 24/24", text)
        self.assertIn("`e01`: 2", text)
        self.assertEqual(text.count("- NOT ASSESSED:"), 3)
        self.assertNotIn("- met:", text)

    def test_missing_adversarial_runs_prevent_acceptance(self):
        score, baseline = sample()
        score["cases"]["a00"].update(n=0, passes=0, runs=[])
        text = self.render(score, baseline)
        self.assertIn("0 real, 3 adversarial", text)
        self.assertNotIn("- met:", text)

    def test_observed_safety_failure_is_not_hidden_by_missing_runs(self):
        score, baseline = sample()
        score["cases"]["a00"].update(n=1, passes=0, any_safety=True, runs=[{"cost": 0}])
        text = self.render(score, baseline)
        self.assertIn("- NOT met: no safety failure", text)
        self.assertNotIn("- met:", text)

    def test_empty_results_report_no_estimate(self):
        score, baseline = sample()
        for case in score["cases"].values():
            case.update(n=0, passes=0, runs=[])
        text = self.render(score, baseline)
        self.assertIn("runs missing: 75 real, 15 adversarial", text)
        self.assertIn("Wilson 95% unavailable", text)
        self.assertIn("Weighted error cost per case: unavailable", text)

    def test_missing_baseline_does_not_validate_cost(self):
        score, baseline = sample()
        del baseline["cases"]["e00"]
        text = self.render(score, baseline)
        self.assertIn("- NOT ASSESSED: mean weighted error cost", text)
        self.assertIn("the same 24 observed cases", text)

    def test_extra_runs_do_not_reduce_missing_count(self):
        score, baseline = sample()
        score["cases"]["e00"].update(n=4, passes=4, runs=[{"cost": 0}] * 4)
        score["cases"]["e01"].update(n=2, passes=2, runs=[{"cost": 0}] * 2)
        text = self.render(score, baseline)
        self.assertIn("runs missing: 1 real", text)
        self.assertNotIn("- met:", text)


if __name__ == "__main__":
    unittest.main()
