#!/usr/bin/env python3
"""
TaskCompleted hook: a task's deliverables must exist before it closes.

Contract (https://code.claude.com/docs/en/hooks, "TaskCompleted"): "TaskCompleted hooks receive
`task_id`, `task_subject`, and optionally `task_description`, `teammate_name`, and `team_name`",
plus the common cwd and session_id. It fires "when any agent explicitly marks a task as completed
through the TaskUpdate tool, or when an agent team teammate finishes its turn with in-progress
tasks", so not only in agent teams. Exit 2: "the task is not marked as completed and the stderr
message is fed back to the model as feedback". A reason printed to stdout lands in the debug log.

TaskCreated carries the same input fields. There this script only snapshots the task's baseline
and always exits 0: exit 2 or `{"decision": "block"}` on TaskCreated deletes the task.

The git state, test-file detection, attribution (`touched_scope`) and block cap live in
`_teamgate.py`, shared with teammate-idle-checker.py and team-task-validator.py.

Gates: (1) a teammate commits its own worktree for handoff; (2) a task that promises tests leaves
test files among its changes, commits included (committing them used to fail this gate).

Exit codes: 0 accepted (and always on TaskCreated), 2 rejected with the reason on stderr.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _hooklib as hooklib  # noqa: E402
import _teamgate as teamgate  # noqa: E402

# Write intent, not a mention: "Run the test suite" names no test file to add, and a hard reject
# must name a remedy the agent can carry out. Word boundaries stay load-bearing ("latest").
TEST_INTENT = re.compile(
    r"\b(add|adding|write|writing|create|creating|implement|implementing|update|updating|"
    r"extend|extending|improve|improving|increase|increasing)\b[^.;\n]*\b(tests?|specs?|coverage)\b"
    r"|\b(tests?|specs?) for\b"
)


def gate_uncommitted(repo, scope, data):
    """Gate 1: a teammate hands off its own worktree by committing it. Never in a solo session
    (committing is the developer's call) and never in a shared tree (whose files are these?)."""
    if not (repo["linked"] and data.get("teammate_name")):
        return []
    pending = sorted(p for p in (scope or ()) if teamgate.is_source_file(p))
    if not pending:
        return []
    shown = ", ".join(pending[:5]) + (f" (+{len(pending) - 5} more)" if len(pending) > 5 else "")
    return [f"Uncommitted source changes in this teammate's worktree: {shown}. Commit them with a "
            "conventional commit (the `std-git-workflow` skill) so the lead can merge the work."]


def gate_tests(repo, scope, data):
    """Gate 2: a task that promises tests leaves test files among its changes, committed included."""
    text = f"{data.get('task_subject') or ''} {data.get('task_description') or ''}".lower()
    if not TEST_INTENT.search(text):
        return []
    candidates = set(scope) if scope is not None else {path for _, path in repo["entries"]}
    if any(teamgate.is_test_file(p) for p in candidates | teamgate.committed_paths(repo, data)):
        return []
    return ["Task mentions testing but no test files were modified (working tree or commits made "
            "for this work). Add the tests per the `std-testing` skill, or reword the task if it "
            "never asked for new tests."]


def main():
    data = hooklib.load_event()
    if not isinstance(data, dict) or not data:
        sys.exit(0)
    repo = teamgate.repo_state(str(data.get("cwd") or os.getcwd()))
    if data.get("hook_event_name") == "TaskCreated":
        if repo:
            teamgate.write_baseline(repo, data)
        sys.exit(0)  # exit 2 on TaskCreated would delete the task
    if repo is None:
        sys.exit(0)  # no git work tree: nothing observable to judge
    scope = teamgate.touched_scope(repo, data)
    feedback = gate_uncommitted(repo, scope, data) + gate_tests(repo, scope, data)
    if feedback:
        subject = data.get("task_subject") or data.get("task_id") or ""
        teamgate.block(data, "task-completed-checker", [f"Task completion rejected for '{subject}':"] + feedback)
    sys.exit(0)


if __name__ == "__main__":
    main()
