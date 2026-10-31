# Workflow data

This directory contains the local data used by the triage scripts. It has no credentials.
Issue titles and bodies remain untrusted, even when stored in a repository file.

| File | Contents and source |
|---|---|
| `labels.json` | Electron's label names, descriptions and colours, fetched on 23 October 2026 with `gh label list -R electron/electron --limit 400 --json name,description,color` |
| `issue-corpus.jsonl` | One JSON object per issue opened from 1 July 2025 to 30 September 2026, excluding bots, plus the synthetic row described below |

The sandbox uses the same label names as the snapshot. The skill's
`assets/allowed-labels.txt` selects the labels the agent may propose; the workflow's
`safe-outputs.add-labels.allowed` patterns restrict which existing labels it may add.
The model cannot create labels.

The corpus was frozen on 23 October 2026 from the opening-state records fetched by
`evals/tools/fetch_issues.py`. Each row has `number`, `created_at`, `title` and `body`; bodies
are truncated to 4,000 characters. Later comments, labels and close reasons are excluded.
The fetcher reconstructs the opening title and body from GitHub history where available;
the source records and their `body_source` values are in `evals/data/`.

`triage_checks.py` ranks earlier issues using BM25, a word-overlap ranking method. It only
returns rows whose `created_at` precedes the input's `as_of` time. A candidate is evidence for
the model to assess, not a duplicate decision. The renderer checks referenced issue numbers
against the corpus and rejects the synthetic test row.

Row `900001` is synthetic. It contains a prompt injection used by adversarial case
`a5-poisoned-corpus`; it is not an Electron issue and must never become a public reference.
Keep it in this evaluation corpus so the retrieval attack remains reproducible.

Current preparation filters the corpus on disk for each run (offline tests; used by the
[five live runs](../evals/failure-recheck-live-3/README.md) at `1173463`). Git history stays
readable, and historical runs had the full corpus. See [the failures list](../docs/FAILURES.md).

These files differ from `evals/need/raw/`, which contains later issue activity for measuring
triage delays, and from `evals/golden/`, which contains expected outcomes and run evidence.
Those evaluation records must not be available to the triage agent.
