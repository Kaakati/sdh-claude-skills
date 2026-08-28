#!/usr/bin/env python3
"""Shared helpers for Claude Code hooks.

Centralizes event parsing, file reading, path normalization, and the run loops
for advisory checkers (PostToolUse) and gates (PreToolUse) so individual hooks
stay small and behave consistently across platforms.

Contract:
  * Advisory checker  -> `check(event) -> list[str]`  (warning lines; never blocks)
  * PreToolUse gate    -> `check(event) -> None`        (calls deny()/ask() to block)

Run a checker standalone with `run_post_checker(check)`; run a gate with
`run_pre_blocker(check, fail_closed=...)`. Both always exit 0 — blocking is
communicated to Claude Code via the permissionDecision JSON, not the exit code.
"""

import json
import os
import sys


def load_event(stream=None):
    """Parse the hook JSON event from stdin.

    Returns {} on any parse error. A malformed or empty event must not crash a
    hook (fail-open at the parse boundary); gates add their own fail-closed
    policy around the check logic via run_pre_blocker.
    """
    if stream is None:
        stream = sys.stdin
    try:
        return json.load(stream)
    except (json.JSONDecodeError, EOFError, ValueError):
        return {}


def tool_name(event):
    return event.get("tool_name", "") or ""


def tool_input(event):
    return event.get("tool_input", {}) or {}


def get_file_path(event):
    return tool_input(event).get("file_path", "") or ""


def get_content(event):
    """The content being written (Write -> content, Edit -> new_string)."""
    data = tool_input(event)
    return data.get("content", "") or data.get("new_string", "") or ""


def normalize(path):
    """Normalize Windows backslashes to forward slashes for path matching."""
    return (path or "").replace("\\", "/")


def read_file(path):
    """Read a file as UTF-8, replacing undecodable bytes. Returns "" on error."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except (OSError, IOError):
        return ""


def emit(warnings, event_name="PostToolUse"):
    """Deliver advisory warnings to the MODEL, not to a log nobody reads.

    This used to be a bare `print(line)`, and that is where every advisory checker's output went
    to die. The hook contract is explicit: *"For most events, stdout is written to the debug log
    but not shown in the transcript. The exceptions are `UserPromptSubmit`,
    `UserPromptExpansion`, and `SessionStart`, where stdout is added as context."* PostToolUse is
    not one of the exceptions — so 14 checkers computed a correct warning, printed it, and threw
    it away. Nobody was reading them: not the model, not the developer.

    The supported way to reach the model from PostToolUse is `hookSpecificOutput.additionalContext`,
    which the harness wraps as a system reminder next to the tool result that triggered it. This
    repo already knew that — `vague-request-detector.py` has used the same contract all along —
    the advisory path just never adopted it.

    Why this matters beyond a bug: a plugin **cannot** ship `.claude/rules/`, so the path-scoped
    auto-injection the `rules/` → `std-*` skills conversion gave up is unrecoverable via skills
    (`paths:` only *limits* eligibility; the model still chooses). Hooks are the one component a
    plugin ships that fires deterministically on every matching edit. This function is therefore
    the plugin's only mechanism for getting a rule to the model automatically — which is exactly
    Ch. 7's placement test arriving as an implementation detail: what must hold whether or not it
    is read is a hook.
    """
    if isinstance(warnings, str):
        warnings = [warnings]
    lines = [l for l in (warnings or []) if l]
    if not lines:
        return
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": event_name,
            "additionalContext": "\n".join(lines),
        }
    }))


def hook_error(label, exc):
    """Build the fail-open failure notice. Returns the line; the caller emits it.

    "Silent failure is invisible failure. A fail-open hook that swallows its own
    exceptions looks identical to one that passed" — so a dead gate can masquerade
    as a green one for months. Advisory hooks fail OPEN (a crash must never block
    the edit) but never SILENTLY: one actionable line naming the checker.

    This function used to `print()` that line, which — on PostToolUse — sent it to the debug log.
    A helper whose entire argument is *"silent failure is invisible failure"* was itself silent:
    a crashed checker announced its death into a void, which is the exact masquerade it exists to
    prevent.

    It RETURNS rather than emits because the dispatcher calls it inside a loop and emits once at
    the end. Emitting here would put a second JSON object on stdout and corrupt the hook's reply,
    which would turn a reporting bug into a broken hook.
    """
    return (
        f"HOOK ERROR: {label} failed to run — {type(exc).__name__}: {exc}. "
        "Its checks did NOT execute, so its rules were not enforced on this edit."
    )


def _script_label():
    """Best-effort name of the running hook, for hook_error."""
    try:
        return os.path.basename(sys.argv[0]) or "checker"
    except Exception:
        return "checker"


# Ch. 13, "It's configurable at the edges": hard-coding a team's branch names,
# test command, or protected paths makes the plugin unusable anywhere else. The
# core rules are universal; the specifics are parameters with sane defaults, so a
# repo we did not design works on day one.
DEFAULT_PROTECTED_BRANCHES = ("main", "master", "develop")


def env_list(name, default):
    """Read a comma-separated env override, falling back to `default`.

    An unset OR blank value yields the default — an empty override almost always
    means "this env var is not set here", not "protect no branches", and the
    silently-unprotected reading is the dangerous one.
    """
    values = [v.strip() for v in os.environ.get(name, "").split(",") if v.strip()]
    return values or list(default)


def protected_branches():
    """Branches a direct push / force push must be gated on.

    Override with SDH_PROTECTED_BRANCHES (e.g. "trunk,release"). Default:
    main, master, develop.
    """
    return env_list("SDH_PROTECTED_BRANCHES", DEFAULT_PROTECTED_BRANCHES)


def branch_alternation(extra=()):
    """Regex alternation of the protected branches, safely escaped."""
    import re as _re

    names = list(protected_branches()) + [e for e in extra if e not in protected_branches()]
    return "|".join(_re.escape(n) for n in names)


def _notice_dir():
    import tempfile

    return os.path.join(tempfile.gettempdir(), "sdh-hook-notices")


def seen_this_session(event, key):
    """True if `key` has already been raised this session; marks it seen otherwise.

    The non-emitting half of `notice_once`, for checkers that RETURN their lines to a dispatcher
    that emits once. Calling `notice_once` from inside a dispatched checker would print a second
    JSON object and corrupt the hook's reply.

    Why a checker would want this at all: `test-runner` said "Related test files found… consider
    running tests" on *every* edit of a file that has tests, while `test-coverage-checker` says
    "no test file found" on every edit of one that does not. Between them, **every source edit
    produced a message** — and now that these reach the model rather than a debug log, a 100%
    injection rate is the Ch. 5 attention problem in its purest form. A nudge is useful once and
    wallpaper by the fifth time.

    Fails toward speaking: if the marker cannot be written, return False (not seen) rather than
    silently suppressing. A repeated notice is visible and fixable; a swallowed one is neither.
    """
    session = str((event or {}).get("session_id") or "nosession")
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in f"{session}-{key}")
    try:
        os.makedirs(_notice_dir(), exist_ok=True)
        marker = os.path.join(_notice_dir(), safe)
        if os.path.exists(marker):
            return True
        with open(marker, "w", encoding="utf-8") as fh:
            fh.write("1")
        return False
    except OSError:
        return False


def notice_once(event, key, message):
    """Print `message` at most once per session, then stay quiet. Returns True if printed.

    Ch. 13: a hook whose tool is missing "should say so once and exit 0, not crash
    on every write". Both other options are wrong: crashing punishes the user for
    not having our toolchain, and exiting silently is Ch. 9's "silent failure is
    invisible failure" — the user watches formatting never happen and has no idea
    why. Once per session is the whole point: the notice is actionable the first
    time and pure noise by the fifth.

    If the marker cannot be written (read-only or missing temp dir), we speak
    rather than stay silent — a repeated notice is visible and fixable; a silent
    hole is neither. Deliberate, not a default.

    The delivery bug this docstring used to embody: it called bare `print()`, and its only caller
    (`auto-format.py`) is a **PostToolUse** hook — where stdout goes to the debug log, not to the
    model and not to the transcript. So a function whose whole argument is *"silent failure is
    invisible failure"* was itself silent, and the "rubocop is not installed" notice reached
    nobody. It now routes through `emit()`, i.e. `hookSpecificOutput.additionalContext`.
    """
    session = str((event or {}).get("session_id") or "nosession")
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in f"{session}-{key}")
    try:
        os.makedirs(_notice_dir(), exist_ok=True)
        marker = os.path.join(_notice_dir(), safe)
        if os.path.exists(marker):
            return False
        with open(marker, "w", encoding="utf-8") as fh:
            fh.write("1")
    except Exception:
        pass
    emit(message)
    return True


def run_post_checker(check):
    """Standalone runner for an advisory PostToolUse checker.

    `check(event)` returns a list of warning lines. Always exits 0 — a crash in an
    advisory checker must never block the tool (fail-open) — but the crash is
    reported rather than swallowed, so a dead checker cannot look like a passing one.
    """
    event = load_event()
    try:
        warnings = check(event) or []
    except Exception as exc:
        warnings = [hook_error(_script_label(), exc)]
    emit(warnings)
    sys.exit(0)


def _decision(decision, reason, event_name="PreToolUse"):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": event_name,
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }))


def deny(reason, event_name="PreToolUse"):
    """Emit a PreToolUse 'deny' decision."""
    _decision("deny", reason, event_name)


def ask(reason, event_name="PreToolUse"):
    """Emit a PreToolUse 'ask' (confirm) decision."""
    _decision("ask", reason, event_name)


def run_pre_blocker(check, fail_closed=False, gate_label="check"):
    """Runner for a PreToolUse gate.

    `check(event)` inspects the event and calls deny()/ask() to block, then
    returns. On an unexpected exception inside check():
      * fail_closed=True  -> emit a deny so a security gate never silently passes
      * fail_closed=False -> allow (advisory gates degrade open)
    Always exits 0; the decision travels via the permissionDecision JSON.
    """
    event = load_event()
    try:
        check(event)
    except Exception as exc:
        if fail_closed:
            deny(
                f"BLOCKED: the {gate_label} hook errored and is failing closed "
                f"({type(exc).__name__}). This action was not evaluated for safety. "
                "Fix the hook or run the action manually outside Claude Code."
            )
    sys.exit(0)


# ---------------------------------------------------------------------------
# Framework detection — wrapper-directory-agnostic.
#
# Conventions auto-load from each framework's own layout and marker files, NOT
# from a forced top-level folder name. Rails code works under backend/, api/, or
# the repo root; a Vite app under web/, frontend/, or root; a Next app under
# next/, web/, or root; React Native under mobile/, app/, or root; a Python
# service (FastAPI or Django) under svc/, api/, ml/, or root.
#
#   under(path, "app/models")      -> matches the canonical layout anywhere
#                                     (backend/app/models, api/app/models, app/models)
#   replace_first_segment(...)     -> map source->test path, preserving the wrapper
#   detect_framework(path)         -> 'rails'|'nextjs'|'vite'|'react-native'
#                                     |'django'|'fastapi'|None
#                                     via on-disk markers, with a path-structure fallback
# ---------------------------------------------------------------------------

def under(path, subpath):
    """True if `subpath` (canonical framework-internal dir, e.g. 'app/models')
    appears as consecutive directory segments anywhere in `path`, regardless of
    the wrapper directory. Pure string work — no disk access, works for files
    that do not exist yet."""
    norm = normalize(path).strip("/")
    needle = subpath.strip("/")
    return ("/" + needle + "/") in ("/" + norm + "/")


def under_any(path, subpaths):
    """True if `under(path, s)` holds for any s in `subpaths`."""
    return any(under(path, s) for s in subpaths)


def replace_first_segment(path, old_seg, new_seg):
    """Replace the first path segment equal to `old_seg` with `new_seg`,
    preserving the wrapper prefix and the rest of the path. Wrapper-agnostic
    source->test mapping: 'api/app/models/u.rb' + (app, spec) ->
    'api/spec/models/u.rb'. Returns the normalized path unchanged if `old_seg`
    is not a segment."""
    norm = normalize(path)
    old_seg = old_seg.strip("/")
    new_seg = new_seg.strip("/")
    parts = norm.split("/")
    for i, part in enumerate(parts):
        if part == old_seg:
            parts[i] = new_seg
            return "/".join(parts)
    return norm


_NEXT_CONFIGS = ("next.config.js", "next.config.mjs", "next.config.ts", "next.config.cjs")
_VITE_CONFIGS = ("vite.config.js", "vite.config.ts", "vite.config.mjs", "vite.config.cjs")
_RN_CONFIGS = ("metro.config.js", "metro.config.cjs", "app.json")
_RAILS_MARKERS = ("Gemfile", os.path.join("config", "application.rb"), os.path.join("bin", "rails"))


def _ancestors(start_dir):
    current = os.path.abspath(start_dir)
    while True:
        yield current
        parent = os.path.dirname(current)
        if parent == current:
            return
        current = parent


def _deepest_existing_dir(file_path):
    """Deepest existing directory at or above file_path (the file itself may not
    exist yet, e.g. a Write of a new file)."""
    base = os.path.dirname(os.path.abspath(file_path)) or os.path.abspath(".")
    for d in _ancestors(base):
        if os.path.isdir(d):
            return d
    return None


def _has(directory, rel):
    return os.path.exists(os.path.join(directory, rel))


def _package_json(directory):
    try:
        with open(os.path.join(directory, "package.json"), "r", encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except (OSError, IOError):
        return ""


def _pyproject(directory):
    """pyproject.toml content, lowercased for dependency grepping ("" if unreadable).

    Lowercased because dependency tables write both `django` and `Django`; the
    grep is for a dependency NAME, and pip/uv names are case-insensitive."""
    try:
        with open(os.path.join(directory, "pyproject.toml"), "r", encoding="utf-8", errors="replace") as handle:
            return handle.read().lower()
    except (OSError, IOError):
        return ""


def _pyproject_dep(pyp, name):
    """True when `name` appears as a DEPENDENCY in lowercased pyproject content —
    a quoted PEP 621 requirement ("django>=5.0", "fastapi[standard]") or a Poetry
    table key (django = "^5.0"). A plain substring grep matched prose and comments
    ("# not a django project") and misclassified plain libraries; anchoring to the
    two dependency spellings is the pyproject analog of package.json's '"next"'."""
    import re as _re

    return bool(
        _re.search(r"[\"']" + name + r"[\"'\[><=~!;@ ]", pyp)
        or _re.search(r"^\s*" + name + r"\s*=", pyp, _re.M)
    )


def detect_framework(file_path):
    """Best-effort framework for an edited file, independent of the wrapper
    directory name. Returns 'rails' | 'nextjs' | 'vite' | 'react-native' |
    'django' | 'fastapi' | None.

    Walks up from the file to the nearest framework marker (next.config /
    vite.config / metro.config / app.json / package.json deps / Gemfile /
    manage.py / pyproject.toml deps / alembic.ini), and falls back to canonical
    path structure when no marker is resolvable on disk (e.g. relative path
    outside the project, or a bare scaffold)."""
    norm = normalize(file_path)
    start = _deepest_existing_dir(file_path)
    if start:
        for d in _ancestors(start):
            if any(_has(d, c) for c in _NEXT_CONFIGS):
                return "nextjs"
            if any(_has(d, c) for c in _VITE_CONFIGS):
                return "vite"
            if _has(d, "metro.config.js") or _has(d, "metro.config.cjs"):
                return "react-native"
            pkg = _package_json(d)
            if pkg:
                if '"next"' in pkg:
                    return "nextjs"
                if '"react-native"' in pkg:
                    return "react-native"
                if '"vite"' in pkg:
                    return "vite"
            if _has(d, "app.json") and ("expo" in _package_json(d) or under(norm, "src")):
                # app.json is a weak RN/Expo signal; only trust with corroboration
                if '"react-native"' in pkg or '"expo"' in pkg:
                    return "react-native"
            if any(_has(d, m) for m in _RAILS_MARKERS):
                return "rails"
            # Python markers come after Rails within a dir: Rails is the primary
            # backend, so on the (unlikely) mixed root, Rails wins the tie.
            if _has(d, "manage.py"):
                # Django's canonical marker (a legacy Flask-Script manage.py
                # would also match — Flask is off-stack).
                return "django"
            pyp = _pyproject(d)
            if pyp:
                # Dependency-anchored grep (see _pyproject_dep). fastapi first:
                # a FastAPI service never DEPENDS on django; the reverse mention
                # (a Django repo's "migrate to fastapi" comment) does not count,
                # because only dependency spellings match.
                if _pyproject_dep(pyp, "fastapi"):
                    return "fastapi"
                if _pyproject_dep(pyp, "django"):
                    return "django"
            if _has(d, "alembic.ini") and _has(d, os.path.join("app", "main.py")):
                return "fastapi"  # house FastAPI layout: app/main.py + alembic
            if _has(d, ".git"):
                break  # do not walk above the repository root

    # Path-structure fallback (no markers, or path not resolvable on disk).
    if norm.endswith(".rb") and under_any(norm, ("app", "lib", "db", "config", "spec")):
        return "rails"
    if under_any(norm, ("src/screens", "src/navigation")):
        return "react-native"
    if under(norm, "src/pages"):
        return "vite"
    # The .py branch must run BEFORE the src/app Next.js rule: `src/app/` is also
    # the Python src-layout for a package named `app`, and the Next rule has no
    # extension guard — python files would be shadowed into 'nextjs'.
    if norm.endswith(".py"):
        # Django-idiomatic filenames and its migrations dirs (alembic's default
        # is alembic/versions; a Flask-Migrate-style migrations/ dir would also
        # land here, but Flask is off-stack).
        if norm.endswith("/manage.py") or norm == "manage.py" or under(norm, "migrations"):
            return "django"
        # House FastAPI package shape (std-fastapi): routers/schemas under app/.
        if under_any(norm, ("app/routers", "app/api", "app/schemas")) or norm.endswith("/app/main.py"):
            return "fastapi"
        return None
    if under(norm, "src/app") or (under(norm, "app") and (norm.endswith(".tsx") or norm.endswith(".jsx"))):
        return "nextjs"
    return None


def is_react_native(file_path):
    return detect_framework(file_path) == "react-native"


def is_web_react(file_path):
    """A browser React file (Vite SPA or Next.js) — distinct from React Native."""
    return detect_framework(file_path) in ("vite", "nextjs")
