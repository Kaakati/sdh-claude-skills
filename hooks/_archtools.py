#!/usr/bin/env python3
"""Community architecture tools, run only when the project already has them. Nothing here installs
or fetches anything: a tool resolves to an executable inside the project (`bin/`, `node_modules/.bin`,
`.venv`) or, for the standalone binaries, on PATH. The launchers that can download a package that
is not installed are never used; `NEVER_INVOKE` documents them and no argv is built from them.

    detect(root, with_db=False) -> [tool rows]   found / absent / needs-db, why, argv, install hint
    run(root, rows, options) -> [results]        serialized, per-tool budget, TOTAL_BUDGET per pass
    new_violations(store, results) / mark_seen(store, results)

Tools that boot the app or need a database (database_consistency, active_record_doctor, Django
checks, alembic check) run only with `with_db`. A tool's own baseline is respected: packwerk and
pks through `package_todo.yml`; the others through the index's `tool_seen` fingerprints.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import time

import _archrules
import _archstore
import _hooktools

NEVER_INVOKE = ("npx", "pnpm dlx", "yarn dlx", "bunx", "uvx", "uv run", "pipx run")
TOTAL_BUDGET = 120.0
PRUNE = frozenset((".git", "node_modules", ".venv", "venv", "vendor", "dist", "build", "tmp", "log", "coverage", "__pycache__"))
SPECS = (
    ("packwerk", ("packwerk.yml",), ("bin",), ("check",), 60, False, "bundle add packwerk --group development && bundle exec packwerk init"),
    ("pks", ("packwerk.yml",), ("path",), ("check",), 60, False, "install the pks release binary"),
    ("import-linter", (".importlinter", "setup.cfg", "pyproject.toml"), ("venv",), (), 60, False, "uv add --dev import-linter"),
    ("tach", ("tach.toml",), ("venv",), ("check",), 30, False, "uv add --dev tach"),
    ("dependency-cruiser", (".dependency-cruiser.js", ".dependency-cruiser.cjs", ".dependency-cruiser.mjs",
                            ".dependency-cruiser.json"), ("node",), ("--output-type", "json", "src"), 60, False,
     "npm install --save-dev dependency-cruiser"),
    ("jscpd", (".jscpd.json",), ("node", "path"), ("--reporters", "consoleFull", "."), 30, False, "npm install --save-dev jscpd"),
    ("squawk", (), ("node", "path"), (), 10, False, "npm install --save-dev squawk-cli"),
    ("database_consistency", ("Gemfile.lock",), ("bundle",), (), 120, True, "bundle add database_consistency --group development"),
    ("active_record_doctor", ("Gemfile.lock",), ("bundle",), (), 120, True, "bundle add active_record_doctor --group development"),
    ("django-check", ("manage.py",), ("venv-python",), ("manage.py", "check", "--fail-level", "WARNING"), 120, True, "a project .venv with Django"),
    ("alembic-check", ("alembic.ini",), ("venv",), ("check",), 120, True, "uv add alembic"),
)
BINARIES = {"import-linter": "lint-imports", "dependency-cruiser": "depcruise", "alembic-check": "alembic"}
CONFIG_MARKERS = {"setup.cfg": "[importlinter]", "pyproject.toml": "[tool.importlinter]",
                  "Gemfile.lock": None}
PACKWERK_LOCATION = re.compile(r"^(\S+?\.rb):(\d+):\d+$")
PACKWERK_MESSAGE = re.compile(r"^(\w+) violation: (\S+) belongs to '([^']+)'", re.I)
LOCATION = re.compile(r"^(?:\S+\s)?(\S+?\.\w{1,4})[:\[]L?(\d+)")


def _subdirs(base):
    try:
        return sorted(e.path for e in os.scandir(base) if e.is_dir() and e.name not in PRUNE and not e.name.startswith("."))
    except OSError:
        return []


def _candidate_dirs(root):
    """The root, its child directories and their children: where a tool's config would sit."""
    children = _subdirs(root)
    return [root] + children + [grandchild for child in children for grandchild in _subdirs(child)]


def _config_in(directory, spec):
    name, configs = spec[0], spec[1]
    for config in configs:
        path = os.path.join(directory, config)
        marker = CONFIG_MARKERS.get(config)
        if not os.path.isfile(path):
            continue
        text = _read(path) if marker or name in ("database_consistency", "active_record_doctor") else ""
        gem = name if name in ("database_consistency", "active_record_doctor") else None
        if (marker is None or marker in text) and (gem is None or re.search(r"^\s+%s \(" % re.escape(gem), text, re.M)):
            return path
    return None


def _read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return ""


def _resolve(spec, directory):
    name, sources = spec[0], spec[2]
    binary = BINARIES.get(name, name.split("-")[0] if name.endswith("-check") else name)
    for source in sources:
        if source == "path":
            found = shutil.which(binary)
            resolved = ([found], directory) if found else None
        elif source == "bundle":
            bundle = shutil.which("bundle")
            resolved = ([bundle, "exec"] + (["rake", name] if name == "active_record_doctor" else [name]), directory) if bundle else None
        elif source == "venv-python":
            python = _hooktools.venv_bin("python", directory)
            resolved = ([python], directory) if python else None
        else:
            resolved = _hooktools.resolve_local(binary, directory, (source,))
        if resolved:
            return resolved
    return None


def _row(spec, directory, root, with_db):
    name, _, sources, args, budget, needs_db, hint = spec
    config = _config_in(directory, spec) if spec[1] else None
    if spec[1] and not config:
        return None
    resolved = _resolve(spec, directory)
    status = "absent" if not resolved else ("needs-db" if needs_db and not with_db else "skipped")
    why = "not installed in this project" if not resolved else ("connects to a database; pass --with-db" if needs_db and not with_db else "found")
    return {"name": name, "found": bool(resolved), "status": status, "why": why, "budget": budget,
            "directory": os.path.relpath(directory, root).replace("\\", "/"), "config": config and os.path.relpath(config, root).replace("\\", "/"),
            "argv": (resolved[0] + list(args)) if resolved else [], "cwd": resolved[1] if resolved else directory,
            "not_run_install_hint": hint}


def detect(root, with_db=False):
    """The detection matrix: one row per tool config found (squawk: per project root)."""
    rows = []
    for directory in _candidate_dirs(root):
        for spec in SPECS:
            row = _row(spec, directory, root, with_db) if spec[1] else None
            if row:
                rows.append(row)
    squawk = _resolve(SPECS[6], root)
    rows.append({"name": "squawk", "found": bool(squawk), "status": "skipped" if squawk else "absent", "why": "runs on changed .sql migrations",
                 "budget": 10, "directory": ".", "config": None, "argv": squawk[0] if squawk else [], "cwd": root,
                 "not_run_install_hint": SPECS[6][6]})
    if any(r["name"] == "packwerk" and r["found"] for r in rows):
        for row in (r for r in rows if r["name"] == "pks" and r["found"]):
            row.update(status="skipped", why="packwerk is installed; pks is never run beside it (two boundary tools)", found=False)
    return rows


def _todo_pairs(text):
    """(constant, file) pairs recorded in one packwerk package_todo.yml."""
    pairs, constant = set(), None
    for line in text.splitlines():
        key = re.match(r"^\s+[\"']?(::?[\w:]+)[\"']?:\s*$", line)
        item = re.match(r"^\s+-\s+(\S+\.rb)\s*$", line)
        constant = key.group(1).lstrip(":") if key else constant
        if item and constant:
            pairs.add((constant, item.group(1)))
    return pairs


def _todo(directory):
    pairs = set()
    for base, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in PRUNE]
        if "package_todo.yml" in files:
            pairs |= _todo_pairs(_read(os.path.join(base, "package_todo.yml")))
    return pairs


def parse_output(name, text, cwd):
    """[{rule, path, line, symbol, message}] from a tool's output."""
    if name == "dependency-cruiser":
        try:
            data = json.loads(text[text.find("{"):])
            return [{"rule": v["rule"]["name"], "path": v["from"], "line": 0, "symbol": v["to"], "message": v["rule"]["name"]}
                    for v in data.get("summary", {}).get("violations", [])]
        except (ValueError, KeyError, TypeError):
            return []
    lines, found = text.splitlines(), []
    for index, line in enumerate(lines):
        location = PACKWERK_LOCATION.match(line.strip()) if name in ("packwerk", "pks") else LOCATION.match(line.strip())
        message = PACKWERK_MESSAGE.match(lines[index + 1].strip()) if location and name in ("packwerk", "pks") and index + 1 < len(lines) else None
        if location and (message or name not in ("packwerk", "pks")):
            found.append({"rule": message.group(1).lower() if message else name, "path": location.group(1), "line": int(location.group(2)),
                          "symbol": message.group(2).lstrip(":") if message else "", "message": (lines[index + 1] if message else line).strip()[:200]})
    if name in ("packwerk", "pks"):
        todo = _todo(cwd)
        found = [v for v in found if (v["symbol"], v["path"]) not in todo]
    return found


def fingerprint(tool, violation):
    return hashlib.sha1(("%s|%s|%s|%s" % (tool, violation["rule"], violation["path"], violation["symbol"])).encode("utf-8")).hexdigest()


def _invoke(row, extra, timeout):
    argv = row["argv"] + list(extra)
    if _hooktools.unsafe_for_cmd(argv[0], " ".join(argv[1:])):
        return {"status": "error", "exit_code": None, "output": "refused: a cmd.exe shim cannot take these arguments safely"}
    try:
        done = subprocess.run(argv, cwd=row["cwd"], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              timeout=max(1.0, timeout), universal_newlines=True, encoding="utf-8", errors="replace")
        return {"status": "ran", "exit_code": done.returncode, "output": done.stdout or ""}
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "exit_code": None, "output": ""}
    except OSError as exc:
        return {"status": "error", "exit_code": None, "output": "%s: %s" % (type(exc).__name__, exc)}


def run(root, rows, options=None):
    """Run the found, runnable rows in order within the total budget. options: changed (paths), budget."""
    options = options or {}
    deadline = time.monotonic() + float(options.get("budget") or TOTAL_BUDGET)
    results = []
    for row in rows:
        result = dict(row, seconds=0.0, violations=[], exit_code=None, new_violations=0)
        extra = [p for p in options.get("changed") or [] if p.endswith(".sql")] if row["name"] == "squawk" else []
        if row["status"] != "skipped" or not row["found"] or (row["name"] == "squawk" and not extra) or time.monotonic() > deadline:
            result["status"] = row["status"] if row["status"] != "skipped" or not row["found"] else "skipped"
            results.append(result)
            continue
        started = time.monotonic()
        outcome = _invoke(row, extra, min(row["budget"], deadline - time.monotonic()))
        result.update(status=outcome["status"], exit_code=outcome["exit_code"], seconds=round(time.monotonic() - started, 2),
                      violations=parse_output(row["name"], outcome["output"], row["cwd"]), output_excerpt=outcome["output"][-400:])
        results.append(result)
    return results


def new_violations(store, results):
    """Findings (id TOOL) for violations whose fingerprints are not in the seen-set."""
    seen = {r["fingerprint"] for r in store.select("tool_seen")} if store is not None else set()
    findings = []
    for result in results:
        for violation in result.get("violations") or []:
            key = fingerprint(result["name"], violation)
            result["new_violations"] = result.get("new_violations", 0) + (key not in seen)
            if key not in seen:
                text = "%s reports %s at %s:%d: %s" % (result["name"], violation["rule"], violation["path"], violation["line"], violation["message"])
                finding = _archrules.make("TOOL", {"path": violation["path"], "line": violation["line"], "symbol": violation["symbol"]},
                                          text, confidence="high", key=(key, ""))
                finding.update(source=result["name"], fingerprint=key)
                findings.append(finding)
    return findings


def mark_seen(store, results):
    now = _archstore.now_iso()
    rows = [{"fingerprint": fingerprint(r["name"], v), "tool": r["name"], "first_seen": now}
            for r in results for v in r.get("violations") or []]
    store.begin()
    store.insert_many("tool_seen", rows)
    store.commit()
    return len(rows)
