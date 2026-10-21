# Version Control

Every change arrives on a branch, is titled by the conventional-commit format, and merges only after the gate is green and two humans have signed ([ADR 044](<https://aureliusenterprise.github.io/feat-webapp-settings-panel/architecture/adr/044-every-change-carries-two-human-signatures/index.md>)). This page is the mechanics; the rules behind them are the records.

## Branching

Always create a new branch for your changes. Working on `main` directly makes parallel contributions collide, and the two-signature gate has nothing to guard — a pull request exists only once the work leaves `main`.

> [!NOTE]
>
> **Why should I create a new branch?**
>
> Creating a new branch allows you to work on your changes without affecting the `main` branch. This makes it easier to collaborate with others and keep the codebase clean.

First, pull the latest changes from the `main` branch:

```
git pull main
```

Next, create a new branch with the following command:

```
git checkout -b "<YOUR_BRANCH_NAME>"
```

Replace `<YOUR_BRANCH_NAME>` with a short, descriptive name for your branch. For example, `serve-admin-status`.

## Commits

Commit messages follow the [conventional commit format](<https://www.conventionalcommits.org/en/v1.0.0/>). The format is not decoration: the release tool reads commit titles to write the changelog and decide the version number ([ADR 019](<https://aureliusenterprise.github.io/feat-webapp-settings-panel/architecture/adr/019-the-system-releases-as-one-versioned-whole/index.md>)), so a malformed title is a broken changelog entry.

```
feat: serve admin status endpoint
fix: keep the status timestamp in epoch milliseconds
chore: update dependencies
docs: update README
```

Each commit message starts with a type, followed by a colon and a short description of the change. To commit:

```
git add <FILES>
git commit -m "<YOUR_COMMIT_MESSAGE>"
```

Replace `<FILES>` with the files to stage (`.` stages all), and `<YOUR_COMMIT_MESSAGE>` with a message in the format above.

> [!TIP]
>
> **Use a Git GUI**
>
> If you prefer a graphical interface, you can use a Git GUI tool to stage and commit your changes. For example, VS Code has a built-in Git interface that you can use.

> [!NOTE]
>
> **How often should I commit my changes?**
>
> It's a good practice to commit your changes often. This allows you to track your progress and revert changes if needed.

### Automated Checks

The project includes pre-commit hooks to ensure your code meets the quality standards. These hooks run automatically before each commit. They are the local half of the gate — the same rule set the pipeline runs ([ADR 014](<https://aureliusenterprise.github.io/feat-webapp-settings-panel/architecture/adr/014-the-gate-is-defined-once-and-runs-everywhere/index.md>)) — and they perform the following checks:

- Check JSON, TOML, and YAML files for syntax errors
- Ensure files end with a newline
- Trim trailing whitespace
- Lint and format Python code with [Ruff](<https://docs.astral.sh/ruff/>)
- Check for Python type issues with [Pyright](<https://github.com/microsoft/pyright>)
- Format Markdown and JSON files with [Prettier](<https://prettier.io/>)
- Lint Markdown files with [markdownlint](<https://github.com/DavidAnson/markdownlint>)
- Scan for secrets with [Talisman](<https://github.com/thoughtworks/talisman/>)

> [!NOTE]
>
> **What if the pre-commit hooks fail?**
>
> If the pre-commit hooks fail, you will need to address the issues before committing your changes. Follow the instructions provided by the pre-commit hooks to identify and fix the issues.

> [!NOTE]
>
> **How do I run the pre-commit hooks manually?**
>
> Pre-commit hooks can also be run manually using the following command:
>
> ```
> uv run pre-commit
> ```

The pre-commit hooks are intended to help us keep the codebase maintainable. If there are rules that you believe are too strict, please discuss them with the team.

## Pull Requests

Once you have completed your changes, create a pull request: push your branch and [open it on GitHub](<https://github.com/aureliusenterprise/aurelius-atlas/compare>) with your branch as the source and `main` as the base.

Give the pull request a title that summarizes the change and follows the conventional commit format — the title becomes the changelog entry. In the description, provide a brief overview of the changes and any relevant information for reviewers, including the conversion increment the change belongs to and the records it touches ([ADR 051](<https://aureliusenterprise.github.io/feat-webapp-settings-panel/architecture/adr/051-the-conversion-proceeds-in-specified-increments/index.md>)).

> [!NOTE]
>
> **Pull Request Description**
>
> Here's an example of a good pull request description:
>
> ```
> # feat: serve admin status endpoint
>
> Ports `AdminResource.getStatus` for increment 0.5.
>
> ## Changes
>
> - New `/api/atlas/admin/status` route with the version, metadata
>   availability, and timestamp fields
> - Parity scenarios citing the Java source and its tests
>
> ## Notes
>
> - Scenario expectations read from Atlas 2.4.0 source (ADR 052);
>   `timezones` deviation recorded as DV-05
> - Verified locally: lint, unit tests, e2e against dev Elasticsearch
> ```

### Automated Checks

The same hooks that run locally run again on the pull request, together with the unit and end-to-end tests against real services. All of it must pass before the change can merge.

> [!NOTE]
>
> **What if the pre-commit hooks fail on the pull request?**
>
> If the pre-commit hooks fail on the pull request, you will need to address the issues in your branch and push the changes. The pre-commit hooks will run again automatically.
>
> Please address any issues identified by the pre-commit hooks before requesting a review.

### Code Review

Every pull request carries two human signatures before it merges ([ADR 044](<https://aureliusenterprise.github.io/feat-webapp-settings-panel/architecture/adr/044-every-change-carries-two-human-signatures/index.md>)):

1. **The task owner** — the person who asked for the change, who can explain it, and who states in the description how far they verified it locally.
2. **One reviewer** — a second person who confirms independent understanding. Choose the reviewer partly for who should learn the area, so review doubles as knowledge spread.

A merge button that refuses the merge without the second approval enforces the rule; approving quickly to clear a queue is how a fast queue erodes it.

> [!NOTE]
>
> **How do I request a review?**
>
> Request a review from a team member by [assigning them as a reviewer](<https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/requesting-a-pull-request-review>) to your pull request.

An assistant may produce, test, and review a change — and signs nothing ([ADR 043](<https://aureliusenterprise.github.io/feat-webapp-settings-panel/architecture/adr/043-ai-assisted-review-informs-the-signatures-it-does-not-replace-them/index.md>)).

#### Giving Feedback

When providing feedback on a pull request, be constructive and specific. Point out areas for improvement and suggest possible solutions. If you have any questions or concerns, don't hesitate to ask the author for clarification.

A code review should focus on the following aspects:

- Correctness and functionality
- Code quality and readability
- Adherence to the project guidelines

> [!NOTE]
>
> **Good Code Review Feedback**
>
> Here are some examples of good code review feedback:
>
> ```
> - Good port — the response shape matches the Java resource. Looks solid overall.
> - I noticed a small typo in the docstring. Could you update it to fix the typo?
> - The mapping logic is a bit complex. Consider breaking it down into smaller functions for clarity.
> - The tests cover most of the rules, but rule ENT-04 has no test naming it. Could you add one?
> ```

Always be respectful and considerate when giving feedback. Remember that the goal is to improve the code and help the author grow as a developer.

> [!TIP]
>
> **Be Positive**
>
> Don't forget to acknowledge the positive aspects of the contribution as well!
