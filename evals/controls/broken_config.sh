#!/usr/bin/env bash
# Control test: break copies of the workflow in two ways and show which layer stops each.
#   1. issues: write        -> gh aw compile --strict must refuse it
#   2. safe output close-issue (permissions unchanged) -> the compiler accepts it,
#      so tests/test_skill_scripts.py WorkflowConfig must fail on it
#   3. add-comment back (free-text comments)            -> config tests must fail
#   4. add-labels target "*" (any issue)                 -> config tests must fail
# Exit 0 only if every break is caught and the real workflow still passes.
set -uo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
status=0

break_copy() {  # $1 = python replacement snippet; prints the work dir
  local w; w=$(mktemp -d)
  mkdir -p "$w/.github/workflows"; cp -R "$root/.claude" "$w/"
  cp "$root/.github/workflows/issue-triage.md" "$w/.github/workflows/"
  (cd "$w" && git init -q && python3 -c "
import pathlib; p = pathlib.Path('.github/workflows/issue-triage.md'); s = p.read_text()
$1
p.write_text(s)")
  echo "$w"
}

echo "== break 1: permissions issues: write"
w=$(break_copy 's = s.replace("  issues: read\n", "  issues: write\n")')
if (cd "$w" && gh aw compile issue-triage --strict --approve --no-check-update >"$w/out.txt" 2>&1); then
  echo "NOT CAUGHT: compiler accepted issues: write"; status=1
else
  grep -m1 "strict mode" "$w/out.txt"; echo "caught by: gh aw compile --strict"
fi
rm -rf "$w"

echo "== break 2: safe output close-issue (max 50)"
w=$(break_copy 's = s.replace("safe-outputs:\n", "safe-outputs:\n  close-issue:\n    max: 50\n")')
if (cd "$w" && gh aw compile issue-triage --strict --approve --no-check-update >"$w/out.txt" 2>&1); then
  echo "compiler accepted it ($(grep -c close_issue "$w/.github/workflows/issue-triage.lock.yml") close_issue lines in the lock file)"
else
  echo "compiler refused it:"; tail -3 "$w/out.txt"
fi
out=$(cd "$root" && WORKFLOW_DIR="$w/.github/workflows" python3 -m unittest tests.test_skill_scripts.WorkflowConfig 2>&1)
echo "$out" | grep -E "^(FAIL|ERROR):|^FAILED|^OK"
if echo "$out" | grep -q "^FAIL: test_no_closing_or_merging_outputs"; then
  echo "caught by: tests/test_skill_scripts.py WorkflowConfig"
else
  echo "NOT CAUGHT by the config tests"; status=1
fi
rm -rf "$w"

config_break() {  # $1 = label, $2 = python replacement, $3 = test that must fail
  echo "== $1"
  local w; w=$(break_copy "$2")
  (cd "$w" && gh aw compile issue-triage --strict --approve --no-check-update >"$w/out.txt" 2>&1) \
    && echo "compiler accepted it" || { echo "compiler refused it:"; tail -2 "$w/out.txt"; }
  local out; out=$(cd "$root" && WORKFLOW_DIR="$w/.github/workflows" python3 -m unittest tests.test_skill_scripts.WorkflowConfig 2>&1)
  if echo "$out" | grep -q "^FAIL: $3"; then echo "caught by: WorkflowConfig.$3"; else echo "NOT CAUGHT"; status=1; fi
  rm -rf "$w"
}
config_break "break 3: add-comment (free text)" \
  's = s.replace("safe-outputs:\n", "safe-outputs:\n  add-comment:\n    max: 1\n")' test_no_closing_or_merging_outputs
config_break "break 4: add-labels target \"*\"" \
  'import re; s = re.sub(r"(add-labels:[\s\S]*?    target: ).*", lambda m: m.group(1) + chr(34) + "*" + chr(34), s, count=1)' test_outputs_pinned_to_the_runs_issue

echo "== real workflow"
(cd "$root" && python3 -m unittest tests.test_skill_scripts.WorkflowConfig 2>&1 | tail -1) | grep -q OK \
  && echo "config tests pass" || { echo "config tests FAIL on the real workflow"; status=1; }
[ $status = 0 ] && echo "CONTROL PASSED" || echo "CONTROL FAILED"
exit $status
