"""The watchdog and drift-check workflows hold write tokens but must stay free of AI and secrets."""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXPECTED = {
    "triage-watchdog.yml": {"actions: read", "contents: read", "issues: write"},
    "drift-check.yml": {"actions: write", "contents: read", "issues: write"},
}


class PlainWorkflows(unittest.TestCase):
    def test_permissions_secrets_and_triggers(self):
        for name, permissions in EXPECTED.items():
            with self.subTest(workflow=name):
                text = (ROOT / ".github/workflows" / name).read_text()
                block = re.search(r"^permissions:\n((?:  .*\n)+)", text, re.M).group(1)
                granted = {line.split("#")[0].strip() for line in block.splitlines()}
                self.assertEqual(granted, permissions)
                self.assertNotIn("secrets.", text)
                # Issue authors cannot start either workflow.
                on_block = text.split("\non:\n", 1)[1].split("\npermissions:", 1)[0]
                triggers = set(re.findall(r"^  ([a-z_]+):", on_block, re.M))
                self.assertLessEqual(triggers, {"workflow_run", "workflow_dispatch", "schedule"})
                self.assertIn("persist-credentials: false", text)

    def test_weekly_drift_run_is_switched_by_a_variable(self):
        text = (ROOT / ".github/workflows/drift-check.yml").read_text()
        self.assertIn("if: github.event_name == 'workflow_dispatch' || vars.DRIFT_WEEKLY == 'true'", text)


if __name__ == "__main__":
    unittest.main()
