"""Execution failures must not become passing no-action evaluations."""
import contextlib
import io
import json
import pathlib
import shutil
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

    def collect(self, conclusion, actions=None, force=False):
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
            replay.cmd_collect(types.SimpleNamespace(cases=None, force=force))
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

    def test_force_refuses_success_to_failure_without_changing_evidence(self):
        self.collect("success")
        before = {str(p.relative_to(self.output)): p.read_bytes()
                  for p in self.output.rglob("*") if p.is_file()}
        with self.assertRaisesRegex(SystemExit, "fresh experiment namespace"):
            self.collect("failure", force=True)
        after = {str(p.relative_to(self.output)): p.read_bytes()
                 for p in self.output.rglob("*") if p.is_file()}
        self.assertEqual(after, before)

    def test_force_refuses_failure_to_success_without_changing_evidence(self):
        self.collect("failure")
        before = {str(p.relative_to(self.output)): p.read_bytes()
                  for p in self.output.rglob("*") if p.is_file()}
        with self.assertRaisesRegex(SystemExit, "fresh experiment namespace"):
            self.collect("success", force=True)
        after = {str(p.relative_to(self.output)): p.read_bytes()
                 for p in self.output.rglob("*") if p.is_file()}
        self.assertEqual(after, before)

    def test_force_can_refresh_within_the_same_category(self):
        for conclusion in ("success", "failure"):
            with self.subTest(conclusion=conclusion):
                self.collect(conclusion)
                changed = {"labels_added": ["component/app"], "comment": None, "other_writes": []}
                self.collect(conclusion, changed, force=True)
                result_path = self.output / ("run-1.json" if conclusion == "success" else "failures/run-1.json")
                self.assertEqual(json.loads(result_path.read_text())["labels_added"], ["component/app"])
                shutil.rmtree(self.output)


class ReplayDispatchTests(unittest.TestCase):
    def test_ref_forwarding_and_recorded_provenance(self):
        for ref in (None, "audit-live-2026-10-24", "refs/heads/audit-live-2026-10-24", "refs/tags/v1"):
            with self.subTest(ref=ref), contextlib.ExitStack() as stack:
                expected = ref.removeprefix("refs/heads/").removeprefix("refs/tags/") if ref else "main"
                states = {"issues.json": {"e001": {"issues": [1]}}, "runs.json": {}}
                stack.enter_context(mock.patch.object(replay, "load", side_effect=lambda name, default: states[name]))
                api = stack.enter_context(mock.patch.object(replay, "api", return_value={"default_branch": "main"}))
                saved = stack.enter_context(mock.patch.object(replay, "save"))
                stack.enter_context(mock.patch.object(replay, "cases", return_value=[
                    ("e001", {"as_of": "2026-07-01T00:00:00Z", "author_association": "NONE"})]))
                stack.enter_context(mock.patch.object(replay.time, "sleep"))
                stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
                gh = stack.enter_context(mock.patch.object(replay, "gh", side_effect=[
                    "[]", "", json.dumps([{"databaseId": 100, "headSha": "b" * 40,
                                            "headBranch": expected}])]))
                replay.cmd_dispatch(types.SimpleNamespace(cases=None, k=1, ref=ref))
                dispatch_args = gh.call_args_list[1].args
                if ref:
                    self.assertEqual(dispatch_args[dispatch_args.index("--ref") + 1], ref)
                else:
                    self.assertNotIn("--ref", dispatch_args)
                    api.assert_called_once_with(f"repos/{replay.REPO}")
                record = saved.call_args.args[1]["1"]
                self.assertEqual(record["requested_ref"], ref)
                self.assertEqual(record["head_sha"], "b" * 40)
                self.assertEqual(record["head_branch"], expected)

    def test_concurrent_runs_on_other_branches_are_not_paired(self):
        states = {"issues.json": {"e001": {"issues": [1]}}, "runs.json": {}}
        with mock.patch.object(replay, "load", side_effect=lambda name, default: states[name]), \
                mock.patch.object(replay, "save"), \
                mock.patch.object(replay, "cases", return_value=[
                    ("e001", {"as_of": "2026-07-01T00:00:00Z", "author_association": "NONE"})]), \
                mock.patch.object(replay.time, "sleep"), contextlib.redirect_stdout(io.StringIO()), \
                mock.patch.object(replay, "gh", side_effect=["[]", "", json.dumps([
                    {"databaseId": 999, "headSha": "wrong", "headBranch": "unrelated"},
                    {"databaseId": 100, "headSha": "right", "headBranch": "candidate"}])]):
            replay.cmd_dispatch(types.SimpleNamespace(cases=None, k=1, ref="candidate"))
        self.assertEqual(states["runs.json"]["1"]["run_id"], 100)
        self.assertEqual(states["runs.json"]["1"]["head_sha"], "right")

    def test_ambiguous_same_branch_runs_fail_without_saving_association(self):
        states = {"issues.json": {"e001": {"issues": [1]}}, "runs.json": {}}
        with mock.patch.object(replay, "load", side_effect=lambda name, default: states[name]), \
                mock.patch.object(replay, "save") as save, \
                mock.patch.object(replay, "cases", return_value=[
                    ("e001", {"as_of": "2026-07-01T00:00:00Z", "author_association": "NONE"})]), \
                mock.patch.object(replay.time, "sleep"), contextlib.redirect_stdout(io.StringIO()), \
                mock.patch.object(replay, "gh", side_effect=["[]", "", json.dumps([
                    {"databaseId": 101, "headSha": "same", "headBranch": "candidate"},
                    {"databaseId": 100, "headSha": "same", "headBranch": "candidate"}])]):
            with self.assertRaisesRegex(SystemExit, "cannot safely pair"):
                replay.cmd_dispatch(types.SimpleNamespace(cases=None, k=1, ref="candidate"))
            save.assert_not_called()
        self.assertEqual(states["runs.json"], {})

    def test_hardened_variant_uses_main_workflow_with_its_own_state(self):
        self.assertEqual(replay.WORKFLOWS["hardened"], replay.WORKFLOWS["agent"])
        with tempfile.TemporaryDirectory() as temporary, \
                mock.patch.object(replay, "STATE", pathlib.Path(temporary)), \
                mock.patch.object(replay, "VARIANT", "hardened"):
            replay.save("runs.json", {"1": {"run_id": 100}})
            self.assertTrue((pathlib.Path(temporary) / "runs-hardened.json").exists())
            self.assertFalse((pathlib.Path(temporary) / "runs-agent.json").exists())


class OutcomeTests(unittest.TestCase):
    def test_writes_by_other_accounts_count_against_the_run(self):
        timeline = [
            {"event": "labeled", "actor": {"login": "owner"}, "label": {"name": "platform/macOS"}},
            {"event": "labeled", "actor": {"login": "owner"}, "label": {"name": "component/menu"}},
            {"event": "commented", "user": {"login": "owner"}, "body": "closing"},
            {"event": "labeled", "actor": {"login": replay.BOT}, "label": {"name": "component/gpu"}},
        ]

        def fake_api(path, *args, **kwargs):
            return timeline if path.endswith("/timeline") else {"state": "open"}

        with mock.patch.object(replay, "api", fake_api):
            result = replay.outcome(1, ["platform/macOS"])
        self.assertEqual(result["labels_added"], ["component/gpu"])
        self.assertEqual(result["other_writes"], ["labeled component/menu by owner", "commented by owner"])


if __name__ == "__main__":
    unittest.main()
