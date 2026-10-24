"""New reproduction gates and evidence lifecycle; all decisions are synthetic fixtures."""
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


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXPERIMENT = load_module("reproduction_experiment", ROOT / "evals/reproduction-check/experiment.py")
RECORDER = load_module("reproduction_recorder", ROOT / "evals/tools/offline_dry_run.py")
with mock.patch.dict(sys.modules, {"experiment": EXPERIMENT}):
    KNOWN = load_module("known_reproduction_regression", ROOT / "evals/reproduction-check/known_regression.py")


def expectation(disposition="forbidden", *, positive=False):
    expected = {"decision": "triage", "labels": {"required": [], "acceptable": [], "one_of": [], "forbidden": []},
                "comment": {"required_kinds": [], "acceptable_kinds": [], "refs_any": [], "must_not_match": []}}
    if disposition != "forbidden":
        field = "required" if disposition == "required" else "acceptable"
        expected["labels"][field].append(EXPERIMENT.REPRO_LABEL)
        expected["comment"][field + "_kinds"].append(EXPERIMENT.REPRO_KIND)
    if positive:
        expected["labels"]["required"].append("component/tray")
        expected["comment"]["required_kinds"].append("similar")
        expected["comment"]["refs_any"].append(50000)
    return expected


def passing_rows():
    """One required constructed request improves twice; all other actions tie."""
    rows = []
    for repetition in EXPERIMENT.REPETITIONS:
        for arm in EXPERIMENT.ARMS:
            for number in range(30):
                required = number == 18
                omitted = required and arm == "original"
                positive = number == 29
                metadata = {"repro_expectation": "required" if required else "forbidden"}
                labels = {EXPERIMENT.REPRO_LABEL} if required and not omitted else set()
                kinds = {EXPERIMENT.REPRO_KIND} if labels else set()
                rows.append({"case_id": f"fixture-{number:03}", "arm": arm, "repetition": repetition,
                             "group": "historical" if number < 18 else "constructed", "scored": True,
                             "pass": not omitted, "cost": 2 if omitted else 0, "fails": [], "safety": False,
                             "missed_required_actions": 2 if omitted else 0, "unsupported_refs": [],
                             "discretionary_labels": [], "discretionary_links": [],
                             "positive_controls": ["link", "component"] if positive else [],
                             "positive_control_coverage": {"link": True, "component": True} if positive else {},
                             "procedure": dict.fromkeys(EXPERIMENT.PROCEDURE_CHECKS, True),
                             "action_constraints": dict.fromkeys(("label_limits_observed", "security_exclusivity_observed",
                                 "references_require_similar", "reference_limit_observed", "no_repeated_references",
                                 "no_reporter_references"), True),
                             **EXPERIMENT.reproduction_actions(expectation(metadata["repro_expectation"]), metadata, labels, kinds)})
    return rows


class ReproductionGateTests(unittest.TestCase):
    protocol = {"decision_rule": ["Synthetic test declaration."]}

    def decision(self, rows):
        return EXPERIMENT.primary_decision(rows, self.protocol)

    def target(self, rows, *, group="constructed", repetition=1, required=True):
        return next(row for row in rows if row["arm"] == "candidate" and row["group"] == group
                    and row["repetition"] == repetition and (not required or row["repro_expectation"] == "required"))

    def test_complete_two_repetition_improvement_passes_with_historical_tie(self):
        result = self.decision(passing_rows())
        self.assertTrue(result["accepted"], result["gates"])

    def test_tie_fails_both_strict_improvement_thresholds(self):
        rows = passing_rows()
        for row in rows:
            if row["arm"] == "original" and row["group"] == "constructed":
                row.update(cost=0, missed_required_repro_actions=0)
        result = self.decision(rows)
        for repetition in EXPERIMENT.REPETITIONS:
            self.assertFalse(result["gates"][f"run_{repetition}_constructed_cost_strictly_lower"])
            self.assertFalse(result["gates"][f"run_{repetition}_constructed_repro_omissions_strictly_lower"])
        self.assertFalse(result["accepted"])

    def test_cost_and_repro_omission_improvement_are_independent(self):
        for field, gate in (("cost", "cost"), ("missed_required_repro_actions", "repro_omissions")):
            with self.subTest(field=field):
                rows = passing_rows()
                self.target(rows)[field] = 2
                result = self.decision(rows)
                self.assertFalse(result["gates"][f"run_1_constructed_{gate}_strictly_lower"])
                self.assertFalse(result["accepted"])

    def test_one_repetition_gain_cannot_pass_pooled(self):
        rows = passing_rows()
        self.target(rows, repetition=2).update(cost=2, missed_required_repro_actions=2)
        result = self.decision(rows)
        self.assertTrue(result["gates"]["run_1_constructed_cost_strictly_lower"])
        self.assertFalse(result["gates"]["run_2_constructed_cost_strictly_lower"])
        self.assertFalse(result["accepted"])

    def test_noop_and_one_sided_request_cannot_count_as_correct(self):
        for labels, kinds, omissions in ((set(), set(), 2), ({EXPERIMENT.REPRO_LABEL}, set(), 1),
                                        (set(), {EXPERIMENT.REPRO_KIND}, 1)):
            with self.subTest(labels=labels, kinds=kinds):
                rows = passing_rows()
                row = self.target(rows)
                row.update(EXPERIMENT.reproduction_actions(expectation("required"),
                           {"repro_expectation": "required"}, labels, kinds))
                self.assertEqual(row["missed_required_repro_actions"], omissions)
                result = self.decision(rows)
                self.assertFalse(result["gates"]["run_1_all_constructed_repro_decisions_correct"])
                self.assertFalse(result["accepted"])

    def test_unwanted_label_and_kind_each_fail_any_cohort(self):
        for group in EXPERIMENT.COHORT_COUNTS:
            for labels, kinds, count in (({EXPERIMENT.REPRO_LABEL}, set(), 1),
                                        (set(), {EXPERIMENT.REPRO_KIND}, 1),
                                        ({EXPERIMENT.REPRO_LABEL}, {EXPERIMENT.REPRO_KIND}, 2)):
                with self.subTest(group=group, labels=labels, kinds=kinds):
                    rows = passing_rows()
                    row = next(row for row in rows if row["arm"] == "candidate" and row["group"] == group
                               and row["repro_expectation"] == "forbidden")
                    row.update(EXPERIMENT.reproduction_actions(expectation(), {"repro_expectation": "forbidden"}, labels, kinds))
                    self.assertEqual(row["unwanted_repro_actions"], count)
                    result = self.decision(rows)
                    self.assertFalse(result["gates"]["no_candidate_unwanted_repro_actions"])
                    self.assertFalse(result["accepted"])

    def test_optional_request_has_no_reproduction_penalty(self):
        for labels, kinds in ((set(), set()), ({EXPERIMENT.REPRO_LABEL}, {EXPERIMENT.REPRO_KIND})):
            result = EXPERIMENT.reproduction_actions(expectation("optional"),
                     {"repro_expectation": "optional"}, labels, kinds)
            self.assertEqual(result["unwanted_repro_actions"], 0)
            self.assertEqual(result["missed_required_repro_actions"], 0)
            self.assertTrue(result["repro_decision_correct"])

    def test_each_historical_regression_blocks_independently(self):
        for field, value, gate in (("cost", 1, "cost_not_higher"), ("pass", False, "passes_not_lower"),
                                   ("missed_required_actions", 1, "omissions_not_higher")):
            with self.subTest(field=field):
                rows = passing_rows()
                self.target(rows, group="historical", required=False)[field] = value
                result = self.decision(rows)
                self.assertFalse(result["gates"][f"run_1_historical_{gate}"])
                self.assertFalse(result["accepted"])

    def test_positive_actions_and_constructed_passes_cannot_be_suppressed(self):
        for control in ("link", "component"):
            with self.subTest(control=control):
                rows = passing_rows()
                positive = next(row for row in rows if row["arm"] == "candidate" and row["positive_controls"])
                positive["positive_control_coverage"][control] = False
                self.assertFalse(self.decision(rows)["gates"]["run_1_all_positive_controls_pass"])
        rows = passing_rows()
        for row in rows:
            if row["arm"] == "candidate" and row["group"] == "constructed" and not row["positive_controls"]:
                row["pass"] = False
        self.assertFalse(self.decision(rows)["gates"]["run_1_constructed_passes_not_lower"])

    def test_missing_duplicate_invalid_and_wrong_cohort_coverage_fail(self):
        for modification in (lambda rows: rows.pop(), lambda rows: rows.__setitem__(0, copy.deepcopy(rows[1])),
                             lambda rows: rows[0].update(scored=False, cost=None),
                             lambda rows: rows[0].update(group="constructed")):
            rows = passing_rows()
            modification(rows)
            self.assertFalse(self.decision(rows)["gates"]["complete_valid_coverage"])

    def test_helper_procedure_required_in_both_arms(self):
        for arm in EXPERIMENT.ARMS:
            for check in EXPERIMENT.PROCEDURE_CHECKS:
                with self.subTest(arm=arm, check=check):
                    rows = passing_rows()
                    next(row for row in rows if row["arm"] == arm)["procedure"][check] = False
                    self.assertFalse(self.decision(rows)["gates"]["all_required_helper_procedures_observed"])

    def test_candidate_safety_constraints_and_unsupported_refs_block(self):
        for field, value, gate in (("safety", True, "no_candidate_safety_or_invalid_final_proposal"),
                                  ("unsupported_refs", [59999], "run_1_unsupported_references_not_higher")):
            rows = passing_rows()
            self.target(rows)[field] = value
            self.assertFalse(self.decision(rows)["gates"][gate])
        rows = passing_rows()
        self.target(rows)["action_constraints"]["no_repeated_references"] = False
        self.assertFalse(self.decision(rows)["gates"]["candidate_action_constraints_observed"])

    def test_structural_checks_keep_raw_duplicate_reporter_and_exclusive_actions(self):
        def constraints(labels=(), kinds=(), raw_refs="", body=""):
            actual = {"labels_added": list(labels), "comment_request": {"refs": raw_refs}}
            return EXPERIMENT.action_constraints({"body": body}, actual, set(labels), set(kinds), set())
        self.assertFalse(constraints(kinds=["similar"], raw_refs="50000,50000")["no_repeated_references"])
        self.assertFalse(constraints(kinds=["similar"], raw_refs="50000", body="Reported in #50000.")["no_reporter_references"])
        self.assertFalse(constraints(raw_refs="50000")["references_require_similar"])
        self.assertFalse(constraints(kinds=["similar"], raw_refs="50000,50001,50002,50003")["reference_limit_observed"])
        self.assertFalse(constraints(labels=["component/a", "component/b", "component/c"])["label_limits_observed"])
        self.assertFalse(constraints(labels=["a", "b", "c", "d"])["label_limits_observed"])
        for labels, kinds, refs in (([EXPERIMENT.REPRO_LABEL], ["security"], ""),
                                   ([], ["security", "similar"], ""), ([], ["security"], "50000")):
            self.assertFalse(constraints(labels, kinds, refs)["security_exclusivity_observed"])
        self.assertTrue(all(constraints(["component/tray"], ["security"]).values()))


class ReproductionEvidenceTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = pathlib.Path(directory.name)
        self.experiment, self.workspace = self.directory / "evaluator", self.directory / "runners"
        self.policies = {"original": b"Original fixture policy.\n", "candidate": b"Candidate fixture policy.\n"}
        paths = [EXPERIMENT.SKILL, EXPERIMENT.CORPUS, "AGENTS.md", "CLAUDE.md", ".github/workflows/issue-triage.md",
                 ".claude/skills/issue-triage/assets/allowed-labels.txt",
                 *[f"{EXPERIMENT.SCRIPT_DIRECTORY}/{name}.py" for name in RECORDER.SCRIPTS],
                 *[f"fixture-runtime-{number}.txt" for number in range(6)]]
        self.source = dict.fromkeys(paths, b"Fixture runtime source.\n")
        self.source[EXPERIMENT.SKILL] = self.policies["original"]
        self.source[EXPERIMENT.CORPUS] = b"".join(EXPERIMENT.json_bytes({"number": 50000 + index,
            "created_at": date, "title": "Fixture tray failure", "body": "Same fixture failure."}).replace(b"\n", b"") + b"\n"
            for index, date in enumerate(("2026-04-01T00:00:00Z", "2026-04-02T00:00:00Z")))
        self.source[".claude/skills/issue-triage/assets/allowed-labels.txt"] = b"component/tray\nblocked/need-repro\n"
        self.source[f"{EXPERIMENT.SCRIPT_DIRECTORY}/triage_checks.py"] = b"print('fixture checks succeeded')\n"
        for name in ("check_labels", "render_comment"):
            self.source[f"{EXPERIMENT.SCRIPT_DIRECTORY}/{name}.py"] = (ROOT / EXPERIMENT.SCRIPT_DIRECTORY / f"{name}.py").read_bytes()
        for name in (EXPERIMENT.RECORDER, EXPERIMENT.SCORER, "evals/tools/replay.py"):
            self.source[name] = (ROOT / name).read_bytes()
        self.source[EXPERIMENT.OLD_MANIFEST] = EXPERIMENT.json_bytes({"runtime_sha256": dict.fromkeys(paths, "fixture")})
        self.dataset = {"cases": []}
        for number in range(30):
            case_id = f"fixture-{number:03}"
            disposition = "required" if number in (1, 18) else "optional" if number == 0 else "forbidden"
            positive = number == 29
            metadata = {"id": case_id, "group": "historical" if number < 18 else "constructed",
                        "repro_expectation": disposition, "positive_controls": ["link", "component"] if positive else [],
                        "coverage_supported_refs": [50000] if positive else []}
            self.dataset["cases"].append(metadata)
            opening = {"id": case_id, "set": "fixture", "source": "Private annotation marker",
                       "title": "Fixture report from @example", "body": "### Testcase Gist URL\n_No response_\n",
                       "as_of": "2026-04-02T00:00:00Z", "labels_at_open": [], "author_association": "NONE"}
            EXPERIMENT.write_json(self.experiment / "cases" / case_id / "input.json", opening)
            EXPERIMENT.write_json(self.experiment / "cases" / case_id / "expected.json", expectation(disposition, positive=positive))
        EXPERIMENT.write_json(self.experiment / "dataset.json", self.dataset)
        EXPERIMENT.write_json(self.experiment / "protocol.json", {"baseline_commit": EXPERIMENT.BASELINE,
            "repetitions_per_arm_per_case": 2, "decision_rule": ["Synthetic fixture rule"],
            "policy_sha256": {arm: EXPERIMENT.sha256(raw) for arm, raw in self.policies.items()}})
        for arm, raw in self.policies.items():
            EXPERIMENT.write_new(self.experiment / "policies" / f"{arm}-SKILL.md", raw)

    def prepare(self):
        with mock.patch.object(EXPERIMENT, "from_commit", side_effect=lambda repo, name: self.source[name]), contextlib.redirect_stdout(io.StringIO()):
            return EXPERIMENT.prepare(self.experiment, ROOT, self.workspace)

    def finish_all(self, manifest, *, malformed_candidate=False):
        """Run local fixture helpers and record first synthetic proposals only."""
        for batch in manifest["batches"]:
            for case in batch["cases"]:
                number = int(case["case_id"].split("-")[-1])
                repro = number == 1 or (number == 18 and batch["arm"] == "candidate")
                positive = number == 29
                labels = [EXPERIMENT.REPRO_LABEL] if repro else ["component/tray"] if positive else []
                kinds, refs = ("need-repro", "") if repro else ("similar", "50000") if positive else ("", "")
                directory = self.workspace / batch["id"] / "cases" / case["token"]
                checkout = directory / "checkout"
                with contextlib.redirect_stdout(io.StringIO()):
                    RECORDER.start(directory, checkout)
                    self.assertEqual(RECORDER.run_script(directory, checkout, "triage_checks", []), 0)
                    if labels:
                        self.assertEqual(RECORDER.run_script(directory, checkout, "check_labels", labels), 0)
                    if kinds:
                        self.assertEqual(RECORDER.run_script(directory, checkout, "render_comment", ["--kinds", kinds, "--refs", refs]), 0)
                    if malformed_candidate and number == 18 and batch["arm"] == "candidate" and batch["repetition"] == 1:
                        # Simulate a malformed first decision, never repair one after sealing.
                        proposal = {"writes_executed": False, "explanation": "Malformed synthetic fixture.",
                                    "items": [{"type": "triage_comment", "kinds": 42, "refs": ""}]}
                        EXPERIMENT.write_json(directory / "proposal.json", proposal)
                        RECORDER.record(directory, {"event": "assistant_decision", "content": proposal})
                    else:
                        RECORDER.finish(directory, argparse.Namespace(labels=labels, kinds=kinds, refs=refs, reason="Synthetic fixture decision."))

    def test_prepare_18_12_pairs_input_privacy_only_skill_diff_and_exact_reproduction(self):
        manifest = self.prepare()
        self.assertEqual(manifest["cohort_counts"], {"historical": 18, "constructed": 12})
        self.assertEqual(manifest["seed"], 4672027)
        self.assertEqual(len(manifest["batches"]), 12)
        self.assertEqual(sum(len(batch["cases"]) for batch in manifest["batches"]), 120)
        self.assertTrue(all(len(batch["cases"]) == 10 for batch in manifest["batches"]))
        for repetition in EXPERIMENT.REPETITIONS:
            arms = {arm: [case for batch in manifest["batches"] if batch["arm"] == arm and batch["repetition"] == repetition
                          for case in batch["cases"]] for arm in EXPERIMENT.ARMS}
            self.assertEqual([case["case_id"] for case in arms["original"]], [case["case_id"] for case in arms["candidate"]])
            for original, candidate in zip(arms["original"], arms["candidate"]):
                self.assertEqual(original["normalized_input_sha256"], candidate["normalized_input_sha256"])
        paired_contexts = {}
        for batch in manifest["batches"]:
            for case in batch["cases"]:
                directory = self.workspace / batch["id"] / "cases" / case["token"]
                context = EXPERIMENT.read_json(directory / "context.json")
                issue = EXPERIMENT.read_json(directory / "checkout/.triage/issue.json")
                self.assertEqual(context["earlier_corpus_rows"], 1)
                self.assertFalse({"source", "id", "set", "repro_expectation"} & issue.keys())
                self.assertIn("@\u200bexample", issue["title"])
                hashes = dict(context["file_sha256"])
                hashes.pop(EXPERIMENT.SKILL)
                key = (case["case_id"], batch["repetition"])
                self.assertEqual(hashes, paired_contexts.setdefault(key, hashes))
        self.assertFalse(any(path.name in {"expected.json", "dataset.json", "protocol.json", ".git"}
                             for path in self.workspace.rglob("*")))
        reconstructed = self.directory / "reconstructed"
        with contextlib.redirect_stdout(io.StringIO()):
            EXPERIMENT.reproduce(self.experiment, reconstructed)
        hashes = lambda root: {str(path.relative_to(root)): EXPERIMENT.digest(path) for path in root.rglob("*") if path.is_file()}
        self.assertEqual(hashes(self.workspace), hashes(reconstructed))
        self.assertEqual((self.experiment / "evidence/frozen/score.py").read_bytes(), self.source[EXPERIMENT.SCORER])
        with self.assertRaisesRegex(ValueError, "preserve existing evidence"):
            self.prepare()
        with self.assertRaises(FileExistsError):
            EXPERIMENT.reproduce(self.experiment, reconstructed)

    def test_prepare_rejects_old_cohort_or_inconsistent_repro_metadata_before_evidence(self):
        wrong = copy.deepcopy(self.dataset)
        wrong["cases"][18]["group"] = "historical"
        with self.assertRaisesRegex(ValueError, "18 historical"):
            EXPERIMENT.validate_dataset(wrong)
        metadata = self.dataset["cases"][18]
        path = self.experiment / "cases" / metadata["id"] / "expected.json"
        path.write_bytes(EXPERIMENT.json_bytes(expectation()))
        with self.assertRaisesRegex(ValueError, "repro_expectation disagrees"):
            self.prepare()
        self.assertFalse((self.experiment / "evidence").exists())
        self.assertFalse(self.workspace.exists())

    def test_complete_fixture_collection_scoring_and_immutability(self):
        manifest = self.prepare()
        self.finish_all(manifest)
        read_bytes, read_text = pathlib.Path.read_bytes, pathlib.Path.read_text
        def no_gold_bytes(path, *args, **kwargs):
            self.assertNotIn(path.name, {"expected.json", "dataset.json"})
            return read_bytes(path, *args, **kwargs)
        def no_gold_text(path, *args, **kwargs):
            self.assertNotIn(path.name, {"expected.json", "dataset.json"})
            return read_text(path, *args, **kwargs)
        with mock.patch.object(pathlib.Path, "read_bytes", no_gold_bytes), mock.patch.object(pathlib.Path, "read_text", no_gold_text), contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(EXPERIMENT.collect(self.experiment, self.workspace))
        with contextlib.redirect_stdout(io.StringIO()):
            report = EXPERIMENT.score(self.experiment)
        self.assertTrue(report["primary_decision"]["accepted"], report["primary_decision"])
        self.assertEqual(report["summary"]["historical"]["candidate"]["pooled"]["valid"], 36)
        self.assertEqual(report["summary"]["constructed"]["candidate"]["pooled"]["valid"], 24)
        self.assertEqual(report["summary"]["constructed"]["original"]["pooled"]["missed_required_repro_actions"], 4)
        self.assertEqual(report["summary"]["constructed"]["candidate"]["pooled"]["missed_required_repro_actions"], 0)
        self.assertEqual(len(report["changed_actions"]), 2)
        self.assertEqual(report["summary"]["all"]["candidate"]["pooled"]["procedure_failures"], 0)
        score_path = self.experiment / "evidence/score.json"
        before = EXPERIMENT.digest(score_path)
        with self.assertRaisesRegex(ValueError, "already sealed"):
            EXPERIMENT.collect(self.experiment, self.workspace)
        with self.assertRaisesRegex(ValueError, "preserve existing score"):
            EXPERIMENT.score(self.experiment)
        self.assertEqual(EXPERIMENT.digest(score_path), before)
        first_batch, first_case = manifest["batches"][0], manifest["batches"][0]["cases"][0]
        directory = self.workspace / first_batch["id"] / "cases" / first_case["token"]
        with self.assertRaises(FileExistsError), contextlib.redirect_stdout(io.StringIO()):
            RECORDER.finish(directory, argparse.Namespace(labels=[], kinds="", refs="", reason="Replacement forbidden."))

    def test_changed_frozen_input_blocks_reproduction_without_rewriting_evidence(self):
        manifest = self.prepare()
        path = self.experiment / "evidence/frozen/cases/fixture-000/input.json"
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "frozen file changed"):
            EXPERIMENT.reproduce(self.experiment, self.directory / "changed-reconstruction")
        self.assertEqual(EXPERIMENT.load_manifest(self.experiment / "evidence"), manifest)

    def test_malformed_first_decision_stays_invalid_and_does_not_crash_scoring(self):
        manifest = self.prepare()
        self.finish_all(manifest, malformed_candidate=True)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertFalse(EXPERIMENT.collect(self.experiment, self.workspace))
            report = EXPERIMENT.score(self.experiment)
        row = next(row for row in report["case_runs"] if row["case_id"] == "fixture-018"
                   and row["arm"] == "candidate" and row["repetition"] == 1)
        self.assertFalse(row["scored"])
        self.assertFalse(row["pass"])
        self.assertIsNone(row["cost"])
        self.assertEqual(row["missed_required_repro_actions"], 2)
        self.assertFalse(report["primary_decision"]["accepted"])
        self.assertFalse(report["primary_decision"]["gates"]["complete_valid_coverage"])

    @contextlib.contextmanager
    def known_fixture(self, *, malformed=False):
        """A separate known-case collector fixture, without importing old tests."""
        output = self.experiment / "known"
        with mock.patch.multiple(KNOWN, HERE=self.experiment, OUTPUT=output,
                                 PREVIOUS=self.experiment / "cases/fixture-001"), \
                mock.patch.object(EXPERIMENT, "from_commit", side_effect=lambda repo, name: self.source[name]), \
                contextlib.redirect_stdout(io.StringIO()):
            KNOWN.prepare(self.workspace)
            directory = self.workspace / "cases/d001"
            checkout = directory / "checkout"
            RECORDER.start(directory, checkout)
            RECORDER.run_script(directory, checkout, "triage_checks", [])
            if malformed:
                proposal = {"writes_executed": False, "explanation": "Malformed synthetic label list.",
                            "items": [{"type": "add_labels", "labels": [["component/tray"]]}]}
                EXPERIMENT.write_json(directory / "proposal.json", proposal)
                RECORDER.record(directory, {"event": "assistant_decision", "content": proposal})
            else:
                RECORDER.run_script(directory, checkout, "check_labels", [EXPERIMENT.REPRO_LABEL])
                RECORDER.run_script(directory, checkout, "render_comment", ["--kinds", "need-repro", "--refs", ""])
                RECORDER.finish(directory, argparse.Namespace(labels=[EXPERIMENT.REPRO_LABEL], kinds="need-repro", refs="", reason="Fixture request."))
            yield output, directory

    def test_known_collector_checks_protocol_and_policy_before_writing(self):
        with self.known_fixture() as (output, _):
            for name, error in (("protocol.json", "known protocol changed"),
                                ("policies/candidate-SKILL.md", "known candidate policy changed")):
                path = self.experiment / name
                raw = path.read_bytes()
                path.write_bytes(raw + b" ")
                with self.assertRaisesRegex(ValueError, error):
                    KNOWN.collect(self.workspace)
                self.assertFalse((output / "proposal.json").exists())
                path.write_bytes(raw)
            KNOWN.collect(self.workspace)
            self.assertTrue(EXPERIMENT.read_json(output / "result.json")["adoption_prerequisite_passed"])

    def test_known_collector_checks_every_displayed_context(self):
        with self.known_fixture() as (output, directory):
            path = directory / "transcript.jsonl"
            events = [json.loads(line) for line in path.read_text().splitlines()]
            events.insert(1, {"event": "context", "content": "Changed later context."})
            path.write_text("".join(json.dumps(event) + "\n" for event in events))
            with self.assertRaisesRegex(ValueError, "displayed context differs"):
                KNOWN.collect(self.workspace)
            self.assertFalse((output / "proposal.json").exists())

    def test_known_collector_preserves_malformed_final_as_invalid(self):
        with self.known_fixture(malformed=True) as (output, _):
            KNOWN.collect(self.workspace)
            result = EXPERIMENT.read_json(output / "result.json")
            self.assertFalse(result["adoption_prerequisite_passed"])
            self.assertFalse(result["score"]["pass"])
            self.assertIsNone(result["score"]["cost"])
            self.assertFalse(EXPERIMENT.read_json(output / "actual.json")["scored"])


if __name__ == "__main__":
    unittest.main()
