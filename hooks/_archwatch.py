#!/usr/bin/env python3
"""The asyncRewake watcher behind `_archhooks.watch`: which shell commands rewrite architecture files, which
paths they changed, and what is new once the index holds them.

    classify_command(command) -> 'install' | 'generator' | 'vcs' | None
    watch(event, budget) -> (exit code, stderr text)

A shell tool's `tool_input.command` (Bash, PowerShell, Monitor) is read with the house shell lexer, looking
through runner prefixes: `bundle exec`, `uv run`, `poetry run`, `pipenv run`, `pdm run`, `python -m <module>`
and `docker compose run|exec <service>`. So `uv run alembic revision --autogenerate`, `bundle exec rails g
model` and `./manage.py startapp` are generators. A file tool counts only for an in-scope path inside the
project root, and a root that is no project is never indexed.

When another writer holds the index lock (the session-start build, another watcher), the watcher waits up to
LOCK_WAIT_SECONDS and retries once. If the lock is still held it runs its detectors read-only against the
index as it stands (CM1 within the manifest when no index is readable yet), leaves the index dirty for the
holder, and records the paths as `pending`: the first baseline leaves findings on them out, so an install
made during the first build is never frozen as legacy. The next watcher that holds the lock re-checks the
pending paths, and clears them once a baseline exists. Community tools are skipped after a wait, which keeps
one watcher inside the 150 s hooks.json timeout.
"""
import json
import os
import time

import _archconfig
import _archhooks
import _archindex
import _archparse
import _archrefresh
import _archstate
import _archstore
import _archview
import _hooklib
import _hookpaths
import _shell

SHELL_TOOLS = ("Bash", "PowerShell", "Monitor")
LOCK_WAIT_SECONDS = 15.0
LOCK_POLL_SECONDS = 0.5
INSTALL_VERBS = {"npm": ("install", "i", "add"), "pnpm": ("add", "install", "i"), "yarn": ("add",), "bun": ("add", "install", "i"),
                 "bundle": ("add",), "uv": ("add",), "poetry": ("add",), "pip": ("install",), "pip3": ("install",)}
VCS_VERBS = ("checkout", "switch", "pull", "merge", "rebase")
GENERATED = ("model", "scaffold", "migration", "resource")
PYTHONS = ("python", "python3", "py")
RUNNERS = {"bundle": ("exec",), "uv": ("run",), "poetry": ("run",), "pipenv": ("run",), "pdm": ("run",)}
RUNNER_VALUE_OPTIONS = frozenset(("--with", "--with-editable", "--with-requirements", "--python", "-p", "--project",
                                  "--directory", "--env-file", "--extra", "--group", "--package", "--index", "--gemfile"))
COMPOSE_VALUE_OPTIONS = frozenset(("-f", "--file", "-p", "--project-name", "--profile", "--env-file", "-e", "--env", "-w",
                                   "--workdir", "-u", "--user", "-v", "--volume", "--name", "--entrypoint", "-l", "--label"))
WATCHED_KINDS = ("manifest", "migration", "model", "schema")


def classify_command(command):
    """'install' | 'generator' | 'vcs' | None for a shell command line."""
    for program in _shell.programs(_shell.executed_segments(command or "")):
        verb = _program_verb(*_unwrap(program.name, list(program.args)))
        if verb:
            return verb
    return None


def _skip_options(args, value_options):
    index = 0
    while index < len(args) and args[index].startswith("-"):
        index += 2 if args[index] in value_options else 1
    return args[index:]


def _runner_command(name, args):
    """The command a runner prefix runs (`uv run X` -> X), or None when `name args` is no runner."""
    if name in RUNNERS and args[:1] and args[0] in RUNNERS[name]:
        return _skip_options(args[1:], RUNNER_VALUE_OPTIONS)
    if name in PYTHONS and "-m" in args and all(a.startswith("-") for a in args[:args.index("-m")]):
        return args[args.index("-m") + 1:]
    if name == "docker-compose" or (name == "docker" and args[:1] == ["compose"]):
        rest = _skip_options(args[1:] if name == "docker" else args, COMPOSE_VALUE_OPTIONS)
        return _skip_options(rest[1:], COMPOSE_VALUE_OPTIONS)[1:] if rest[:1] in (["run"], ["exec"]) else None
    return None


def _unwrap(name, args):
    """(program, args) past runner prefixes, at most four deep (`uv run python -m pip install x`)."""
    for _ in range(4):
        rest = _runner_command(name, args)
        if not rest:
            break
        name, args = _shell.basename(rest[0]), rest[1:]
    return name, args


def _program_verb(name, args):
    words = [a for a in args if not a.startswith("-")]
    if name in PYTHONS and words[:1] and _shell.basename(words[0]) == "manage.py":
        name, words = "manage.py", words[1:]
    if name in INSTALL_VERBS and words[:1] and words[0] in INSTALL_VERBS[name] and (len(words) > 1 or name in ("bundle", "uv", "poetry")):
        return "install"
    if name == "rails" and words[:1] in (["g"], ["generate"]) and words[1:2] and words[1] in GENERATED:
        return "generator"
    if (name == "manage.py" and words[:1] in (["startapp"], ["makemigrations"])) or (name == "alembic" and words[:1] == ["revision"]):
        return "generator"
    if name == "git" and (words[:1] and words[0] in VCS_VERBS or words[:2] == ["stash", "pop"]):
        return "vcs"
    return None


def _trigger(event):
    """(command, verb, file_path): a shell command and its class ("" for a shell call carrying no command), or the
    path a file tool wrote (command None)."""
    if _hooklib.tool_name(event) in SHELL_TOOLS:
        command = _hooklib.tool_input(event).get("command")
        return (command, classify_command(command), None) if isinstance(command, str) else ("", None, None)
    return None, None, _hooklib.get_file_path(event)


def _changed_paths(root, verb, cwd):
    if verb == "vcs":
        return None
    import _teamgate
    code, raw = _teamgate.run_git(root, ["status", "--porcelain=v2", "-z", "--untracked-files=all"], 6)
    paths = [p for _, p in _teamgate.parse_status(raw)[1] if _archparse.classify(p)] if code == 0 else []
    package = _hookpaths.project_root(os.path.join(cwd or root, "__probe__"))
    for name in ("Gemfile", "package.json", "pyproject.toml"):
        rel = _archindex.rel_path(root, os.path.join(package, name)) if package else None
        if rel and os.path.isfile(os.path.join(root, rel)) and verb == "install":
            paths.append(rel)
    return sorted(set(paths)) if code == 0 or paths else None


def _target_paths(root, event, verb, file_path):
    """Paths to index: the written file ([] when it lies outside the root), the files a shell command changed, or
    None for a tree-rewriting git command (a full pass)."""
    if file_path:
        rel = _archindex.rel_path(root, file_path)
        return [rel] if rel else []
    return _changed_paths(root, verb, event.get("cwd"))


def _watch_findings(root, paths):
    """WATCH_DETECTORS on changed manifests, models and migrations, read-only against the index as it stands.
    With no readable index yet, only CM1 within the manifest runs."""
    try:
        store = _archstore.open_store(root)
    except _archstore.StoreError:
        store = None
    try:
        view = _archview.IndexView(store, root, _archconfig.load(root)[0])
        detectors = _archhooks.WATCH_DETECTORS if store is not None else ("CM1",)
        deltas = [_archhooks.build_delta(view, root, rel) for rel in paths if _archparse.classify(rel) in WATCHED_KINDS]
        return [f for delta in deltas if delta for f in _archhooks._findings(view, delta, detectors, None)[0]]
    finally:
        if store is not None:
            store.close()


def _tool_findings(root, paths):
    """New violations from installed community tools; only with SDH_ORTHOGONALITY_TOOLS=1 (off by default)."""
    if os.environ.get("SDH_ORTHOGONALITY_TOOLS", "0").strip() != "1":
        return []
    import _archtools
    rows = [r for r in _archtools.detect(root) if r["found"] and r["status"] == "skipped"]
    results = _archtools.run(root, rows, {"changed": paths})
    store = _archstore.open_store(root, write=True)
    try:
        findings = _archtools.new_violations(store, results)
        _archtools.mark_seen(store, results)
        return findings
    finally:
        store.close()


def _after_lock(root, directory, options):
    """Wait (bounded) for another writer's lock to go, then retry the refresh once."""
    deadline = time.monotonic() + LOCK_WAIT_SECONDS
    while _archstate.lock_held(directory) and time.monotonic() < deadline:
        time.sleep(LOCK_POLL_SECONDS)
    return _archrefresh.refresh(root, options)


def _baselined(root):
    """True once the baseline covers every detector the watcher runs."""
    try:
        store = _archstore.open_store(root)
    except _archstore.StoreError:
        return False
    if store is None:
        return False
    try:
        return set(_archhooks.WATCH_DETECTORS) <= set(json.loads(store.get_meta("baseline_detectors", "[]") or "[]"))
    finally:
        store.close()


def _with_pending(root, directory, own):
    """`own` plus the paths earlier watchers could not index; pending clears once a baseline covers the watcher."""
    earlier = _archstate.pending(directory)
    if earlier and _baselined(root):
        _archstate.clear_pending(directory)
    return sorted(set(own) | set(earlier))


def _refresh_and_detect(root, paths, command, budget):
    """Index `paths` (waiting once when another writer holds the lock), then the findings for this event."""
    directory, options = _archstore.index_dir(root), {"paths": paths, "budget": budget}
    stats = _archrefresh.refresh(root, options)
    waited = bool(stats.get("locked"))
    stats = _after_lock(root, directory, options) if waited else stats
    own = list(paths or []) if command is not None else []
    if stats.get("locked"):
        _archstate.add_pending(directory, paths or [])
        scope = own
    else:
        scope = _with_pending(root, directory, own)
    findings = _watch_findings(root, scope) if scope else []
    return findings + ([] if waited else _tool_findings(root, paths or []))


def watch(event, budget=_archindex.DEFAULT_BUDGET):
    """(exit code, stderr text) for the asyncRewake watcher; a crash is recorded in the status table and exits 0."""
    root = None
    try:
        if _archhooks.disabled():
            return 0, ""
        command, verb, file_path = _trigger(event)
        skip = (not verb) if command is not None else not _archhooks.in_scope(file_path)
        if skip:
            return 0, ""
        root = _archindex.resolve_root(event.get("cwd"), file_path)
        paths = _target_paths(root, event, verb, file_path) if root else []
        if not _archindex.indexable_root(root) or (file_path and not paths):
            return 0, ""
        findings = _refresh_and_detect(root, paths, command, budget)
        trigger = "`%s`" % command.strip()[:80] if command is not None else "editing %s" % (paths or ["a file"])[0]
        return _archhooks.wake(findings, event, trigger)
    except Exception as exc:
        if root:
            _archhooks.record_status(root, "watch", exc)
        return 0, ""
