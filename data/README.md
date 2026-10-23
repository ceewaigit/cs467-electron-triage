# Sandbox data

- `labels.json`: the label set of electron/electron, from `gh label list -R electron/electron --limit 400 --json name,description,color` on 23 Oct 2026. The sandbox repo is given the same labels so the agent's allowlist matches real Electron labels.
- `issue-corpus.jsonl`: electron/electron issues opened 1 Jul 2025 to 30 Sep 2026 (bots excluded), frozen on 23 Oct 2026, built by `evals/tools/fetch_issues.py`. Each row has only what was public when the issue was opened: number, opening time, opening title and opening body (truncated to 4,000 characters). Later comments, labels and close reasons are left out on purpose. The duplicate search only returns rows opened before the issue it is triaging.
- Row `900001` is **synthetic**. It is a planted issue carrying a prompt injection, used by adversarial case `a5-poisoned-corpus`. It is not a real Electron issue.
