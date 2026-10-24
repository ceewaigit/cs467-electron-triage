"""Offline harness lifecycle and rejection gates using synthetic decisions only."""
import argparse
import contextlib
import copy
import importlib.util
import io
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


EXP = module("judgment_experiment", ROOT / "evals/judgment-check/experiment.py")
RECORDER = module("judgment_recorder", ROOT / "evals/tools/offline_dry_run.py")
with mock.patch.dict(sys.modules, {"experiment": EXP}):
    KNOWN = module("judgment_known", ROOT / "evals/judgment-check/known_cases.py")


def rows(namespace="fresh", improve=True):
    ids = [f"fixture-{index:02}" for index in range(24)] if namespace == "fresh" else ["e52255", "e53734"]
    result = []
    for repetition in EXP.REPETITIONS:
        for arm in EXP.ARMS:
            for index, case_id in enumerate(ids):
                failed = improve and arm == "original" and index == 0
                result.append({"case_id": case_id, "arm": arm, "repetition": repetition,
                    "group": ("historical" if index < 12 else "constructed") if namespace == "fresh" else "known",
                    "scored": True, "pass": not failed, "cost": int(failed), "fails": ["wrong label component/tray"] if failed else [],
                    "safety": False, "missed_required_actions": 0, "unsupported_refs": [],
                    "positive_control_coverage": {"component": True} if index == 1 else {},
                    "action_constraints": {"label_limits_observed": True},
                    "procedure": dict.fromkeys(("checks_executed", "labels_validated_before_decision", "comment_rendered_before_decision"), True)})
    return result


class JudgmentGateTests(unittest.TestCase):
    protocol = {"decision_rule": ["Test rule."]}

    def decision(self, data, namespace="fresh"):
        return EXP.primary_decision(data, self.protocol, namespace)

    def test_full_paired_coverage_and_anonymous_same_order(self):
        data = [{"id": f"fixture-{index:02}"} for index in range(24)]
        batches = EXP.plan_batches(data)
        self.assertEqual(len(batches), 16)
        self.assertTrue(all(len(batch["cases"]) == 6 for batch in batches))
        for repetition in (1, 2):
            orders = [[case for batch in batches if batch["arm"] == arm and batch["repetition"] == repetition
                       for case in batch["cases"]] for arm in EXP.ARMS]
            self.assertEqual(*orders)
        self.assertEqual(len({batch["opaque_arm"] for batch in batches}), 2)

    def test_tie_is_non_regressing_but_does_not_claim_improvement(self):
        report = self.decision(rows(improve=False))
        self.assertTrue(report["non_regression_passed"])
        self.assertFalse(report["strict_cost_improvement"])
        self.assertTrue(self.decision(rows())["strict_cost_improvement"])

    def test_pooled_gain_cannot_hide_single_pair_regression(self):
        data = rows()
        candidate = next(row for row in data if row["arm"] == "candidate" and row["case_id"] == "fixture-03")
        candidate.update(cost=1, fails=["wrong label component/gpu"])
        candidate["pass"] = False
        report = self.decision(data)
        self.assertFalse(report["non_regression_passed"])
        self.assertFalse(report["gates"]["every_pair_non_regressing"])

    def test_equal_cost_failure_swap_and_required_omission_each_fail(self):
        original = rows()[0]
        candidate = copy.deepcopy(original)
        candidate["fails"] = ["missing label blocked/need-repro"]
        self.assertFalse(EXP.paired_checks(original, candidate)["no_new_scorer_failure"])
        candidate = copy.deepcopy(original)
        candidate["missed_required_actions"] = 1
        self.assertFalse(EXP.paired_checks(original, candidate)["required_omissions_not_higher"])

    def test_extra_unsupported_link_cannot_hide_behind_a_supported_link(self):
        original = rows(improve=False)[0]
        candidate = copy.deepcopy(original)
        candidate["unsupported_refs"] = [900001]
        self.assertTrue(candidate["pass"])
        self.assertFalse(EXP.paired_checks(original, candidate)["unsupported_references_not_increased"])
        original["unsupported_refs"] = [900002]
        self.assertFalse(EXP.paired_checks(original, candidate)["unsupported_references_not_increased"])

    def test_both_arms_missing_required_component_fail_designated_control(self):
        h = EXP.helpers(ROOT)
        expected = {"labels": {"required": ["component/webRequest"], "acceptable": ["component/net"], "one_of": []}}
        metadata = {"positive_controls": ["component"], "coverage_supported_refs": []}
        coverage = EXP.positive_coverage(expected, metadata, {"component/net"}, set(), set(), h)
        self.assertFalse(coverage["component"])
        data = rows()
        for row in data:
            if row["case_id"] == "fixture-01":
                row["positive_control_coverage"] = coverage.copy()
                row["fails"] = ["missing label component/webRequest"]
                row.update(cost=1, missed_required_actions=1)
                row["pass"] = False
        report = self.decision(data)
        self.assertTrue(report["gates"]["every_pair_non_regressing"])
        self.assertFalse(report["gates"]["all_designated_positive_controls_covered"])
        self.assertFalse(report["non_regression_passed"])
        self.assertTrue(EXP.positive_coverage(expected, metadata, {"component/webRequest"}, set(), set(), h)["component"])

    def test_component_coverage_requires_each_component_one_of_group(self):
        h = EXP.helpers(ROOT)
        expected = {"labels": {"required": ["component/webRequest"], "acceptable": ["component/net"],
                                "one_of": [["component/session", "component/cookies"], ["blocked/need-repro"]]}}
        metadata = {"positive_controls": ["component"], "coverage_supported_refs": []}
        self.assertFalse(EXP.positive_coverage(expected, metadata, {"component/webRequest", "component/net"}, set(), set(), h)["component"])
        self.assertTrue(EXP.positive_coverage(expected, metadata, {"component/webRequest", "component/session"}, set(), set(), h)["component"])

    def test_title_only_reporter_reference_is_a_repeated_link(self):
        h = EXP.helpers(ROOT)
        opening = {"title": "Regression related to #51237", "body": "The body has no issue reference."}
        actual = {"labels_added": [], "comment_request": {"kinds": "similar", "refs": "51237"}}
        checks = EXP.action_constraints(opening, actual, set(), {"similar"}, {51237}, h)
        self.assertFalse(checks["no_reporter_references"])
        self.assertTrue(EXP.action_constraints({**opening, "title": "Regression"}, actual, set(), {"similar"}, {51237}, h)["no_reporter_references"])

    def test_candidate_safety_procedure_positive_and_structural_failures_block(self):
        mutations = [lambda row: row.update(safety=True),
                     lambda row: row["procedure"].update(checks_executed=False),
                     lambda row: row["positive_control_coverage"].update(component=False),
                     lambda row: row["action_constraints"].update(label_limits_observed=False),
                     lambda row: row.update(scored=False, cost=None)]
        for mutate in mutations:
            data = rows()
            candidate = next(row for row in data if row["arm"] == "candidate" and row["case_id"] == "fixture-01")
            mutate(candidate)
            self.assertFalse(self.decision(data)["non_regression_passed"])

    def test_duplicates_or_missing_rows_cannot_pass_coverage(self):
        data = rows()
        data[-1] = copy.deepcopy(data[-2])
        self.assertFalse(self.decision(data)["gates"]["complete_coverage"])
        self.assertFalse(self.decision(rows()[:-1])["gates"]["complete_coverage"])

    def test_every_known_candidate_repeat_must_pass(self):
        data = rows("known")
        self.assertTrue(self.decision(data, "known")["non_regression_passed"])
        candidate = next(row for row in data if row["arm"] == "candidate")
        candidate["pass"] = False
        self.assertFalse(self.decision(data, "known")["gates"]["candidate_every_known_trial_passes"])

    def test_blind_review_maps_only_candidate_direction_and_requires_both(self):
        packet = {"changes": [{"change_id": "fresh/fixture-01/1"}]}
        blind = {"completed": True, "reviewer": "Independent fixture reviewer", "source_sha256": "packet-hash",
                 "judgments": [
                     {"change_id": "fresh/fixture-01/1", "from": "v01", "to": "v02", "harmful": False, "rationale": "Improvement."},
                     {"change_id": "fresh/fixture-01/1", "from": "v02", "to": "v01", "harmful": True, "rationale": "Loses a correct action."}]}
        h = EXP.helpers(ROOT)
        result = EXP.mapped_semantic_review(blind, packet, {"fresh": ("v01", "v02")}, "packet-hash", h)
        self.assertEqual(result["harmful_regressions"], [])
        result = EXP.mapped_semantic_review(blind, packet, {"fresh": ("v02", "v01")}, "packet-hash", h)
        self.assertEqual(len(result["harmful_regressions"]), 1)
        blind["judgments"].pop()
        with self.assertRaises(ValueError):
            EXP.mapped_semantic_review(blind, packet, {"fresh": ("v01", "v02")}, "packet-hash", h)


class JudgmentLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name)
        self.experiment = self.root / "experiment"
        self.workspace = self.root / "runner"
        self.h = EXP.helpers(ROOT)
        self.policy = EXP.source(ROOT, self.h.SKILL)
        protocol = {"baseline_commit": EXP.BASELINE, "repetitions_per_arm_per_case": 2,
                    "policy_sha256": dict.fromkeys(EXP.ARMS, self.h.sha256(self.policy)), "decision_rule": ["Test only."]}
        self.h.write_json(self.experiment / "protocol.json", protocol)
        self.h.write_json(self.experiment / "evidence/preflight.json", {"preserve": True})
        for arm in EXP.ARMS:
            self.h.write_new(self.experiment / "policies" / f"{arm}-SKILL.md", self.policy)
        cases = []
        for index in range(24):
            case_id = f"fixture-{index:02}"
            metadata = {"id": case_id, "group": "historical" if index < 12 else "constructed",
                        "positive_controls": [], "coverage_supported_refs": [], "acceptable_optional_refs": [],
                        "repro_expectation": "forbidden"}
            cases.append(metadata)
            opening = {"title": "Harness-only sample", "body": "Synthetic lifecycle test.", "labels_at_open": [],
                       "author_association": "MEMBER", "as_of": "2026-04-01T00:00:00Z"}
            expected = {"decision": "skip", "labels": {"required": [], "acceptable": [], "one_of": [], "forbidden": []},
                        "comment": {"required_kinds": [], "acceptable_kinds": [], "refs_any": [], "must_not_match": []}}
            self.h.write_json(self.experiment / "cases" / case_id / "input.json", opening)
            self.h.write_json(self.experiment / "cases" / case_id / "expected.json", expected)
        self.h.write_json(self.experiment / "dataset.json", {"cases": cases})

    def tearDown(self):
        self.temp.cleanup()

    def prepare(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return EXP.prepare(self.experiment, ROOT, self.workspace)

    def record(self, manifest, workspace=None):
        workspace = workspace or self.workspace
        with contextlib.redirect_stdout(io.StringIO()):
            for batch in manifest["batches"]:
                for case in batch["cases"]:
                    directory = workspace / batch["id"] / "cases" / case["token"]
                    checkout = RECORDER.verify_snapshot(directory)
                    RECORDER.start(directory, checkout)
                    self.assertEqual(RECORDER.run_script(directory, checkout, "triage_checks", []), 0)
                    RECORDER.finish(directory, argparse.Namespace(labels=[], kinds="", refs="", reason="Synthetic harness fixture."))

    def test_freeze_reproduce_seal_score_and_preserve_first_outputs(self):
        manifest = self.prepare()
        evidence = self.experiment / "evidence"
        self.assertEqual(manifest["planned_first_decisions"], 96)
        self.assertEqual(self.h.read_json(evidence / "preflight.json"), {"preserve": True})
        self.assertEqual(self.h.digest(evidence / "frozen/helper.py"), EXP.HELPER_SHA256)
        self.assertFalse(any(self.workspace.rglob("expected.json")))
        self.assertFalse(any(self.workspace.rglob("dataset.json")))
        reconstructed = self.root / "reconstructed"
        EXP.reproduce(self.experiment, reconstructed)
        for batch in manifest["batches"]:
            for case in batch["cases"]:
                relative = pathlib.Path(batch["id"]) / "cases" / case["token"] / "context.json"
                self.assertEqual((self.workspace / relative).read_bytes(), (reconstructed / relative).read_bytes())
        with self.assertRaises((ValueError, FileExistsError)):
            self.prepare()
        self.record(manifest)
        # Collector must never inspect expected outcomes or annotated dataset.
        original_read = pathlib.Path.read_bytes
        def no_gold(path):
            if path.name in {"expected.json", "dataset.json"}:
                raise AssertionError("collector read grading material")
            return original_read(path)
        with contextlib.redirect_stdout(io.StringIO()), mock.patch.object(pathlib.Path, "read_bytes", no_gold):
            self.assertTrue(EXP.collect(self.experiment, self.workspace))
        with self.assertRaises(FileNotFoundError):
            EXP.score(self.experiment)
        known_workspace = self.root / "known-runner"
        with contextlib.redirect_stdout(io.StringIO()):
            known_manifest = KNOWN.prepare(self.experiment, ROOT, known_workspace)
        self.record(known_manifest, known_workspace)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(EXP.collect(self.experiment / "known-cases", known_workspace))
        with contextlib.redirect_stdout(io.StringIO()):
            result = EXP.score(self.experiment)
        self.assertTrue(result["primary_decision"]["non_regression_passed"])
        self.assertFalse(result["primary_decision"]["strict_cost_improvement"])
        self.assertEqual(len(result["case_runs"]), 96)
        with contextlib.redirect_stdout(io.StringIO()):
            EXP.score(self.experiment / "known-cases")
            packet = EXP.review_packet(self.experiment)
        self.assertEqual(packet["changes"], [])
        self.h.write_json(evidence / "semantic-review-blind.json", {
            "completed": True, "reviewer": "Synthetic lifecycle fixture only",
            "source_sha256": self.h.digest(evidence / "blind-review.json"), "judgments": []})
        EXP.semantic_review(self.experiment)
        with contextlib.redirect_stdout(io.StringIO()):
            final = EXP.decision(self.experiment)
        self.assertFalse(final["accepted"])
        self.assertFalse(final["gates"]["strict_cost_improvement_somewhere"])
        self.assertFalse(final["gates"]["known_non_regression"])
        self.assertTrue(final["gates"]["independent_semantic_review_complete"])
        with self.assertRaises(ValueError):
            EXP.collect(self.experiment, self.workspace)
        with self.assertRaises(ValueError):
            EXP.score(self.experiment)

    def test_tampered_context_stops_collection_before_seal(self):
        manifest = self.prepare()
        case = manifest["batches"][0]["cases"][0]
        path = self.workspace / "s001/cases" / case["token"] / "checkout/.triage/issue.json"
        path.write_text("{}")
        with self.assertRaises(ValueError):
            EXP.collect(self.experiment, self.workspace)
        self.assertFalse((self.experiment / "evidence/sealed-proposals.json").exists())

    def test_known_namespace_preserves_original_targets_and_pairing(self):
        self.prepare()
        with contextlib.redirect_stdout(io.StringIO()):
            manifest = KNOWN.prepare(self.experiment, ROOT, self.root / "known-runner")
        self.assertEqual(manifest["planned_first_decisions"], 8)
        self.assertEqual(len(manifest["batches"]), 4)
        for case_id in KNOWN.KNOWN_IDS:
            for name in ("input.json", "expected.json"):
                frozen = self.experiment / "known-cases/evidence/frozen/cases" / case_id / name
                self.assertEqual(frozen.read_bytes(), EXP.source(ROOT, f"evals/golden/cases/{case_id}/{name}"))
        self.assertEqual({batch["arm"] for batch in manifest["batches"]}, set(EXP.ARMS))

    def test_fixture_additions_are_local_earlier_and_disjoint(self):
        opening = {"as_of": "2026-04-01T00:00:00Z"}
        base = b'{"number":1,"created_at":"2026-01-01T00:00:00Z"}\n'
        fixture = {"number": 900001, "created_at": "2026-03-01T00:00:00Z", "fixture_provenance": "test"}
        additions = (json.dumps(fixture) + "\n").encode()
        self.assertEqual(EXP.case_corpus(base, opening, additions, self.h), base + additions)
        for key, value in (("number", 1), ("created_at", opening["as_of"]), ("fixture_provenance", "")):
            changed = {**fixture, key: value}
            with self.assertRaises(ValueError):
                EXP.case_corpus(base, opening, (json.dumps(changed) + "\n").encode(), self.h)


if __name__ == "__main__":
    unittest.main()
