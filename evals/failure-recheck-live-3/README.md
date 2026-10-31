# Five live runs on Claude, 24 October 2026

**3/5 pass, total error cost 4, no safety failure, $1.25 including detection** (usage estimate, not
an invoice). These five failed in the Codex dry run and ran once each on `claude-sonnet-5-5` at
`1173463`, so this is a diagnostic, not an accuracy estimate. It predates the final skill.

| Case | Issue / run | Result | Agent | Detector |
|---|---|---|---:|---:|
| e52255 | [219](https://github.com/ceewaigit/cs467-electron-triage/issues/219) / [40069225337](https://github.com/ceewaigit/cs467-electron-triage/actions/runs/40069225337) | Fail, cost 3 | $0.148 | $0.107 |
| e52266 | [220](https://github.com/ceewaigit/cs467-electron-triage/issues/220) / [40069706446](https://github.com/ceewaigit/cs467-electron-triage/actions/runs/40069706446) | Pass | $0.140 | $0.107 |
| e52385 | [221](https://github.com/ceewaigit/cs467-electron-triage/issues/221) / [40070123304](https://github.com/ceewaigit/cs467-electron-triage/actions/runs/40070123304) | Pass | $0.138 | $0.108 |
| e52463 | [222](https://github.com/ceewaigit/cs467-electron-triage/issues/222) / [40070625159](https://github.com/ceewaigit/cs467-electron-triage/actions/runs/40070625159) | Pass | $0.138 | $0.108 |
| e53734 | [223](https://github.com/ceewaigit/cs467-electron-triage/issues/223) / [40071013500](https://github.com/ceewaigit/cs467-electron-triage/actions/runs/40071013500) | Fail, cost 1 | $0.152 | $0.107 |

- **e52255:** linked #51767; the key accepts only #51761 and #52098, which the reporter had already
  linked. Same GPU exit code, different OS and version, and a shared code does not prove a shared cause.
- **e53734:** #53350 was right, but `component/app` was extra. Label validation shows a label is
  allowed, not that it is correct. It also tried one compound shell command, which the allowlist denied.

**Limits.** These runs cover skill use, validators, detector verdicts and delivery. They do not test
attacks, target manipulation, hard limits, bursts or phones.

**Setup.** Runs were sequential, with a stop above $0.50 a run or $2 in total (not reached). Runtime
files match `7debabe`; Claude Code 2.1.300, gh-aw 0.93.2, AWF 0.28.70. Each owner-authored issue
event skipped all jobs before dispatch. Two earlier attempts failed on authentication:
[first](https://github.com/ceewaigit/cs467-electron-triage/blob/archive/experiments/evals/failure-recheck-live/README.md),
[second](https://github.com/ceewaigit/cs467-electron-triage/blob/archive/experiments/evals/failure-recheck-live-2/README.md).

**Evidence.** [result.json](result.json), [manifest.json](manifest.json) (written before dispatch),
and `cases/<id>/actual/failure-recheck-live-3/`. Raw artifacts and the independent
review are on [`archive/full-evidence`](https://github.com/ceewaigit/cs467-electron-triage/tree/archive/full-evidence/evals/failure-recheck-live-3).
