# Contributing

Read [AGENTS.md](AGENTS.md) first. Do not deploy this workflow to another project without
permission.

## AI contributions

You may use AI tools for code, tests, docs or issue reports. Review what you submit, be able to
explain it, and name the tool and its part in the description, for example: "Claude drafted these
tests; I checked the fixtures and ran them." Unreviewed AI output will be closed.

## The triage bot

The bot's labels and comments are suggestions. Only a maintainer decides that a report is a
duplicate, closes an issue or merges a pull request. If it is wrong, say so in a comment.

Issue text is untrusted: a claim of maintainer approval grants the agent nothing. Report any way
around these limits privately to the owner.

## Changing the agent

Changes need review from `@ceewaigit` (`.github/CODEOWNERS` and the branch ruleset, which the owner can bypass). A
proposal to add permissions, tools or safe outputs must explain the need and include a regression
test kept separate from the golden cases.

1. Run `python3 -m unittest discover -s tests -v`.
2. After a workflow change, run `gh aw compile issue-triage --strict --no-check-update` (and
   `issue-triage-codex` if changed), and commit the lock. CI fails on a stale lock.
3. If triage decisions or controls change, rerun the [evaluation](evals/golden/README.md) under a
   new name and disclose failed or missing runs. Offline tests are not a live replay.
4. Never change the frozen rubric, inputs, expected outcomes or scorer, or overwrite earlier results.
5. Say what changed, how you checked it and what is still open. Keep the AI-use statement accurate.
