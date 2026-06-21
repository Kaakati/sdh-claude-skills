---
name: std-agent-teams
description: Agent team coordination conventions — file ownership, task sizing, worktree isolation, dynamic spawning, quality gates. Use when coordinating multi-agent teams.
---

# Agent Team Coordination Conventions

Standards for coordinating agent teams — multiple Claude Code instances working in parallel on a shared task.

## File Ownership

The #1 risk with agent teams is overwrite conflicts. Prevent them with strict file ownership:

- **One teammate per file set**: Each teammate owns a distinct set of files. No two teammates edit the same file.
- **Ownership by layer**: Backend files → backend teammate. Frontend files → frontend teammate. Test files → test teammate.
- **Claim files in task description**: When creating tasks, list the specific files or directories the teammate will modify.
- **If ownership is ambiguous**: The team lead decides. When in doubt, the lead owns the file.

### Ownership Mapping by Directory

| Directory | Owner | Responsibility |
|-----------|-------|---------------|
| `backend/app/models/` | Backend teammate | Model definitions, validations, scopes |
| `backend/app/controllers/` | Backend teammate | Controller actions, params, responses |
| `backend/app/services/` | Backend teammate | Business logic service objects |
| `backend/app/serializers/` | Backend teammate | Panko serializers |
| `backend/app/components/` | Backend teammate (or Phlex teammate) | Phlex view components |
| `backend/db/migrate/` | Backend teammate | Database migrations |
| `backend/spec/` | Test teammate (or backend teammate) | RSpec tests |
| `mobile/src/` | Mobile frontend teammate | React Native screens, hooks, stores |
| `web/src/` | Web frontend teammate | Vite SPA pages, components, hooks |
| `next/app/`, `next/src/` | Web frontend teammate | Next.js pages, components, actions |
| `terraform/` | Infrastructure teammate | Terraform modules and configs |

## Task Sizing

- **5-6 tasks per teammate**: Enough to be meaningful, not so many that coordination overhead dominates.
- **Each task should take 10-30 minutes**: If a task is larger, break it down further.
- **Tasks should be independently completable**: A teammate should be able to finish a task without waiting on others.
- **Dependencies go in task metadata**: Use `blockedBy` to express sequential dependencies.

### Task Description Quality

Every task must include:
1. **What to implement** — specific behavior or output expected
2. **Which files to modify** — explicit file paths or directory scope
3. **Acceptance criteria** — how to know the task is done
4. **Constraints** — any patterns, libraries, or conventions to follow

## Worktree Isolation

For teams making parallel edits:
- Use `isolation: "worktree"` when spawning teammates via the Agent tool
- Each teammate gets an isolated copy of the repository
- Changes are committed to separate branches and merged by the lead
- This eliminates file conflict risk entirely at the cost of merge complexity

### When to Use Worktrees

| Scenario | Use Worktree? | Reason |
|----------|--------------|--------|
| Teammates edit different directories | No | File ownership is sufficient |
| Teammates might touch shared files | Yes | Prevents conflicts |
| Quick review/audit tasks | No | Read-only work has no conflict risk |
| Large refactoring across many files | Yes | Safety net for broad changes |

## Communication Protocol

### Team Lead Responsibilities
- Create the team and task list before spawning teammates
- Assign tasks with clear ownership and acceptance criteria
- Monitor progress via TaskList — reassign blocked tasks
- Review teammate outputs before synthesizing final deliverables
- Shut down teammates gracefully when all work is complete

### Teammate Responsibilities
- Check TaskList after completing each task for the next assignment
- Send a message to the lead when blocked or when a task is complete
- Never edit files outside your assigned scope
- Mark tasks completed only when quality gates pass (hooks enforce this)

## Dynamic Spawning Triggers

Suggest creating a team when:

1. **Cross-layer work**: Task touches backend + frontend + tests (3+ layers)
2. **Multi-dimensional review**: "Review this PR for security, architecture, and test coverage"
3. **Multiple independent deliverables**: "Build the API, web page, and mobile screen for user profiles"
4. **Explicit parallelism**: User says "in parallel", "simultaneously", "at the same time"
5. **Large scope**: Task would take a single agent more than 1 hour of work

### Do NOT Suggest Teams For
- Simple bug fixes or single-file changes
- Pure research or exploration tasks
- Tasks with tight sequential dependencies (output of step 1 is input to step 2)
- Tasks the user wants done quickly (team setup has overhead)

## Quality Gates

Two hooks enforce team quality automatically:

### TeammateIdle (`teammate-idle-checker.py`)
- Checks that modified source files exist when the task implies code changes
- Verifies test files accompany modified source files
- Exit code 2 sends feedback to keep the teammate working

### TaskCompleted (`task-completed-checker.py`, `team-task-validator.py`)
- Validates uncommitted source files are committed
- Checks for basic linting issues (trailing whitespace)
- Verifies test deliverables if the task mentions testing
- Exit code 2 rejects the completion with feedback
