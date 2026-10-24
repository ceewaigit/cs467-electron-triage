"""Execution failures must not become passing no-action evaluations."""
import contextlib
import io
import json
import pathlib
import sys
import tempfile
import types
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "evals/tools"))
import replay


class ReplayCollectionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.golden = pathlib.Path(self.temporary.name)
        self.output = self.golden / "cases/e001/actual/test"
        self.state = {
            "issues.json": {"e001": {"title": "Test issue", "labels_at_open": [], "issues": [1]}},
            "runs.json": {"1": {"case": "e001", "run": 1, "run_id": 100}},
            "live-skips.json": {"1": {"case": "e001", "runs": []}},
        }

    def collect(self, conclusion, actions=None):
        """Replace every network boundary with a deterministic saved-artifact fixture."""
        actions = actions or {"labels_added": [], "comment": None, "other_writes": []}
        session = {"type": "result", "is_error": conclusion != "success"}
        if conclusion == "failure":
            session.update(error="billing_error", result="Credit balance is too low")

        def fake_gh(*args, **kwargs):
            if args[:2] == ("run", "view"):
                return json.dumps({"status": "completed", "conclusion": conclusion,
                                   "headSha": "a" * 40, "headBranch": "audit-live-2026-10-24"})
            if args[:2] == ("run", "download"):
                artifact = pathlib.Path(args[args.index("-D") + 1]) / "artifact"
                artifact.mkdir()
                (artifact / "agent-session.jsonl").write_text(json.dumps(session) + "\n")
                return ""
            self.fail(f"Unexpected GitHub operation: {args}")

        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(replay, "GOLDEN", self.golden))
            stack.enter_context(mock.patch.object(replay, "VARIANT", "test"))
            stack.enter_context(mock.patch.object(replay, "load", side_effect=lambda name, default: self.state[name]))
            stack.enter_context(mock.patch.object(replay, "save"))
            stack.enter_context(mock.patch.object(replay, "cases", return_value=[("e001", {})]))
            gh = stack.enter_context(mock.patch.object(replay, "gh", side_effect=fake_gh))
            stack.enter_context(mock.patch.object(replay, "outcome", return_value=actions))
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            replay.cmd_collect(types.SimpleNamespace(cases=None, force=False))
            return gh.call_count

    def test_successful_no_action_remains_a_scorable_run(self):
        self.collect("success")
        result = json.loads((self.output / "run-1.json").read_text())
        self.assertEqual(result["conclusion"], "success")
        self.assertEqual(result["labels_added"], [])
        self.assertIsNone(result["comment"])
        self.assertEqual(result["head_sha"], "a" * 40)
        self.assertEqual(result["head_branch"], "audit-live-2026-10-24")
        self.assertIsNone(result["requested_ref"])
        self.assertTrue((self.output / "logs/run-1/agent-session.jsonl").exists())
        self.assertFalse((self.output / "failures").exists())

    def test_billing_failure_is_separate_and_preserves_diagnostic_log(self):
        self.collect("failure")
        self.assertEqual(list(self.output.glob("run-*.json")), [])
        result = json.loads((self.output / "failures/run-1.json").read_text())
        self.assertFalse(result["scored"])
        self.assertEqual(result["conclusion"], "failure")
        session = json.loads((self.output / "failures/logs/run-1/agent-session.jsonl").read_text())
        self.assertEqual(session["error"], "billing_error")
        self.assertFalse((self.output / "logs").exists())

    def test_failed_run_retains_partial_writes_for_audit(self):
        actions = {"labels_added": ["component/app"], "comment": None, "other_writes": []}
        self.collect("failure", actions)
        result = json.loads((self.output / "failures/run-1.json").read_text())
        self.assertEqual(result["labels_added"], ["component/app"])
        self.assertFalse((self.output / "run-1.json").exists())

    def test_non_success_conclusions_are_also_excluded(self):
        for conclusion in ("cancelled", "timed_out", "skipped", "neutral"):
            with self.subTest(conclusion=conclusion):
                self.collect(conclusion)
                failure = self.output / "failures/run-1.json"
                self.assertEqual(json.loads(failure.read_text())["conclusion"], conclusion)
                self.assertFalse((self.output / "run-1.json").exists())
                failure.unlink()

    def test_existing_success_or_failure_is_preserved_without_force(self):
        for relative in ("run-1.json", "failures/run-1.json"):
            with self.subTest(relative=relative):
                saved = self.output / relative
                saved.parent.mkdir(parents=True, exist_ok=True)
                saved.write_text("previous evidence\n")
                self.assertEqual(self.collect("failure"), 0)
                self.assertEqual(saved.read_text(), "previous evidence\n")
                saved.unlink()

    def test_requested_ref_is_preserved_alongside_observed_commit(self):
        self.state["runs.json"]["1"]["requested_ref"] = "audit-live-2026-10-24"
        self.collect("success")
        result = json.loads((self.output / "run-1.json").read_text())
        self.assertEqual(result["requested_ref"], "audit-live-2026-10-24")
        self.assertEqual(result["head_sha"], "a" * 40)


class ReplayDispatchTests(unittest.TestCase):
    def test_ref_forwarding_and_recorded_provenance(self):
        for ref in (None, "audit-live-2026-10-24"):
            with self.subTest(ref=ref), contextlib.ExitStack() as stack:
                states = {"issues.json": {"e001": {"issues": [1]}}, "runs.json": {}}
                stack.enter_context(mock.patch.object(replay, "load", side_effect=lambda name, default: states[name]))
                saved = stack.enter_context(mock.patch.object(replay, "save"))
                stack.enter_context(mock.patch.object(replay, "cases", return_value=[
                    ("e001", {"as_of": "2026-07-01T00:00:00Z", "author_association": "NONE"})]))
                stack.enter_context(mock.patch.object(replay.time, "sleep"))
                stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
                gh = stack.enter_context(mock.patch.object(replay, "gh", side_effect=[
                    "[]", "", json.dumps([{"databaseId": 100, "headSha": "b" * 40,
                                            "headBranch": ref or "main"}])]))
                replay.cmd_dispatch(types.SimpleNamespace(cases=None, k=1, ref=ref))
                dispatch_args = gh.call_args_list[1].args
                if ref:
                    self.assertEqual(dispatch_args[dispatch_args.index("--ref") + 1], ref)
                else:
                    self.assertNotIn("--ref", dispatch_args)
                record = saved.call_args.args[1]["1"]
                self.assertEqual(record["requested_ref"], ref)
                self.assertEqual(record["head_sha"], "b" * 40)
                self.assertEqual(record["head_branch"], ref or "main")

    def test_hardened_variant_uses_main_workflow_with_its_own_state(self):
        self.assertEqual(replay.WORKFLOWS["hardened"], replay.WORKFLOWS["agent"])
        with tempfile.TemporaryDirectory() as temporary, \
                mock.patch.object(replay, "STATE", pathlib.Path(temporary)), \
                mock.patch.object(replay, "VARIANT", "hardened"):
            replay.save("runs.json", {"1": {"run_id": 100}})
            self.assertTrue((pathlib.Path(temporary) / "runs-hardened.json").exists())
            self.assertFalse((pathlib.Path(temporary) / "runs-agent.json").exists())


if __name__ == "__main__":
    unittest.main()
