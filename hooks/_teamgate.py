#!/usr/bin/env python3
"""Lock-free git state, test-file detection, task attribution and the block cap for the team gates.

`task-completed-checker`, `teammate-idle-checker` and `team-task-validator` gate TaskCompleted and
TeammateIdle; `session-start-check` and `session-stop-summary` read the same porcelain through
`run_git`. Imported normally: these helpers used to live in task-completed-checker.py, which its
siblings loaded by path.

ATTRIBUTION (`touched_scope`): a gate rejects only over files the task touched — every change in a
linked worktree (one agent's checkout); None in a shared tree with several writers; otherwise the
changes since the TaskCreated baseline, or None without one. None keeps the file gates quiet rather
than reject over someone else's work in progress.

BLOCKING (`block`): exit 2 with the reason on stderr, which the hooks reference says is "fed back"
to the model or teammate (stdout on exit 2 reaches nobody). After GIVE_UP_AFTER identical
rejections in one session the gate stops and hands the gap to the developer as a systemMessage.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

import _hooklib as hooklib

SOURCE_EXTENSIONS = (".rb", ".py", ".ts", ".tsx", ".js", ".jsx", ".tf")
TEST_NAME_MARKERS = ("_test.", "_spec.", ".test.", ".spec.")
TEST_DIRS = ("__tests__", "tests", "test", "spec")
SNAPSHOT_CAP = 2000
GIVE_UP_AFTER = 3


def run_git(cwd, args, timeout=6):
    """(returncode, stdout) of a lock-free git call in `cwd`; (1, "") when git cannot run.
    --no-optional-locks stops `git status` rewriting .git/index (no index.lock race with a
    teammate's `git add`). Output is NOT stripped: porcelain's first column is data."""
    try:
        result = subprocess.run(
            ["git", "--no-optional-locks", "-C", cwd] + list(args),
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
        )
        return result.returncode, result.stdout
    except (subprocess.TimeoutExpired, OSError, ValueError):
        return 1, ""


def parse_status(raw):
    """`status --porcelain=v2 -z --branch` -> ({header: value}, [(XY, repo-root-relative path)])."""
    info, entries = {}, []
    fields = raw.split("\0")
    index = 0
    while index < len(fields):
        record = fields[index]
        index += 1
        kind = record[:2]
        if kind == "# ":
            key, _, value = record[2:].partition(" ")
            info[key] = value
        elif kind in ("1 ", "u "):
            entries.append((record[2:4], record.split(" ", 8 if kind == "1 " else 10)[-1]))
        elif kind == "2 ":
            entries.append((record[2:4], record.split(" ", 9)[-1]))
            index += 1  # a rename/copy carries its source path in the next NUL field
        elif kind == "? ":
            entries.append(("??", record[2:]))
    return info, entries


def repo_state(cwd):
    """Git facts for the event's directory (untracked files included), or None outside a work tree."""
    code, out = run_git(cwd, ["rev-parse", "--show-toplevel", "--absolute-git-dir", "--git-common-dir"], 3)
    lines = out.splitlines()
    if code != 0 or len(lines) < 3:
        return None
    common = os.path.abspath(os.path.join(cwd, lines[2]))
    code, raw = run_git(lines[0], ["status", "--porcelain=v2", "-z", "--branch", "--untracked-files=all"])
    if code != 0:
        return None
    info, entries = parse_status(raw)
    return {
        "top": lines[0],
        "common": common,
        "linked": os.path.normcase(os.path.abspath(lines[1])) != os.path.normcase(common),
        "head": info.get("branch.oid", ""),
        "entries": entries,
    }


def is_source_file(path):
    return os.path.splitext(path)[1] in SOURCE_EXTENSIONS


def is_test_file(path):
    """pytest test_*.py, Django tests.py, conftest.py, Terraform *.tftest.hcl, *_test / *_spec /
    *.test / *.spec names, and anything under a tests/, test/, spec/ or __tests__/ directory."""
    parts = hooklib.normalize(path).split("/")
    name = parts[-1]
    if name in ("tests.py", "conftest.py") or name.endswith(".tftest.hcl"):
        return True
    if name.startswith("test_") and name.endswith(".py"):
        return True
    return any(m in name for m in TEST_NAME_MARKERS) or any(p in TEST_DIRS for p in parts[:-1])


def team_members(data):
    """Members of THIS session's live team (~/.claude/teams/<team>/config.json), or [].

    The team name is the event's team_name (deprecated in the hooks reference) or `session-` + the
    first eight characters of the session id (agent-teams docs). Never 'the newest team on the
    machine': that leaks another project's team into this one."""
    session = str(data.get("session_id") or "")
    team = str(data.get("team_name") or (f"session-{session[:8]}" if session else ""))
    if not re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9._-]*", team):
        return []
    base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    try:
        with open(os.path.join(base, "teams", team, "config.json"), encoding="utf-8") as handle:
            members = json.load(handle).get("members", [])
    except (OSError, ValueError, AttributeError):
        return []
    return [m for m in members if isinstance(m, dict)] if isinstance(members, list) else []


def multi_writer(data):
    """Several agents may be editing this tree: a teammate event, or a live team of 2+ members."""
    return bool(data.get("teammate_name")) or len(team_members(data)) >= 2


def _state_path(*parts):
    root = os.environ.get("CLAUDE_PLUGIN_DATA") or os.path.join(tempfile.gettempdir(), "sdh-hook-notices")
    return os.path.join(root, *parts)


def baseline_path(repo, data):
    session, task = str(data.get("session_id") or ""), str(data.get("task_id") or "")
    if not (session and task):
        return None
    key = "\0".join((os.path.normcase(repo["common"]), session, task))
    return _state_path("task-baselines", hashlib.sha1(key.encode("utf-8")).hexdigest()[:24] + ".json")


def snapshot(repo):
    """{path: [XY, size, mtime_ns]} for each dirty entry: a signature of the tree, not a copy."""
    state = {}
    for xy, path in repo["entries"][:SNAPSHOT_CAP]:
        try:
            stat = os.stat(os.path.join(repo["top"], path))
            state[path] = [xy, stat.st_size, stat.st_mtime_ns]
        except OSError:
            state[path] = [xy, -1, -1]
    return state


def write_baseline(repo, data):
    target = baseline_path(repo, data)
    if not target or multi_writer(data):
        return  # a shared multi-writer tree is never attributed by baseline, so do not snapshot it
    try:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as handle:
            json.dump({"head": repo["head"], "entries": snapshot(repo)}, handle)
    except OSError:
        pass  # no baseline -> the file gates stay quiet for this task; a creation is never blocked


def load_baseline(repo, data):
    try:
        with open(baseline_path(repo, data), encoding="utf-8") as handle:
            baseline = json.load(handle)
    except (OSError, ValueError, TypeError):
        return None
    return baseline if isinstance(baseline, dict) else None


def touched_scope(repo, data):
    """Repo-root-relative paths this task changed in the working tree, or None when unknowable."""
    if repo["linked"]:
        return {path for _, path in repo["entries"]}
    if multi_writer(data):
        return None
    baseline = load_baseline(repo, data)
    if baseline is None:
        return None
    before = baseline.get("entries") or {}
    return {path for path, sig in snapshot(repo).items() if before.get(path) != sig}


def committed_paths(repo, data):
    """Paths committed as part of this work: a worktree branch since it forked from the main
    checkout's branch, or everything since the task baseline's HEAD."""
    if repo["linked"]:
        head = hooklib.read_file(os.path.join(repo["common"], "HEAD")).strip()
        ref = head[5:].strip() if head.startswith("ref: ") else ""
        target = f"{ref}...HEAD" if re.fullmatch(r"refs/heads/[\w./-]+", ref) else ""
    else:
        base = str((load_baseline(repo, data) or {}).get("head") or "")
        target = f"{base}..HEAD" if re.fullmatch(r"[0-9a-f]{7,64}", base) and base != repo["head"] else ""
    if not target:
        return set()
    code, out = run_git(repo["top"], ["diff", "--name-only", "-z", target], 4)
    return {p for p in out.split("\0") if p} if code == 0 else set()


def _bump(marker):
    try:
        with open(marker, encoding="utf-8") as handle:
            count = int(handle.read().strip() or 0) + 1
    except (OSError, ValueError):
        count = 1
    try:
        os.makedirs(os.path.dirname(marker), exist_ok=True)
        with open(marker, "w", encoding="utf-8") as handle:
            handle.write(str(count))
    except OSError:
        return 1  # an unwritable marker must not switch the gate off
    return count


def block(data, hook, lines):
    """Reject: reason on stderr, exit 2. After GIVE_UP_AFTER identical rejections in one session,
    stop the retry loop and hand the unresolved gap to the developer as a systemMessage."""
    text = "\n".join(lines)
    session = str(data.get("session_id") or "")
    if session:
        subject = str(data.get("task_id") or data.get("teammate_name") or "")
        key = "\0".join((session, hook, subject, text))
        count = _bump(_state_path("gate-blocks", hashlib.sha1(key.encode("utf-8")).hexdigest()[:24]))
        if count > GIVE_UP_AFTER:
            if count == GIVE_UP_AFTER + 1:
                print(json.dumps({"systemMessage": f"sdh {hook} stopped repeating the same rejection "
                                                   f"after {GIVE_UP_AFTER} attempts; resolve it by hand:\n{text}"}))
            sys.exit(0)
    print(text, file=sys.stderr)
    sys.exit(2)
