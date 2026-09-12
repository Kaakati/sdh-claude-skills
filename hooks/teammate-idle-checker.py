#!/usr/bin/env python3
"""
TeammateIdle hook: keep a teammate working while its OWN change set has a gap it can close.

Contract (https://code.claude.com/docs/en/hooks, "TeammateIdle"): "TeammateIdle hooks receive
`teammate_name` and `team_name`" ("Deprecated. Session-derived team name; will be removed in a
future release"), plus the common cwd and session_id. The common `agent_type` is only "present when
the session uses --agent or the hook fires inside a subagent". Exit 2: "the teammate receives the
stderr message as feedback and continues working instead of going idle".

The event carries no task text, no teammate id and no task status. The old reads of agent_name and
task_description, and the code-intent gate built on them, never matched a real event and are gone.

Role: the member entry for teammate_name in THIS session's team config gives the agent type
(`agentType`, observed: sdh:code-reviewer -> code-reviewer). An agent whose `tools:` line holds no
file-edit tool cannot satisfy "add the tests", so the gate skips it.

Gate (git state and attribution helpers live in `_teamgate.py`): source changed in the teammate's
own linked worktree without a pairing test change. In a shared checkout the changes cannot be
attributed to this teammate, so the gate stays quiet instead of keeping a reviewer busy over a
peer's untested file.

Exit codes: 0 idle allowed, 2 keep working (reason on stderr).
"""
import os
import re
import sys

HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HOOKS_DIR)
import _hooklib as hooklib  # noqa: E402
import _teamgate as teamgate  # noqa: E402

try:
    from _vendored import is_vendored_ui  # components.json aliases.ui: CLI-owned shadcn/ui source
except Exception:  # helper absent or broken: degrade to every check running, never to silence
    def is_vendored_ui(file_path):
        return False

PLUGIN_ROOT = os.path.dirname(HOOKS_DIR)
EDIT_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}  # MultiEdit: releases that still ship it
READ_ONLY_BUILTINS = ("Explore", "Plan")
# Used only when agents/<role>.md cannot be read; the file's `tools:` line is the authority.
READ_ONLY_FALLBACK = (
    "architecture-advisor", "clean-architecture", "code-reviewer", "design-critique",
    "design-system-architect", "monorepo-architect", "requirements-consultant",
)
COVERAGE_EXTENSIONS = (".rb", ".py", ".ts", ".tsx", ".js", ".jsx")
# Changes with no unit to test: migrations, config, scripts, framework boilerplate, type stubs,
# stories. Terraform is not in COVERAGE_EXTENSIONS at all: *.tftest.hcl is optional per module.
NO_TEST_NEEDED = re.compile(
    r"(^|/)(db/migrate|migrations|alembic/versions|config|scripts|bin)/"
    r"|(^|/)(__init__|manage|settings|urls|apps|admin|asgi|wsgi|schema|seeds)\.(py|rb)$"
    r"|\.config\.[cm]?[jt]s$|\.d\.ts$|\.stories\.[jt]sx?$"
)


def resolve_role(data):
    """Bare agent type for this teammate: the team config member's `agentType` (the key the live
    config carries; `agent_type` kept as a fallback), the common agent_type, then the name itself."""
    name = str(data.get("teammate_name") or "")
    member = next((m for m in teamgate.team_members(data) if name and m.get("name") == name), {})
    for value in (member.get("agentType"), member.get("agent_type"), data.get("agent_type"), name):
        if value:
            return str(value).split(":")[-1]
    return ""


def declared_tools(role):
    """Tool names from agents/<role>.md frontmatter; None when the file or its tools: line is absent
    (an agent without a tools: line inherits every tool)."""
    if not re.fullmatch(r"[a-z0-9-]+", role or ""):
        return None
    text = hooklib.read_file(os.path.join(PLUGIN_ROOT, "agents", f"{role}.md"))
    parts = text.split("---", 2) if text.startswith("---") else []
    front = parts[1] if len(parts) == 3 else ""
    match = re.search(r"^tools:[ \t]*(.*)$((?:\n[ \t]*-[ \t]*\S+)*)", front, re.M)
    if not match:
        return None
    return set(re.findall(r"[A-Za-z_]\w*", match.group(1) + " " + match.group(2)))


def is_read_only(role):
    if role in READ_ONLY_BUILTINS:
        return True
    tools = declared_tools(role)
    if tools is None:
        return role in READ_ONLY_FALLBACK
    return not tools & EDIT_TOOLS


def has_matching_test(source, test_files):
    """users.py <-> test_users.py / users_test.py / users.test.ts; a Django app's models.py <->
    that app's tests.py."""
    stem = os.path.splitext(os.path.basename(source))[0]
    folder = os.path.dirname(source) + "/"
    for test in test_files:
        if stem in os.path.basename(test):
            return True
        if os.path.basename(test) == "tests.py" and folder.startswith(os.path.dirname(test) + "/"):
            return True
    return False


def vendored(repo, path):
    try:
        return bool(is_vendored_ui(os.path.join(repo["top"], path)))
    except Exception:
        return False


def gate_untested(repo):
    """Own worktree only: a source change with no pairing test change."""
    if not repo["linked"]:
        return []
    live = [path for xy, path in repo["entries"] if "D" not in xy]
    tests = [p for p in live if teamgate.is_test_file(p)]
    untested = [p for p in live if p.endswith(COVERAGE_EXTENSIONS) and not teamgate.is_test_file(p)
                and not NO_TEST_NEEDED.search(p) and not vendored(repo, p)
                and not has_matching_test(p, tests)]
    if not untested:
        return []
    shown = ", ".join(untested[:5]) + (f" (+{len(untested) - 5} more)" if len(untested) > 5 else "")
    return [f"Modified source files lack corresponding test changes: {shown}. "
            "Add or update tests per the `std-testing` skill before going idle."]


def main():
    data = hooklib.load_event()
    if not isinstance(data, dict) or not data:
        sys.exit(0)
    if is_read_only(resolve_role(data)):
        sys.exit(0)
    repo = teamgate.repo_state(str(data.get("cwd") or os.getcwd()))
    if repo is None:
        sys.exit(0)
    feedback = gate_untested(repo)
    if feedback:
        who = data.get("teammate_name") or "teammate"
        teamgate.block(data, "teammate-idle-checker",
                       [f"Quality gate feedback for {who}:"] + [f"  - {item}" for item in feedback])
    sys.exit(0)


if __name__ == "__main__":
    main()
