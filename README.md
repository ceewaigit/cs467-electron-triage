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
Further paid evaluation has been deferred by the owner. The
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

Historical logs establish what the recorded version did. Offline tests and coding-assistant
transcripts support the tested procedures and proposed decisions. The latest skill has not
been rerun on the full golden set; its five earlier mismatches remain recorded. The full hosted
acceptance protocol remains unassessed, and all 90 planned hardened evaluations stay pending.

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
| `evals/controls/` | Deliberately broken configurations and adversarial control workflows |
| `evals/tools/` | Dataset preparation, replay, collection and analysis scripts |
| `tests/` | Offline script and configuration tests |

## Before submission

- Resolve or explicitly disclose the outstanding items in [the audit](docs/AUDIT.md), including
  the missing runs and the lack of live evidence for the latest configuration.
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
