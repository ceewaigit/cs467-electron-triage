"""Evidence boundaries for the paired experiment, using only temporary fake cases."""
import argparse
import contextlib
import importlib.util
import io
import json
import pathlib
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EXPERIMENT = load_module("paired_experiment", ROOT / "evals/conservative-linking/experiment.py")
RECORDER = load_module("paired_recorder", ROOT / "evals/tools/offline_dry_run.py")
REPLAY = load_module("paired_replay", ROOT / "evals/tools/replay.py")


class ExperimentEvidenceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = pathlib.Path(temporary.name)
        self.experiment = self.directory / "evaluator"
        self.workspace = self.directory / "runners"
        self.policies = {"original": b"Original fixture skill.\n", "candidate": b"Candidate fixture skill.\n"}
        paths = [
            EXPERIMENT.SKILL,
            ".claude/skills/issue-triage/assets/allowed-labels.txt",
            ".claude/skills/issue-triage/references/components.json",
            *[f"{EXPERIMENT.SCRIPT_DIRECTORY}/{script}.py" for script in RECORDER.SCRIPTS],
            ".github/workflows/issue-triage.lock.yml", ".github/workflows/issue-triage.md",
            "AGENTS.md", "CLAUDE.md", EXPERIMENT.CORPUS, "data/labels.json",
            "scripts/post_triage_comment.py", "scripts/prepare_agent_context.py", "scripts/prepare_issue.py",
        ]
        self.source = {name: b"Input-only fixture source.\n" for name in paths}
        for script in ("check_labels", "render_comment"):
            name = f"{EXPERIMENT.SCRIPT_DIRECTORY}/{script}.py"
            self.source[name] = (ROOT / name).read_bytes()
        self.source[EXPERIMENT.SKILL] = self.policies["original"]
        self.source[".claude/skills/issue-triage/assets/allowed-labels.txt"] = b"component/tray\ncomponent/app\n"
        self.source[EXPERIMENT.CORPUS] = self.corpus_bytes()
        self.source[EXPERIMENT.OLD_MANIFEST] = EXPERIMENT.json_bytes({"runtime_sha256": {name: "old" for name in paths}})
        for name in (EXPERIMENT.RECORDER, EXPERIMENT.SCORER, "evals/tools/replay.py"):
            self.source[name] = (ROOT / name).read_bytes()
        self.protocol = {
            "baseline_commit": EXPERIMENT.BASELINE, "repetitions_per_arm_per_case": 2,
            "policy_sha256": {arm: EXPERIMENT.sha256(raw) for arm, raw in self.policies.items()},
            "decision_rule": ["Fixture declaration; production protocol is never loaded by these tests."],
        }
        self.expected = {
            "decision": "triage",
            "labels": {"required": [], "acceptable": [], "one_of": [], "forbidden": []},
            "comment": {"required_kinds": [], "acceptable_kinds": [], "refs_any": [], "must_not_match": []},
        }
        cases = []
        for number in range(1, 31):
            case_id = f"fixture-{number:03}"
            cases.append({"id": case_id, "group": "historical" if number <= 24 else "constructed",
                          "positive_controls": [], "coverage_supported_refs": []})
            opening = {"id": case_id, "set": "fixture", "source": "private evaluator marker",
                       "title": "Question from @example about owner/project#1234",
                       "body": "See https://github.com/owner/project/issues/1234 and @example.",
                       "as_of": "2026-04-02T00:00:00Z", "labels_at_open": [], "author_association": "NONE"}
            EXPERIMENT.write_json(self.experiment / "cases" / case_id / "input.json", opening)
            EXPERIMENT.write_json(self.experiment / "cases" / case_id / "expected.json", self.expected)
        self.dataset = {"cases": cases}
        EXPERIMENT.write_json(self.experiment / "dataset.json", self.dataset)
        EXPERIMENT.write_json(self.experiment / "protocol.json", self.protocol)
        for arm, raw in self.policies.items():
            EXPERIMENT.write_new(self.experiment / "policies" / f"{arm}-SKILL.md", raw)
        EXPERIMENT.write_new(self.experiment / "cases/fixture-025/corpus.jsonl", self.corpus_bytes(60000))

    @staticmethod
    def corpus_bytes(first_number=50000):
        return b"".join((json.dumps({"number": first_number + index, "created_at": date,
                                     "title": "Fixture issue", "body": "Fixture evidence"}) + "\n").encode()
                        for index, date in enumerate(("2026-04-01T00:00:00Z", "2026-04-02T00:00:00Z", "2026-04-03T00:00:00Z")))

    def prepare(self):
        with mock.patch.object(EXPERIMENT, "from_commit", side_effect=lambda repo, name: self.source[name]), \
                contextlib.redirect_stdout(io.StringIO()):
            return EXPERIMENT.prepare(self.experiment, ROOT, self.workspace)

    def finish_all(self, manifest, *, rejected_call=False, invalid_final=False, optional_link_case=None):
        """Write simulated recorder fixtures, never decisions on the real dataset."""
        first = True
        for batch in manifest["batches"]:
            for case in batch["cases"]:
                directory = self.workspace / batch["id"] / "cases" / case["token"]
                with contextlib.redirect_stdout(io.StringIO()):
                    RECORDER.start(directory, directory / "checkout")
                    if first and rejected_call:
                        RECORDER.record(directory, {"event": "script",
                            "command": ["python3", f"{EXPERIMENT.SCRIPT_DIRECTORY}/render_comment.py", "--kinds", "invalid"],
                            "exit_code": 1, "stdout": "Fixture rejection retained.\n", "stderr": ""})
                    labels = ["priority/invalid"] if first and invalid_final else []
                    link = case["case_id"] == optional_link_case
                    RECORDER.finish(directory, argparse.Namespace(labels=labels, kinds="similar" if link else "",
                                    refs="50000" if link else "", reason="Fixture decision."))
                first = False

    def collect(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return EXPERIMENT.collect(self.experiment, self.workspace)

    def test_preparation_is_paired_private_and_exactly_reproducible(self):
        manifest = self.prepare()
        self.assertEqual(len(manifest["batches"]), 12)
        self.assertEqual(sum(len(batch["cases"]) for batch in manifest["batches"]), 120)
        self.assertTrue(all(len(batch["cases"]) == 10 for batch in manifest["batches"]))
        for repetition in (1, 2):
            orders = {arm: [case for batch in manifest["batches"] if batch["arm"] == arm and batch["repetition"] == repetition
                            for case in batch["cases"]] for arm in EXPERIMENT.ARMS}
            self.assertEqual([case["case_id"] for case in orders["original"]],
                             [case["case_id"] for case in orders["candidate"]])
            self.assertEqual([case["token"] for case in orders["original"]],
                             [case["token"] for case in orders["candidate"]])
        self.assertFalse(any(path.name in {"expected.json", "dataset.json", "manifest.json", ".git"}
                             for path in self.workspace.rglob("*")))
        for batch in manifest["batches"]:
            prompt = (self.workspace / batch["id"] / "INSTRUCTIONS.md").read_text()
            self.assertNotIn("candidate", prompt.lower())
            self.assertNotIn("original", prompt.lower())
            for case in batch["cases"]:
                directory = self.workspace / batch["id"] / "cases" / case["token"]
                context = EXPERIMENT.read_json(directory / "context.json")
                issue = EXPERIMENT.read_json(directory / "checkout/.triage/issue.json")
                self.assertNotIn("case_id", context)
                self.assertNotIn("source", issue)
                self.assertNotIn("id", issue)
                self.assertNotIn("set", issue)
                self.assertEqual(issue["number"], 800000 + int(case["token"][1:]))
                self.assertIn("@\u200bexample", issue["body"])
                self.assertEqual(context["earlier_corpus_rows"], 1)
                corpus = (directory / "checkout" / EXPERIMENT.CORPUS).read_text().splitlines()
                self.assertEqual(json.loads(corpus[0])["number"], 60000 if case["case_id"] == "fixture-025" else 50000)
                self.assertEqual((directory / "checkout" / EXPERIMENT.SKILL).read_bytes(), self.policies[batch["arm"]])
        reconstructed = self.directory / "reconstructed"
        with contextlib.redirect_stdout(io.StringIO()):
            EXPERIMENT.reproduce(self.experiment, reconstructed)
        hashes = lambda root: {str(path.relative_to(root)): EXPERIMENT.digest(path) for path in root.rglob("*") if path.is_file()}
        self.assertEqual(hashes(self.workspace), hashes(reconstructed))
        with self.assertRaisesRegex(ValueError, "preserve existing evidence"):
            self.prepare()

    def test_neutralisation_is_exactly_replay_and_cutoff_is_strict(self):
        for text in ("@one, @two-user, a@domain", "https://github.com/electron/electron/issues/12345#comment-1",
                     "owner/project#1234 `owner/project#1234` https://www.github.com/o/r/pull/5555"):
            self.assertEqual(EXPERIMENT.neutralise(text), REPLAY.neutralise(text))
        earlier, count = EXPERIMENT.earlier_corpus(self.corpus_bytes(), "2026-04-02T00:00:00Z")
        self.assertEqual(count, 1)
        self.assertEqual(json.loads(earlier)["number"], 50000)
        with self.assertRaisesRegex(ValueError, "invalid UTC timestamp"):
            EXPERIMENT.earlier_corpus(b'{"created_at":"not a date"}\n', "2026-04-02T00:00:00Z")

    def test_collection_never_reads_gold_and_keeps_intermediate_rejections(self):
        manifest = self.prepare()
        self.finish_all(manifest, rejected_call=True)
        original_reader = pathlib.Path.read_bytes
        original_text_reader = pathlib.Path.read_text

        def guard_bytes(path, *args, **kwargs):
            self.assertNotIn(path.name, {"expected.json", "dataset.json"})
            return original_reader(path, *args, **kwargs)

        def guard_text(path, *args, **kwargs):
            self.assertNotIn(path.name, {"expected.json", "dataset.json"})
            return original_text_reader(path, *args, **kwargs)

        with mock.patch.object(pathlib.Path, "read_bytes", guard_bytes), mock.patch.object(pathlib.Path, "read_text", guard_text):
            self.assertTrue(self.collect())
        batch = manifest["batches"][0]
        case = batch["cases"][0]
        destination = self.experiment / "cases" / case["case_id"] / "actual" / batch["arm"]
        outcome = EXPERIMENT.read_json(destination / "run-1.json")
        self.assertFalse(outcome["writes_executed"])
        self.assertTrue(outcome["scored"])
        self.assertEqual(len(outcome["procedure"]["rejected_script_calls"]), 1)
        self.assertTrue((destination / "logs/run-1/transcript.md").exists())
        before = EXPERIMENT.digest(destination / "run-1.json")
        with self.assertRaisesRegex(ValueError, "already sealed"):
            self.collect()
        self.assertEqual(before, EXPERIMENT.digest(destination / "run-1.json"))
        with contextlib.redirect_stdout(io.StringIO()):
            report = EXPERIMENT.score(self.experiment)
        self.assertEqual(report["summary"]["historical"]["original"]["pooled"]["full_case_passes"], 48)
        self.assertEqual(report["summary"]["constructed"]["candidate"]["1"]["full_case_passes"], 6)
        self.assertFalse(report["primary_decision"]["accepted"])

    def test_incomplete_or_changed_sessions_cannot_be_sealed(self):
        manifest = self.prepare()
        self.finish_all(manifest)
        batch, case = manifest["batches"][0], manifest["batches"][0]["cases"][0]
        directory = self.workspace / batch["id"] / "cases" / case["token"]
        proposal = directory / "proposal.json"
        raw = proposal.read_bytes()
        proposal.unlink()
        with self.assertRaises(FileNotFoundError):
            self.collect()
        self.assertFalse((self.experiment / "evidence/sealed-proposals.json").exists())
        EXPERIMENT.write_new(proposal, raw)
        (directory / "checkout" / EXPERIMENT.SKILL).write_text("Changed policy.")
        with self.assertRaisesRegex(ValueError, "prepared file changed"):
            self.collect()
        self.assertFalse((self.experiment / "evidence/sealed-proposals.json").exists())

    def test_invalid_final_is_preserved_and_cannot_become_a_noop_pass(self):
        manifest = self.prepare()
        self.finish_all(manifest, invalid_final=True)
        self.assertFalse(self.collect())
        batch, case = manifest["batches"][0], manifest["batches"][0]["cases"][0]
        destination = self.experiment / "cases" / case["case_id"] / "actual" / batch["arm"]
        outcome = EXPERIMENT.read_json(destination / "run-1.json")
        self.assertFalse(outcome["scored"])
        self.assertTrue(outcome["invalid_final_proposal"])
        self.assertEqual(outcome["labels_added"], ["priority/invalid"])
        validation = EXPERIMENT.read_json(destination / "logs/run-1/export-validation.json")
        self.assertEqual(validation[0]["exit_code"], 1)
        with contextlib.redirect_stdout(io.StringIO()):
            report = EXPERIMENT.score(self.experiment)
        row = next(row for row in report["case_runs"] if row["case_id"] == case["case_id"] and row["arm"] == batch["arm"] and row["repetition"] == 1)
        self.assertFalse(row["pass"])
        self.assertIsNone(row["cost"])
        self.assertFalse(report["primary_decision"]["gates"]["complete_valid_coverage"])

    def test_acceptable_optional_link_is_not_an_unsupported_reference(self):
        # The annotation permits this uncertain link without counting it as a
        # strong positive-control match. Freeze that distinction before outputs.
        case = self.dataset["cases"][0]
        case["acceptable_optional_refs"] = [50000]
        (self.experiment / "dataset.json").write_bytes(EXPERIMENT.json_bytes(self.dataset))
        expected = json.loads(json.dumps(self.expected))
        expected["comment"].update(acceptable_kinds=["similar"], refs_any=[50000])
        (self.experiment / "cases" / case["id"] / "expected.json").write_bytes(EXPERIMENT.json_bytes(expected))
        manifest = self.prepare()
        self.finish_all(manifest, optional_link_case=case["id"])
        self.collect()
        with contextlib.redirect_stdout(io.StringIO()):
            report = EXPERIMENT.score(self.experiment)
        rows = [row for row in report["case_runs"] if row["case_id"] == case["id"]]
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(row["pass"] and row["refs"] == [50000] for row in rows))
        self.assertTrue(all(row["unsupported_refs"] == [] for row in rows))

    def test_changed_export_refuses_scoring(self):
        manifest = self.prepare()
        self.finish_all(manifest)
        self.collect()
        batch, case = manifest["batches"][0], manifest["batches"][0]["cases"][0]
        path = self.experiment / "cases" / case["case_id"] / "actual" / batch["arm"] / "run-1.json"
        path.write_text("{}\n")
        with self.assertRaisesRegex(ValueError, "collected evidence changed"):
            EXPERIMENT.score(self.experiment)
        self.assertFalse((self.experiment / "evidence/score.json").exists())

    def test_export_tool_failure_is_explicit_and_never_fabricates_comment(self):
        proposal = {"writes_executed": False, "explanation": "Fixture", "items": [
            {"type": "triage_comment", "kinds": "similar", "refs": "50000"}]}
        with mock.patch.object(EXPERIMENT.subprocess, "run", side_effect=subprocess.TimeoutExpired("fixture", 30)):
            outcome, validations = EXPERIMENT.export_proposal(proposal, self.directory)
        self.assertFalse(outcome["scored"])
        self.assertIsNone(outcome["comment"])
        self.assertIsNone(validations[0]["exit_code"])
        self.assertIn("timed out", validations[0]["error"])


class ExperimentDecisionTests(unittest.TestCase):
    def test_optional_positive_actions_need_actual_coverage(self):
        expected = {"labels": {"required": [], "acceptable": ["component/tray"], "one_of": []}}
        metadata = {"positive_controls": ["link", "component"], "coverage_supported_refs": [50000]}
        self.assertEqual(EXPERIMENT.positive_coverage(expected, metadata, set(), set(), set()),
                         {"link": False, "component": False})
        self.assertEqual(EXPERIMENT.positive_coverage(expected, metadata, {"component/tray"}, {"similar"}, {50000}),
                         {"link": True, "component": True})
        self.assertFalse(EXPERIMENT.positive_coverage(expected, metadata, set(), set(), {50000})["link"])

    def test_primary_rule_requires_both_repetitions_and_no_new_unsupported_refs(self):
        rows = []
        for repetition in (1, 2):
            for arm in EXPERIMENT.ARMS:
                for number in range(30):
                    rows.append({"case_id": str(number), "arm": arm, "repetition": repetition,
                                 "group": "historical" if number < 24 else "constructed", "scored": True,
                                 "pass": True, "cost": 1 if arm == "original" and number < 24 else 0,
                                 "missed_required_actions": 0, "safety": False, "unsupported_refs": [],
                                 "discretionary_labels": [], "discretionary_links": [],
                                 "positive_controls": ["link"] if number == 24 else [],
                                 "positive_control_coverage": {"link": True} if number == 24 else {}})
        protocol = {"decision_rule": ["Fixture rule"]}
        self.assertTrue(EXPERIMENT.primary_decision(rows, protocol)["accepted"])
        candidate = next(row for row in rows if row["arm"] == "candidate" and row["repetition"] == 2)
        candidate["unsupported_refs"] = [59999]
        result = EXPERIMENT.primary_decision(rows, protocol)
        self.assertFalse(result["accepted"])
        self.assertFalse(result["gates"]["run_2_unsupported_references_not_higher"])
        candidate["unsupported_refs"] = []
        positive = next(row for row in rows if row["arm"] == "candidate" and row["positive_controls"])
        positive["positive_control_coverage"]["link"] = False
        self.assertFalse(EXPERIMENT.primary_decision(rows, protocol)["accepted"])


if __name__ == "__main__":
    unittest.main()
