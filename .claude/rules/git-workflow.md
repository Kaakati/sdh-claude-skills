# Git Workflow

Universal rules for version control, commit messages, branching, and pull requests.

## Conventional Commits

All commit messages must follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
type(scope): short description

[optional body]

[optional footer(s)]
```

### Types

| Type       | Purpose                                          | Example                                        |
|------------|--------------------------------------------------|------------------------------------------------|
| `feat`     | New feature for users                            | `feat(auth): add SSO login with Google`        |
| `fix`      | Bug fix                                          | `fix(cart): resolve race condition on checkout` |
| `docs`     | Documentation changes only                       | `docs(api): update authentication endpoints`   |
| `refactor` | Code change that neither fixes a bug nor adds a feature | `refactor(user): extract validation logic` |
| `test`     | Adding or updating tests                         | `test(orders): add edge cases for discount`    |
| `chore`    | Maintenance tasks, dependency updates            | `chore(deps): upgrade express to 4.19`         |
| `perf`     | Performance improvement                          | `perf(search): add index for full-text query`  |
| `ci`       | CI/CD configuration changes                      | `ci: add parallel test execution`              |
| `build`    | Build system or external dependency changes      | `build: update webpack to v5`                  |
| `style`    | Formatting, whitespace (no logic change)         | `style: fix linting warnings`                  |

### Rules

- Subject line: imperative mood, lowercase, no period, max 72 characters.
- Body: explain **what** and **why**, not how. Wrap at 80 characters.
- Breaking changes: add `BREAKING CHANGE:` in the footer or `!` after the type.
  ```
  feat(api)!: change authentication response format

  BREAKING CHANGE: The /auth/login endpoint now returns { token, refreshToken }
  instead of { accessToken, expiresIn }.
  ```

## Branch Naming

Format: `type/TICKET-ID-short-description`

| Type      | Pattern                                | Example                           |
|-----------|----------------------------------------|-----------------------------------|
| Feature   | `feature/TICKET-123-description`       | `feature/PROJ-42-user-dashboard`  |
| Bug fix   | `bugfix/TICKET-456-description`        | `bugfix/PROJ-87-login-timeout`    |
| Hotfix    | `hotfix/TICKET-789-description`        | `hotfix/PROJ-101-payment-crash`   |
| Release   | `release/vX.Y.Z`                       | `release/v2.1.0`                  |
| Chore     | `chore/description`                    | `chore/upgrade-node-20`           |

- Use lowercase and hyphens. No spaces or underscores.
- Keep descriptions short but meaningful (3-5 words max).
- Always include the ticket/issue ID when one exists.

## Pull Request Requirements

Every PR must include:

1. **Title**: Follow conventional commit format — `type(scope): description`
2. **Description**: Context for why the change is needed. Link to the ticket/issue.
3. **Test Plan**: How the change was tested. Include commands to run tests.
4. **Screenshots**: Required for any UI changes (before/after).
5. **Breaking Changes**: Clearly called out with migration instructions.
6. **Checklist**:
   - [ ] Tests pass locally
   - [ ] Linting passes
   - [ ] No new warnings introduced
   - [ ] Documentation updated if needed
   - [ ] Reviewed my own diff before requesting review

### PR Size

- Target **under 400 lines changed** per PR. Smaller PRs get faster, better reviews.
- If a feature is large, break it into incremental PRs behind a feature flag.
- Separate refactoring from feature work — do not mix them in one PR.

## Merge Strategy

- **Squash merge** to main/master — keeps the main branch history clean with one commit per PR.
- **Rebase** feature branches onto the target branch before merging to keep history linear.
- Delete the source branch after merge.
- Never use merge commits for feature branches into main.

## Protected Branches

- **No force pushes** to `main`, `master`, or `develop`. Ever.
- **No direct pushes** to protected branches. All changes go through PRs.
- Require at least one approval before merge.
- Require CI to pass before merge is allowed.
- Enable branch protection rules in the repository settings.

## Release Process

- Tag releases with semantic versioning: `vMAJOR.MINOR.PATCH`
- Create release branches from `main` for release preparation.
- Hotfixes branch from the release tag, merge back to both `main` and the release branch.
- Write release notes summarizing changes, linking to relevant PRs.
