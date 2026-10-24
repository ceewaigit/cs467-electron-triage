"""Template choices must preserve private disclosure and cite only real corpus rows."""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
RENDERER = pathlib.Path(".claude/skills/issue-triage/scripts/render_comment.py")


class CommentTemplateBoundaries(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = pathlib.Path(self.directory.name)
        (self.root / RENDERER).parent.mkdir(parents=True)
        shutil.copy2(ROOT / RENDERER, self.root / RENDERER)
        (self.root / "data").mkdir()
        # Arbitrary IDs ensure rejection depends on metadata, not golden-case numbers.
        corpus = [{"number": 23456}, {"number": 34567, "synthetic": True}]
        (self.root / "data/issue-corpus.jsonl").write_text(
            "".join(json.dumps(issue) + "\n" for issue in corpus)
        )

    def render(self, kinds, refs=""):
        return subprocess.run(
            [sys.executable, str(self.root / RENDERER), "--kinds", kinds, "--refs", refs],
            capture_output=True, text=True,
        )

    def test_security_only_is_accepted(self):
        result = self.render("security")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("reported privately", result.stdout)

    def test_repro_request_does_not_claim_a_label_was_applied(self):
        # Comment and label jobs run separately, so posting cannot assert label success.
        result = self.render("need-repro")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("Electron Fiddle", result.stdout)
        self.assertNotIn("blocked/need-repro", result.stdout)

    def test_security_cannot_request_public_follow_up(self):
        for other in ("need-repro", "similar", "support", "upstream", "third-party", "site-policy"):
            with self.subTest(other=other):
                result = self.render(f"security,{other}", "23456")
                self.assertEqual(result.returncode, 1)
                self.assertNotIn("-----BEGIN COMMENT-----", result.stdout)

    def test_synthetic_reference_is_rejected(self):
        result = self.render("similar", "34567")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("-----BEGIN COMMENT-----", result.stdout)

    def test_real_reference_is_accepted(self):
        result = self.render("similar", "23456")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("`electron/electron#23456`", result.stdout)


if __name__ == "__main__":
    unittest.main()
