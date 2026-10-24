# CS467 Assignment 3 — Configuring and Governing an AI Agent for an Open-Source Workflow

## Purpose

Configure an existing AI agent to support a real open-source workflow, test the configuration on historical cases, and justify your design decisions. Both the configuration and its justification will be assessed.

## Choosing a workflow

- Choose a workflow in an open-source project, such as:
  - issue triage
  - first-pass PR review
  - CI-failure analysis
  - duplicate detection
  - changelog drafting
- Explain why an AI agent is appropriate for this workflow rather than conventional automation.
- Use repository data to establish the need for automation (e.g., time to first issue response, number of PRs awaiting review).
- State what you measured, over which period, and the limitations of the metric.
- Students may choose the same project and workflow, but must develop and evaluate their configurations independently.

## What to do

### 1. Configure the agent

Implement the following:

- **Workflow:** A GitHub Agentic Workflow (or platform equivalent) with:
  - a trigger
  - explicit permissions
  - allowed tools
  - safe outputs with limits
  - a timeout
  - restricted network access where supported
  - The agent must **not** be able to close or delete issues, merge PRs, or force-push.
- **AGENTS.md:** Repository instructions covering build and test commands, project structure, conventions, and forbidden changes.
- **Claude Skill:** A `SKILL.md` defining the procedure the agent follows, with supporting scripts where useful.
  - Automate checks that do not require model judgement (e.g., label validation, duplicate searches).
  - Verify that the agent running your workflow loads and uses the skill.
- **CONTRIBUTING.md:** An AI-contribution policy if the workflow produces material that humans later submit, or if its rules apply to all contributors.

Put each rule where it can be enforced:

- Repository facts → `AGENTS.md`
- Procedures → the skill
- Hard restrictions → workflow permissions and safe outputs
- An instruction telling the model not to perform an action is not a substitute for preventing that action.

### 2. Test the configuration

- Run the agent in a **sandbox repository you control**, using a copy or representative subset of the original project.
- Do not deploy it to someone else's project without permission.
- Collect **at least 10 real historical inputs** (issues, PRs, CI failures, etc.), **including cases requiring no action**.
  - Preserve the context needed to evaluate each case (relevant repository files, issue history, CI logs).
  - Avoid information that became available only after the original event.
  - **Record the expected outcome for each case before running the agent.**
- Construct **at least one adversarial input** to test the agent's safeguards.
- Run the agent and compare its actual output with the expected outcome for every case.
- Report all failures and explain them. A successful workflow execution does not establish that the agent made the correct decisions.
- If end-to-end execution is not possible:
  - explain why
  - conduct a dry run using a coding assistant with the same configuration and inputs
  - keep the transcripts
  - identify which controls you could not test

### 3. Govern the agent

For each control below, implement it or explain why it is unnecessary or unsupported. Choose controls based on the actions your agent can perform, rather than implementing mechanisms that serve no purpose.

| Control | Meaning |
|---|---|
| Identity | Agent actions are attributed to a bot or application, not a personal account. |
| Least privilege | Read-only permissions by default. |
| Safe outputs | Explicitly allowed actions with enforced limits. |
| Human approval | Required reviews, draft PRs, or CODEOWNERS where appropriate. |
| Budgets | Limits on runs, outputs, runtime, and model usage. |
| Audit trail | Records of triggers, model versions, tool calls, outputs, and costs where available. |
| Kill switch | A mechanism for maintainers to stop the agent, including handling running executions. |
| Drift detection | When golden tasks are rerun, which outputs humans review, and who reviews them. |
| Accountability | Who can change or disable the configuration, and who is responsible for the agent's actions. |

- Distinguish **implemented and tested** controls from those that are **only proposed**.
- Identify the **untrusted inputs** the agent reads and the **actions** it can perform.

#### Five questions (answer referring to your configuration)

1. An issue instructs the agent to close all stale issues and claims maintainer approval. What happens? **Test this case.**
2. The provider updates the model and a golden task starts failing. How and when would you detect this?
3. The project receives 300 issues in one week. What happens under your rate limits?
4. A tool or MCP server returns malicious instructions. What can the agent still do?
5. A maintainer needs to stop the agent using only a phone. What steps are required?

### 4. Justify the design

In `DESIGN.md`, explain:

- why you chose this workflow
- why the controls fit its risks
- one alternative you rejected
- what you deliberately prevented the agent from doing
- what your tests revealed
- what remains unresolved
- for each governance control, briefly how it is implemented or why it is absent, referring to the relevant configuration files

## Deliverables

Submit a Git repository containing:

- **Configuration:**
  - workflow files in `.github/workflows/` (including the compiled `.lock.yml` for GitHub Agentic Workflows)
  - `AGENTS.md`
  - `.claude/skills/<name>/SKILL.md`
  - supporting scripts
  - `CONTRIBUTING.md` where applicable
- **`evals/golden/`:** historical inputs, expected outcomes, actual outputs, and test logs, with instructions for reproducing the evaluation.
- **`DESIGN.md`:**
  - design justification
  - governance summary
  - an **agent bill of materials** identifying: the model (including whether its version is pinned), instructions, tools and MCP servers, permissions, data sources, logs, evaluations, and responsible humans
  - answers to the five questions
  - ends with an **AI-use statement**: which parts you wrote, which were AI-generated, and how you verified them

### DESIGN.md constraints

- **Max 150 lines**, including headings and blank lines.
- Normal Markdown formatting; do not combine paragraphs into unusually long lines.
- No length limit on configuration files, evaluation data, or logs.

## Submission

- Submit **one GitHub link** through eLearn, pointing to the **specific commit** you want marked.
- If the repository is private, add GitHub user **ctreude** as a collaborator before submitting.
- All required files must be present at that commit. Later commits will not be marked.
- No PDF is required.
- You may use AI tools throughout, but you must be able to explain every part of your submission.
