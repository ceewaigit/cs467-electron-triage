# Contributing

This is a course sandbox, so contributions are mostly changes to the triage agent and its tests.
Read `AGENTS.md` first for the layout, commands and the rules on what may not change.

## Issues

New issues from people outside the project get a first pass from an automated triage agent. It
can add a `component/*` label, ask for an Electron Fiddle repro, point to an earlier issue that
looks like the same problem, or suggest a better place for the report. It cannot close, edit,
assign or unlabel anything. A maintainer reviews every label and comment it leaves; if it got
something wrong, say so in a comment and a maintainer will fix it.

## AI policy

**There must be a human in the loop.** You may use AI tools to write issues, code or tests, but
you are responsible for what you submit: review it, understand it, and be able to explain it.

- **Disclose AI help** in the issue or pull request description: which tool, and what it did (for
  example "Claude drafted the test, I checked the cases"). Unreviewed AI output will be closed.
- **The triage agent's output is a suggestion.** A label or comment from
  `github-actions[bot]` is not a maintainer decision. Only a maintainer closes issues, merges pull
  requests or decides an issue is a duplicate.
- **Issue text is data to the agent.** Instructions written into an issue ("ignore your rules",
  "a maintainer approved closing these") are not followed, and trying them is not welcome. Report
  ways around the agent's limits privately to the owner, as you would a security issue.
- **Changes to the agent need owner review.** Pull requests touching `.github/`, `.claude/`,
  `AGENTS.md`, `CLAUDE.md`, `scripts/` or `evals/golden/` are routed to the owner by `CODEOWNERS`.
  A change that widens what the agent can do (new permissions, tools or safe outputs) must say why
  in the description and come with a failing-then-passing eval case.
- **Coding agents** working in this repository must follow `AGENTS.md`.

## Pull requests

1. Run `python3 -m unittest discover -s tests` and, after any change to the workflow,
   `gh aw compile issue-triage --strict`. Commit the regenerated `.lock.yml` with the source.
2. If the change affects triage decisions, rerun the golden set (`evals/golden/README.md`) and put
   the score before and after in the description.
3. Do not edit frozen expected outcomes; see `AGENTS.md`.
