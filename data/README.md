# Workflow data

Local data for the triage scripts. It holds no credentials, and issue text stays untrusted.

| File | Contents |
|---|---|
| `labels.json` | Electron's labels, fetched 23 October 2026 |
| `issue-corpus.jsonl` | Non-bot issues opened 1 July 2025 to 30 September 2026, as first written, cut to 4,000 characters, plus row `900001` |

**Row `900001` is synthetic.** It is the injection for `a5-poisoned-corpus`. It must stay here for
that test and must never become a public reference. Remove it before any deployment.

`triage_checks.py` ranks earlier issues with BM25 (word overlap) and returns only those opened
before `as_of`. A match is evidence for the model to judge, not a duplicate decision. Each run also
filters the corpus on disk; the original runs at `5ab5169` had the full corpus.

Keep this apart from `evals/need/raw/` and `evals/golden/`: they hold later outcomes the agent must
not see.
