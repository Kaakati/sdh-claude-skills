#!/usr/bin/env python3
"""Shared helpers for Claude Code hooks.

Centralizes event parsing, file reading, notices, output and the run loops for advisory checkers
(PostToolUse) and gates (PreToolUse), so individual hooks stay small and behave consistently
across platforms. Two responsibilities live in their own modules and are re-exported here, so
every hook keeps calling `hooklib.<name>` with unchanged signatures:

  * `_hookpaths.py` — project-relative matching (`under`, `rel_to_root`, `project_root`,
    `replace_first_segment`, `normalize`) and framework detection (`detect_framework`)
  * `_hookaudit.py` — the audit trail (`redact`, `audit_dir`, `append_audit`)

Contract:
  * Advisory checker  -> `check(event) -> list[str]`  (warning lines; never blocks)
  * PreToolUse gate    -> `check(event) -> None`        (calls deny()/ask() to block)

Run a checker standalone with `run_post_checker(check)`; run a gate with
`run_pre_blocker(check, fail_closed=...)`. Both always exit 0 — blocking is
communicated to Claude Code via the permissionDecision JSON, not the exit code.
A fail-closed gate that cannot even START (no Python, a broken import) is the launcher's
job: `run-python.sh --fail-closed` turns that into exit 2.
"""

import hashlib
import io
import json
import os
import re
import sys

from _hookaudit import (  # noqa: F401  re-exported: hooks call these as hooklib.<name>
    _REDACTIONS, _append_line, _ensure_audit_dir, _main_checkout, append_audit, audit_dir, redact,
)
from _hookpaths import (  # noqa: F401  re-exported: hooks call these as hooklib.<name>
    _BACKEND_EXTENSIONS, _NEXT_CONFIGS, _PACKAGE_MARKERS, _RAILS_APP_MARKERS, _RAILS_MARKERS,
    _RN_CONFIGS, _VITE_CONFIGS, _ancestors, _backend_label, _deepest_existing_dir, _fold, _has,
    _js_label, _label_for_dir, _package_json, _package_root, _pyproject, _pyproject_dep, _read_text,
    _session_root, _structure_label, detect_framework, is_react_native, is_web_react, normalize,
    project_root, rel_to_root, replace_first_segment, set_current_event, under, under_any,
)

# The event the running hook parsed. Path scoping reads its `cwd`, and gate decisions read its
# tool and target for the audit trail, without threading the event through every caller.
_CURRENT_EVENT = {}


def _read_stream(stream):
    """(text, error) from `stream` (default stdin). Never raises."""
    try:
        return (stream if stream is not None else sys.stdin).read(), None
    except (OSError, ValueError, AttributeError) as exc:
        return "", f"stdin could not be read ({type(exc).__name__})"


def _parse(raw, read_error=None):
    """(value, error): the decoded JSON, or {} and why it is not an event."""
    if read_error:
        return {}, read_error
    if not raw.strip():
        return {}, "empty event on stdin"
    try:
        return json.loads(raw), None
    except ValueError as exc:
        return {}, f"unparseable event on stdin ({type(exc).__name__}: {exc})"


def _remember(event):
    """Keep the parsed event current here and in `_hookpaths`, where the `cwd` fallbacks read it."""
    global _CURRENT_EVENT
    _CURRENT_EVENT = event if isinstance(event, dict) else {}
    set_current_event(_CURRENT_EVENT)
    _safe_stdio()


def _safe_stdio():
    """Never let a character the console codepage cannot encode crash a hook.

    The launcher exports PYTHONUTF8=1, so in production stdout is already UTF-8. Run directly
    (the harness, the documented dev loop) on a cp932 console, a plain print of an em dash raised
    UnicodeEncodeError and the hook exited 1. The encoding stays what the reader decodes with —
    the harness reads with the same locale — and only unencodable characters are replaced.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            if (stream.encoding or "").lower().replace("-", "") != "utf8":
                stream.reconfigure(errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


def load_event(stream=None):
    """Parse the hook JSON event from stdin.

    Returns {} on any parse error. A malformed or empty event must not crash a
    hook (fail-open at the parse boundary); gates add their own fail-closed
    policy around the check logic via run_pre_blocker. To tell an empty or
    unparseable event from a real one, use `load_event_strict`.
    """
    value, _error = _parse(*_read_stream(stream))
    _remember(value)
    return value


def load_event_strict(stream=None):
    """(event, error) — `error` is None only for a well-formed event object.

    `load_event` folds "no event", "garbage" and "a JSON list" into `{}`, which a checker reads as
    "nothing to check" and a gate as "nothing to deny". Right for fail-open code; wrong for the
    callers that must refuse or report what they could not evaluate. A truncated event used to be
    ALLOWED by the fail-closed gates, and an empty one looked exactly like a clean edit to the
    dispatcher.
    """
    value, error = _parse(*_read_stream(stream))
    if error is None and not isinstance(value, dict):
        value, error = {}, f"event is a JSON {type(value).__name__}, not an object"
    if error is None and not isinstance(value.get("tool_input", {}), dict):
        error = "tool_input is not a JSON object"
    _remember(value)
    return value, error


def tool_name(event):
    return (event.get("tool_name", "") or "") if isinstance(event, dict) else ""


def tool_input(event):
    data = event.get("tool_input", {}) if isinstance(event, dict) else {}
    return data if isinstance(data, dict) else {}


# The tools that run a shell command from `tool_input.command`. hooks.json registers every shell gate
# on "Bash|PowerShell|Monitor". The hooks reference: "Match `Bash|PowerShell` in hooks that inspect
# shell commands ... On Windows without Git Bash, the tool is enabled automatically and Claude Code
# doesn't register the Bash tool at all. A hook that matches only `Bash` never fires there." Monitor
# runs a watch command in the background under "the same permission rules as Bash" (tools reference).
SHELL_TOOLS = ("Bash", "PowerShell", "Monitor")


def is_shell_tool(event):
    """True for a Bash, PowerShell or Monitor call."""
    return tool_name(event) in SHELL_TOOLS


def shell_command(event):
    """The command a shell tool runs; "" for any other tool, and for a Monitor WebSocket watch (it
    sends `ws` "in place of `command`"). A non-string command is returned as is, so a fail-closed gate
    errors on it and denies rather than reading it as an empty command."""
    command = tool_input(event).get("command") if is_shell_tool(event) else None
    return "" if command is None else command


def shell_dialect(event):
    """"powershell" for the PowerShell tool; "bash" for Bash and Monitor (the `_shell` lexer dialects)."""
    return "powershell" if tool_name(event) == "PowerShell" else "bash"


# The MCP tools that write a file: hooks.json registers security-scan and mcp-install-gate on this
# string verbatim, and both scripts test tool names against it (the registration test compares all
# three). A matcher holding regex characters is "JavaScript regular expression, unanchored" in the
# hooks reference, so it is anchored with ^ and $ and lists whole tool names: the verb-prefix
# pattern it replaced, `mcp__.*__(write|edit|create|move).*`, put Gmail `create_draft`, Calendar
# `create_event` and memory `create_entities` in front of a fail-closed gate. The server segment
# stays open, since tools are named `mcp__<server>__<tool>` and a plugin-bundled server's
# `mcp__plugin_<plugin>_<server>__<tool>`. The names are the reference filesystem server's four
# writers, the GitHub server's `create_or_update_file` (a repository file sent as `path` and
# `content`) and its `push_files`, which commits many files at once: `files`, "Array of file objects to
# push, each object with path (string) and content (string)" (github-mcp-server README), read by
# `get_file_entries`. `create_file` is out on purpose: the claude.ai Google Drive connector's
# `create_file` takes a title and no path.
MCP_FILE_WRITE_MATCHER = (r"^mcp__[^_].*__(write_file|edit_file|create_directory|move_file|create_or_update_file"
                          r"|push_files)$")
MCP_FILE_WRITE_TOOL = re.compile(MCP_FILE_WRITE_MATCHER)


def is_mcp_file_write(name):
    """True for an MCP tool the PreToolUse file gates are registered for (MCP_FILE_WRITE_MATCHER)."""
    return isinstance(name, str) and bool(MCP_FILE_WRITE_TOOL.search(name))


def get_file_path(event):
    """The file a writing tool targets.

    Write/Edit (and MultiEdit, on releases that still ship it) send `file_path`, NotebookEdit sends
    `notebook_path`, and MCP filesystem writers send `path`, or `destination` for a move or copy.
    `path` and `destination` count only for `mcp__*` tools: Grep and Glob take a `path` too, and a
    directory being searched is not an edit target.
    """
    data = tool_input(event)
    found = data.get("file_path") or data.get("notebook_path")
    if not found and tool_name(event).startswith("mcp__"):
        found = data.get("path") or data.get("destination")
    return found if isinstance(found, str) else ""


_CONTENT_KEYS = ("content", "new_string", "new_source")


def get_content(event):
    """Every piece of text the tool is about to write, joined.

    Write -> content, Edit -> new_string, NotebookEdit -> new_source, plus each `edits[]` entry
    (MultiEdit's new_string, the MCP filesystem editor's newText) and each `files[]` entry an MCP
    call commits (`get_file_entries`). Reading only the first key scanned a one-key tool fine and a
    notebook cell or a multi-edit not at all.
    """
    data = tool_input(event)
    parts = [data.get(key) for key in _CONTENT_KEYS]
    edits = data.get("edits")
    for edit in edits if isinstance(edits, list) else []:
        if isinstance(edit, dict):
            parts.extend((edit.get("new_string"), edit.get("newText")))
    parts.extend(content for _path, content in get_file_entries(event))
    return "\n".join(p for p in parts if isinstance(p, str) and p)


def get_file_entries(event):
    """(path, content) for each file an MCP call writes as a list: the GitHub server's `push_files`
    sends `files`, each "with path (string) and content (string)". [] for every other tool — a single
    target is `get_file_path`'s. A non-string content reads as ""."""
    files = tool_input(event).get("files") if tool_name(event).startswith("mcp__") else None
    entries = [entry for entry in files if isinstance(entry, dict)] if isinstance(files, list) else []
    return [(entry["path"], entry.get("content") if isinstance(entry.get("content"), str) else "")
            for entry in entries if isinstance(entry.get("path"), str)]


def match_path(path):
    """`normalize(path)`, lowercased where the filesystem itself folds case.

    For a comparison that must follow the filesystem the hook runs on: NTFS and default APFS treat
    `.ENV` and `.env` as one file, ext4 does not. Compare lowercase patterns against this.

    security-scan does NOT use it, on purpose: its protected names (`.env`, `secrets/`, key files)
    are semantic, and it folds case on every OS. A repository travels between NTFS, APFS and ext4
    checkouts, so a `.ENV` or `Secrets/db.yml` write gets the same decision on every machine rather
    than a deny on a laptop and an allow in Linux CI; its code-suffix exemption keeps a
    `Private/Route.tsx` component allowed everywhere.
    """
    norm = normalize(path)
    return norm.lower() if _folds_case(path) else norm


def _folds_case(path):
    if os.name == "nt":
        return True
    probe = _deepest_existing_dir(path) or ""
    swapped = probe.swapcase()
    if swapped == probe:
        return sys.platform == "darwin"  # nothing to test with; APFS defaults to folding
    try:
        return os.path.exists(swapped) and os.path.samefile(probe, swapped)
    except OSError:
        return False


def read_file(path):
    """Read a file as UTF-8, replacing undecodable bytes. Returns "" on error.

    An empty read of a file that is not empty on disk is retried once: a formatter rewriting in
    place truncates before it writes, and a checker landing in that window saw "" and passed
    every rule without a word.
    """
    text = _read_text(path)
    try:
        if not text and os.path.getsize(path) > 0:
            text = _read_text(path)
    except OSError:
        pass
    return text


EMIT_MAX_LINES = 20
EMIT_MAX_CHARS = 4000


def emit(warnings, event_name="PostToolUse", system_message=None):
    """Deliver advisory warnings to the MODEL, not to a log nobody reads.

    The hook contract: *"For most events, stdout is written to the debug log but not shown in the
    transcript. The exceptions are `UserPromptSubmit`, `UserPromptExpansion`, and `SessionStart`."*
    A bare `print(line)` from PostToolUse therefore reached nobody; `additionalContext` is the
    supported channel, wrapped as a system reminder next to the tool result. Hooks are the one
    component a plugin ships that fires deterministically on every matching edit, so this is the
    plugin's only way to get a rule to the model automatically.

    PostToolUse volume is capped (`_cap`): one legacy module put 402 lines / 32K chars into context
    on every edit. HOOK ERROR lines are never dropped. `system_message` also shows a line to the
    USER; `event_name=None` sends only that (for events with no context channel).
    """
    lines = [line for line in ([warnings] if isinstance(warnings, str) else warnings or []) if line]
    if event_name == "PostToolUse":
        lines = _cap(lines)
    payload = {}
    if lines and event_name:
        payload["hookSpecificOutput"] = {"hookEventName": event_name,
                                         "additionalContext": "\n".join(lines)}
    if system_message:
        payload["systemMessage"] = system_message
    if payload:
        print(json.dumps(payload))


def _max_lines():
    """EMIT_MAX_LINES, overridable with SDH_HOOK_MAX_WARNINGS (0 = no cap, for a full report)."""
    try:
        return int(os.environ.get("SDH_HOOK_MAX_WARNINGS", EMIT_MAX_LINES))
    except ValueError:
        return EMIT_MAX_LINES


def _cap(lines):
    """Every HOOK ERROR line, the first warnings that fit, and a count of the rest."""
    limit = _max_lines()
    if limit <= 0:
        return lines
    kept, dropped, budget = [], 0, EMIT_MAX_CHARS
    for line in lines:
        is_error = str(line).startswith("HOOK ERROR")
        if is_error or (limit > 0 and budget >= len(line)):
            kept.append(line)
            limit -= 0 if is_error else 1
            budget -= len(line)
        else:
            dropped += 1
    if dropped:
        kept.append(f"+{dropped} more warning(s) not shown. Fix the ones above first, or run the "
                    "checker standalone with SDH_HOOK_MAX_WARNINGS=0 for the full list.")
    return kept


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
    names = list(protected_branches()) + [e for e in extra if e not in protected_branches()]
    return "|".join(re.escape(n) for n in names)


def _notice_dir():
    import tempfile

    return os.path.join(tempfile.gettempdir(), "sdh-hook-notices")


def first_in_session(event, key):
    """True exactly once per (session_id, key); False on every later call in that session.

    The one marker implementation behind `notice_once` and `seen_this_session`. Use it directly
    from a checker that RETURNS its lines to the dispatcher (which emits once): calling
    `notice_once` from inside a dispatched checker would print a second JSON object and corrupt
    the hook's reply.

    Fails toward speaking: if the marker cannot be written (read-only or missing temp dir), it
    returns True — every time. A repeated notice is visible and fixable; a swallowed one is
    neither. Deliberate, not a default.
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
        return True
    return True


def seen_this_session(event, key):
    """True if `key` has already been raised this session; marks it seen otherwise.

    The inverse spelling of `first_in_session`, and it fails the same way: toward speaking (an
    unwritable marker reads as "not seen").

    Why a checker would want this at all: `test-runner` said "Related test files found… consider
    running tests" on *every* edit of a file that has tests, while `test-coverage-checker` says
    "no test file found" on every edit of one that does not. Between them, **every source edit
    produced a message** — and now that these reach the model rather than a debug log, a 100%
    injection rate is the Ch. 5 attention problem in its purest form. A nudge is useful once and
    wallpaper by the fifth time.
    """
    return not first_in_session(event, key)


def notice_once(event, key, message):
    """Print `message` at most once per session, then stay quiet. Returns True if printed.

    Ch. 13: a hook whose tool is missing "should say so once and exit 0, not crash
    on every write". Both other options are wrong: crashing punishes the user for
    not having our toolchain, and exiting silently is Ch. 9's "silent failure is
    invisible failure" — the user watches formatting never happen and has no idea
    why. Once per session is the whole point: the notice is actionable the first
    time and pure noise by the fifth. The marker policy lives in `first_in_session`.

    The delivery bug this docstring used to embody: it called bare `print()`, and its only caller
    (`auto-format.py`) is a **PostToolUse** hook — where stdout goes to the debug log, not to the
    model and not to the transcript. It now routes through `emit()`.
    """
    if not first_in_session(event, key):
        return False
    emit(message)
    return True


def formatter_marker(event):
    """Marker file auto-format holds while it rewrites this edit's file; None for a fixture.

    Matching PostToolUse hooks run in PARALLEL, so the dispatcher's checkers could read a file in
    a formatter's truncate-then-write window, see "", and pass every rule. auto-format writes
    "running" then "done" here and the dispatcher waits (bounded) for "done". Keyed by
    `tool_use_id`, the value both hooks receive for one call: the hooks reference's PostToolUse
    input carries `"tool_use_id": "toolu_01ABC123..."`, and "The `tool_name`, `tool_input`, and
    `tool_use_id` fields are event-specific". The session|path fallback covers an event without it.
    A hand-built fixture has no `hook_event_name`, is paired with no formatter, and must not make
    the dispatcher wait.
    """
    if not isinstance(event, dict) or not event.get("hook_event_name"):
        return None
    key = event.get("tool_use_id") or f"{event.get('session_id', '')}|{get_file_path(event)}"
    digest = hashlib.sha1(str(key).encode("utf-8")).hexdigest()[:20]
    return os.path.join(_notice_dir(), f"formatting-{digest}")


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


# ---------------------------------------------------------------------------
# Gate decisions — every deny/ask is also appended to the audit trail (`_hookaudit.py`).
# ---------------------------------------------------------------------------

def _audit_decision(decision, reason):
    """Record a gate's deny/ask. Returns a gap notice, or None.

    PostToolUse never fires for a call a hook denied, so without this the audit trail held no
    denial at all. Only a real event (it carries `hook_event_name`) is recorded: a hand-built
    fixture is a test, and tests must not write audit trails into whatever directory they run in.
    """
    event = _CURRENT_EVENT
    if not event.get("hook_event_name"):
        return None
    error = append_audit(event, {
        "event": event.get("hook_event_name"), "tool": tool_name(event),
        "tool_use_id": event.get("tool_use_id"), "outcome": decision,
        "target": get_file_path(event), "reason": redact(reason)[:300],
    })
    if not error:
        return None
    return (f"HOOK ERROR: this {decision} was not recorded in the audit trail — {error}. "
            "The audit trail now has a gap.")


def _decision(decision, reason, event_name="PreToolUse"):
    payload = {
        "hookSpecificOutput": {
            "hookEventName": event_name,
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }
    gap = _audit_decision(decision, reason)
    if gap:
        payload["systemMessage"] = gap
    print(json.dumps(payload))


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
    A fail-closed gate also denies an event it cannot parse: `load_event` turned truncated stdin
    into {}, check() found nothing to deny, and the write went through. Empty stdin carries no
    action to evaluate and is left to check(). Always exits 0; the decision travels as JSON.
    """
    raw, _read_error = _read_stream(None)
    event, error = load_event_strict(io.StringIO(raw))
    if fail_closed and error and raw.strip():
        deny(f"BLOCKED: the {gate_label} hook could not read this event ({error}), so the action "
             "was not evaluated. Retry it; if this repeats, run the action manually outside "
             "Claude Code and update the sdh plugin.")
        sys.exit(0)
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
