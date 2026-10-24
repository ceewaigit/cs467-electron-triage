# cs467-electron-triage

This CS467 Assignment 3 sandbox tests an AI agent that gives new Electron issues a first
triage pass. It can add allowed labels and one comment assembled from fixed templates.
Maintainers still decide whether to close an issue or accept a contribution. The workflow
runs in `ceewaigit/cs467-electron-triage`; it is not deployed to `electron/electron`.

## Start here

1. Read [DESIGN.md](DESIGN.md) for the workflow choice, governance, results, five assignment
   questions and AI-use statement.
2. Read the [codebase guide](docs/CODEBASE.md) to follow one issue through the system and find
   each script's inputs, outputs and role.
3. Read the [evaluation guide](evals/golden/README.md) to inspect a case, reproduce the
   analysis offline and understand the limits of the recorded evidence.
4. Read the [audit](docs/AUDIT.md) for current findings and outstanding verification.

All commands in these documents start from this repository's root. Python scripts use Python
3.10 or later and the standard library; there is no dependency installation or application
build step. `gh` and `gh aw` are needed for workflow compilation and live sandbox runs.

```bash
python3 -m unittest discover -s tests -v
```

These tests run offline. They check the current scripts and configuration, including mocked
posting requests. They do not call the model or prove that GitHub enforces every control.
The updated credential worked for all five authorized targeted live runs. Their recorded
inference estimate is $1.2526727, including threat detection. This check is complete; the
separate 90-run plan remains pending. The
[offline reproduction steps](evals/golden/README.md#reproduce-the-analysis-offline) need no
GitHub login or provider credit; the live replay instructions are an optional future step.

## What the evidence covers

The current skill includes the reproduction-only clarification tested in the
[fresh comparison](evals/reproduction-check/ADOPTION.md). It fixed the known missed request
in one separate trial. Across 60 paired fresh trials, no scored regression was observed;
both versions already made every required and forbidden reproduction decision correctly.
The owner adopted it after reviewing those results. The experiment did not meet its original,
stricter improvement criteria, and its rejection report and all original results remain intact.
The earlier [linking/label candidate](evals/conservative-linking/README.md) was not adopted.

The preceding runtime source, commit `7ef6696a5f7f56112db829287c2d776e40411a57`, has a
[coding-assistant dry run](evals/golden/results/assistant-dry-run/README.md) covering all
30 cases once. Its proposed actions pass 20 of 25 real cases and all five adversarial cases.
Mean weighted error cost is 0.56 against 0.44 for the stored rule baseline, so this fallback
does not show an advantage on the preregistered cost measure.

Six fresh Codex subagents used that version's instructions and scripts, with expected outcomes
hidden. The configured Claude model was not executed. The recorder kept the displayed
context, helper calls and first proposed actions; no triage actions were published. This
checks the procedure and proposals, while GitHub permissions, threat detection, firewall,
budgets and posting remain outside the dry run. One trial per case does not replace the
planned three-repeat hosted evaluation.

The golden set has 25 real historical issues and five adversarial cases, with three planned
runs per case. The stored `final` experiment has 79 of 90 output records: 64 of 75 real-case
outputs and all 15 adversarial outputs. Eleven runs failed and lack collected output records.
The [evaluation guide](evals/golden/README.md#recorded-results-and-missing-runs) identifies them
and explains how missing runs affect the reported rates.

`final` is the historical experiment with template-only comments. The audited `hardened`
candidate is commit `5af79d55215dda9e0610278c42c71a4365edb25d`, with 0 of 90 planned valid
evaluation outputs. An earlier preflight at `401cbfa0b776b1f2b36d032b48946aa81d9c7c0e`
failed because of insufficient provider credit. The two commits have identical recorded
runtime-source hashes; the failed preflight supplies no valid triage result for either one.
See the [candidate manifest](evals/golden/replay/experiment-hardened.json) and
[preflight record](evals/golden/results/credit-check-2026-10-24.json).

The runtime used by the dry run includes the wording correction in renderer version 3:
the reproduction-request template no longer claims that a label was already added. Label
and comment jobs can finish independently. This change is newer than both candidate manifests.

A separate [recheck of the five old failures](evals/failure-recheck-offline/README.md) used
source `7debabe` once per case with fresh Codex assistants. It passed 1/5, with total weighted
error cost 11 versus 14 on those same five old decisions. Only the DevTools case changed by
dropping an uncertain similar link. The blind checker identifies the printing link as the
strongest residual risk; the other failures have defensible interpretations but remain scored.
Do not combine this selected diagnostic with the old 20 passes or attribute it to the skill edit.

Two authorized live preflights, [first](evals/failure-recheck-live/README.md) and
[refreshed-key retry](evals/failure-recheck-live-2/README.md), failed workspace authentication.
Both recorded zero inference usage and no triage writes; neither supplied a valid decision.

After a further secret update, the [third live attempt](evals/failure-recheck-live-3/README.md)
completed all five cases at source `1173463`, whose 15 runtime files match `7debabe` exactly.
The independent checker and frozen scorer agree: 3/5 pass, total weighted error cost 4,
and zero scored safety failures. Printing, DevTools and the upstream case pass; the GPU
reference and extra app label still fail their frozen targets. The app case also attempted
one disallowed shell command, which was denied before the permitted validators ran separately.
The recorded estimate is $0.7156697 for the agent plus $0.5370030 for detection, not an invoice.

These are five selected previous failures, once each, using configured Claude. They do not
replace the old Codex results or establish a causal improvement, full-suite rate or pass³.
Ordinary hosted execution now has evidence; current adversarial rejection and hard-limit
exhaustion do not. No further runs were dispatched. The full golden rerun and separate
90-run hardened plan remain pending.

## Repository map

| Path | Purpose |
|---|---|
| `.github/workflows/issue-triage.md` | Workflow source: triggers, permissions, tools, budgets and safe outputs |
| `.github/workflows/issue-triage.lock.yml` | Compiled GitHub Actions workflow; regenerate from the source |
| `.claude/skills/issue-triage/` | Agent procedure, deterministic checks, templates and label data |
| `scripts/` | Prepare the issue and limit the agent checkout; post a validated template after triage |
| `AGENTS.md`, `CONTRIBUTING.md`, `.github/CODEOWNERS` | Editing rules, AI policy and requested owner review |
| `data/` | Frozen search corpus and label snapshot available to the workflow |
| `evals/data/` | Opening-state research records used to build historical inputs |
| `evals/need/` | Q3 2026 evidence for the need for triage automation |
| `evals/golden/` | Frozen cases and expectations, collected outputs, logs and reports |
| `evals/conservative-linking/`, `evals/reproduction-check/` | Separate offline comparisons, frozen expectations, transcripts and reviews; current adoption decision in `reproduction-check/ADOPTION.md` |
| `evals/failure-recheck-offline/`, `evals/failure-recheck-live*/` | Five free diagnostic reruns, two failed live preflights and five completed live cases, with separate evidence and limits |
| `evals/controls/` | Deliberately broken configurations and adversarial control workflows |
| `evals/tools/` | Dataset preparation, replay, collection and analysis scripts |
| `tests/` | Offline script and configuration tests |

## Before submission

- Resolve or explicitly disclose the outstanding items in [the audit](docs/AUDIT.md), including
  the missing full-suite runs, two current scored mismatches and limits of hosted control testing.
- Check that every quoted number identifies its experiment and denominator. Preserve failed
  runs, frozen expectations and earlier results.
- Review the AI-use statement and be able to explain the workflow, each script, the evaluation
  limits and the reason for every permission. Use the questions in the
  [codebase guide](docs/CODEBASE.md#explain-the-submission) to prepare.
- Commit all required configuration, evidence and documentation, including generated lock
  files. Inspect the exact commit's file tree and rerun the offline checks from a clean copy.
- Submit one GitHub link through eLearn pointing to that specific commit. Later commits will
  not be marked. If the repository is private, add GitHub user `ctreude` as a collaborator
  before submitting. No PDF is required.

Human review and eLearn submission remain separate steps.
