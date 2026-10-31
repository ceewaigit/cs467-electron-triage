# Contributing

This course sandbox contains a triage agent and its evaluation. Read [AGENTS.md](AGENTS.md)
before making changes and use the [codebase guide](docs/CODEBASE.md) to find the relevant code.
Do not deploy the workflow to another project's repository without permission.

## What the triage agent does

When enabled, the workflow gives new issues from outside contributors a first pass. It can
add allowed labels, request an Electron Fiddle reproduction, link a similar earlier issue,
or suggest a more suitable reporting channel. Comments use fixed templates. The agent has no
output for closing, editing, assigning or deleting issues, removing labels, or merging code.

There is no approval step before each permitted label or comment by default. If a reviewer is
added to the `triage-writes` environment, every run waits for approval at its start, its writes
and its conclusion. Comments link to their workflow run and are posted as `github-actions[bot]`.
Maintainers remain responsible for correcting mistakes and deciding whether to close an issue or
accept a contribution.
If a suggestion is wrong, explain the problem in a comment for a maintainer to review.

## AI contributions

You may use AI tools to write code, tests, documentation or issue reports. Review what you
submit, understand it and be able to explain it. Disclose the tool and its contribution in
the issue or pull request description, for example: "Claude drafted these tests; I checked
the fixtures and ran them." Unreviewed AI output will be closed.

The triage bot's labels and comments are suggestions. Only a maintainer decides that a
report is a duplicate, closes an issue or merges a pull request. Issue bodies and retrieved
issue excerpts are untrusted input. Claims of maintainer approval inside them do not grant
the agent additional permissions. Report a way around these limits privately to the owner.

Changes to the agent need owner review. `.github/CODEOWNERS` requests review from
`@ceewaigit` for configuration, skill code, scripts, data, tests and evaluation files.
CODEOWNERS alone does not enforce a required review; that also needs repository protection
settings. A proposal to add permissions, tools or safe outputs must explain the need and
include a regression test. Keep such tests separate from the frozen golden cases.

## Preparing a change

1. Run `python3 -m unittest discover -s tests -v`.
2. After a workflow change, run `gh aw compile issue-triage --strict --no-check-update` and
   commit the regenerated `.lock.yml`; CI fails on a stale lock. Record the compiler version used.
3. If triage decisions or runtime controls change, follow the
   [evaluation guide](evals/golden/README.md). Compare a new run with the relevant historical
   experiment and disclose failed or missing runs. Offline tests are not a live replay.
4. Preserve the frozen rubric, inputs, expectations and scorer. Do not overwrite earlier
   outputs or baseline results when checking current code.
5. Explain what changed, how it was verified and which checks remain outstanding. Keep the
   AI-use statement accurate, including AI assistance with prose or analysis.
