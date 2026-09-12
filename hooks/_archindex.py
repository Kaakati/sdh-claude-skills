#!/usr/bin/env python3
"""Build and refresh the orthogonality index for one project root, incrementally.

Scope: `git ls-files -z --cached --others --exclude-standard` (os.walk without git, pruning build,
vendor, site-packages, AppData/Library and dot directories other than `.claude`), filtered to
`_archparse.classify` kinds, minus the house build-artifact globs and config `ignore`. Caps: MAX_FILES
in-scope files and MAX_BYTES per file; past either cap schema, manifests, models, migrations and config
are kept first and `coverage.truncated` is set. `indexable_root` refuses a root that is no project (the
home directory, a filesystem root, a folder with no .git or package manifest), so a session started there
walks nothing.

Change detection per file: (size, mtime_ns) against the `files` row; when the size matches but the
mtime moved, or the mtime is within RACY_SECONDS of the refresh start, sha1 decides (the racy-
timestamp rule, which also makes a seeded worktree re-parse only files whose content differs).
A changed file's facts are replaced in the same transaction. Context declarations are recomputed
only when a declaring file or the set of Rails model namespaces changes; refs are re-resolved for
changed files, files with unresolved refs when files were added, and files pointing at deleted files.

Concurrency: writers take `refresh.lock` (`_archstate`); a writer that cannot sets `dirty` and
returns, and the holder runs one more pass. `budget` seconds bound a pass: past it the work so far
is committed with meta `complete = 0`.
"""
import hashlib
import json
import os
import posixpath
import time

import _archconfig
import _archcontexts
import _archdup
import _archparse
import _archstate
import _archstore
import _hookpaths
import _teamgate

MAX_FILES = 50000
MAX_BYTES = 1024 * 1024
RACY_SECONDS = 2.0
BATCH = 250
DEFAULT_BUDGET = 120.0
PRUNE_DIRS = frozenset((".git", "node_modules", ".venv", "venv", "__pycache__", ".next", "dist", "build", "coverage",
                        "vendor", ".tox", ".mypy_cache", ".ruff_cache", ".pytest_cache", ".turbo", ".cache",
                        "site-packages", "dist-packages", "AppData", "Library"))
EXCLUDE_GLOBS = ("**/dist/**", "**/build/**", "**/.next/**", "**/coverage/**", "**/*.generated.*", "**/*.min.js",
                 "**/*.min.css", "**/vendor/**", "**/public/assets/**", "**/public/packs/**", "**/tmp/cache/**",
                 "**/node_modules/**", "**/.venv/**", "**/venv/**", "**/__pycache__/**")
PRIORITY_KINDS = ("manifest", "schema", "model", "config", "migration", "alembic")
DEPLOYABLE_MARKERS = ("Gemfile", "package.json", "pyproject.toml", "manage.py")
CONTEXT_FILES = frozenset(("packwerk.yml", "package.yml", ".importlinter", "setup.cfg", "pyproject.toml", "tach.toml",
                           "project.json", "apps.py", "orthogonality.json"))
_PROBES = {"rubygems": "__probe__.rb", "npm": "__probe__.tsx", "pypi": "__probe__.py"}


def _inside(path, root):
    return os.path.normcase(os.path.abspath(path)).startswith(os.path.normcase(os.path.abspath(root)).rstrip("\\/") + os.sep)


def _git_ancestor(start):
    for directory in _hookpaths._ancestors(start):
        if os.path.exists(os.path.join(directory, ".git")):
            return directory
    return None


def resolve_root(cwd=None, file_path=None):
    """The project root: nearest ancestor holding .git, else the nearest package root, else the start."""
    file_dir = _hookpaths._deepest_existing_dir(file_path) if file_path else None
    starts = [s for s in (cwd, file_dir) if s and os.path.isdir(s)]
    for finder in (_git_ancestor, lambda s: _hookpaths.project_root(os.path.join(s, "__probe__"))):
        for start in starts:
            found = finder(start)
            if found and (not file_path or _inside(file_path, found)):
                return os.path.abspath(found)
    return os.path.abspath(starts[0]) if starts else None


def indexable_root(root):
    """False where the hooks build no index: no root, the home directory, a filesystem root, or a folder holding
    no .git, package manifest or `.claude/orthogonality.json` at its top level (a session outside a project)."""
    if not root:
        return False
    real = os.path.normcase(os.path.realpath(root))
    if real == os.path.normcase(os.path.realpath(os.path.expanduser("~"))) or os.path.dirname(real) == real:
        return False
    return any(os.path.exists(os.path.join(root, name)) for name in (".git", _archconfig.CONFIG_REL) + DEPLOYABLE_MARKERS)


def rel_path(root, path):
    try:
        rel = os.path.relpath(os.path.abspath(path), root).replace("\\", "/")
    except ValueError:
        return None
    return None if rel == "." or rel.startswith("../") or rel == ".." else rel


def excluded(rel, config):
    return _archconfig.matches(rel, EXCLUDE_GLOBS) or _archconfig.matches(rel, (config or {}).get("ignore") or ())


def _walk(root):
    rels = []
    for directory, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in PRUNE_DIRS and (d == ".claude" or not d.startswith("."))]
        base = os.path.relpath(directory, root).replace("\\", "/")
        rels.extend((name if base == "." else base + "/" + name) for name in files)
    return rels


def enumerate_files(root, config):
    """(in-scope project-relative paths, coverage dict)."""
    code, out = _teamgate.run_git(root, ["ls-files", "-z", "--cached", "--others", "--exclude-standard"], 60)
    listed = [p for p in out.split("\0") if p] if code == 0 and out else _walk(root)
    rels = sorted({r for r in listed if _archparse.classify(r) and not excluded(r, config)})
    coverage = {"files_in_scope": len(rels), "truncated": False, "enumerated_by": "git" if code == 0 and out else "walk"}
    if len(rels) > MAX_FILES:
        first = [r for r in rels if _archparse.classify(r) in PRIORITY_KINDS]
        rest = [r for r in rels if _archparse.classify(r) not in PRIORITY_KINDS]
        rels, coverage["truncated"] = first + rest[:max(0, MAX_FILES - len(first))], True
    return rels, coverage


def deployable_dirs(rels):
    dirs = {posixpath.dirname(r) or "." for r in rels if posixpath.basename(r) in DEPLOYABLE_MARKERS}
    return sorted(dirs | {"."}, key=lambda d: (-len(d) if d != "." else 1))


def deployable_of(rel, dirs):
    for directory in dirs:
        if directory != "." and rel.startswith(directory + "/"):
            return directory
    return "."


def ecosystem_of(rel):
    base, ext = posixpath.basename(rel), posixpath.splitext(rel)[1]
    if rel.endswith("config/importmap.rb") or base in ("package.json", "pnpm-workspace.yaml") or ext in (".ts", ".tsx", ".js", ".jsx"):
        return "npm"
    if base == "Gemfile" or ext in (".rb", ".rake"):
        return "rubygems"
    if base == "pyproject.toml" or ext == ".py" or base.startswith("requirements"):
        return "pypi"
    return None


def framework_for(root, deployable, ecosystem, cache):
    key = (deployable, ecosystem)
    if key not in cache:
        base = root if deployable == "." else os.path.join(root, deployable)
        cache[key] = _hookpaths.detect_framework(os.path.join(base, _PROBES.get(ecosystem, "__probe__")))
    return cache[key]


def _read_bytes(path):
    try:
        with open(path, "rb") as handle:
            return handle.read()
    except OSError:
        return b""


def _needs_parse(row, stat, started, abs_path):
    """(parse?, sha1 when it had to be computed)."""
    if row is None or row["size"] != stat.st_size:
        return True, None
    if row["mtime_ns"] == stat.st_mtime_ns and stat.st_mtime < started - RACY_SECONDS:
        return False, None
    digest = hashlib.sha1(_read_bytes(abs_path)).hexdigest()
    return digest != row["sha1"], digest


def _scan_changes(root, rels, existing, started):
    changed, touched, missing = [], [], []
    for rel in rels:
        try:
            stat = os.stat(os.path.join(root, rel))
        except OSError:
            missing.append(rel)
            continue
        parse, digest = _needs_parse(existing.get(rel), stat, started, os.path.join(root, rel))
        if parse:
            changed.append((rel, stat))
        elif digest:
            touched.append((existing[rel]["id"], stat))
    return changed, touched, missing


def _row_sets(file_id, facts, place):
    base = {"file_id": file_id}
    dep, ctx = place["deployable"], place["context"]
    return {
        "models": [dict(base, symbol=m["symbol"], norm=_archdup.normalize_name(m["symbol"])[0], tbl=m.get("table"), context=ctx, deployable=dep, line=m["line"],
                        abstract=int(bool(m.get("abstract"))), sti_parent=m.get("sti_parent"),
                        proxy=int(bool(m.get("proxy"))), framework=m.get("framework")) for m in facts["models"]],
        "consts": [dict(base, symbol=c["symbol"], line=c["line"]) for c in facts["consts"]],
        "refs": [dict(base, line=r["line"], symbol=r["symbol"], scope=r.get("scope") or "", lang=r["lang"],
                      type_only=int(bool(r.get("type_only"))), src_context=ctx, dst_path=None, dst_context=None) for r in facts["refs"]],
        "writes": [dict(base, line=w["line"], symbol=w.get("symbol"), op=w.get("op"), tbl=w.get("table")) for w in facts["writes"]],
        "factories": [dict(base, line=f["line"], kind=f["kind"], target=f.get("target") or "", deployable=dep) for f in facts["factories"]],
        "handlers": [dict(base, line=h["line"], kind=h["kind"], exception=h.get("exception") or "", deployable=dep) for h in facts["handlers"]],
        "pagination": [dict(base, line=p["line"], style=p["style"], deployable=dep) for p in facts["pagination"]],
        "deps": [dict(base, line=d["line"], ecosystem=d["ecosystem"], package=d["package"], grp=d["group"], deployable=dep) for d in facts["deps"]],
        "variants": [dict(base, line=v["line"], kind=v["kind"], variant=v["variant"], deployable=dep) for v in facts["variants"]],
        "jsonb": [dict(base, line=j["line"], field=j["field"], key=j["key"], confidence=j["confidence"]) for j in facts["jsonb"]],
        "markers": [dict(base, line=m["line"], detector=m["detector"], reason=m["reason"]) for m in facts["markers"]],
        "tf": [dict(base, line=t["line"], block=t["block"], type=t.get("type"), name=t.get("name"), source=t.get("source"),
                    version=t.get("version")) for t in facts["tf"]],
        "txns": [dict(base, line=t["line"], end_line=t["end_line"]) for t in facts["txns"]],
    }


def write_facts(store, file_id, facts, place):
    """Insert one file's facts; `place` carries its deployable and context."""
    for table in facts["tables"]:
        extra = {"indexes": table.get("indexes") or [], "composite_fks": table.get("composite_fks") or [],
                 "concept": table.get("concept"), "relations": table.get("relations") or []}
        norm, near = _archdup.normalize_name(table.get("concept") or table["name"])
        table_id = store.insert("tables", {
            "file_id": file_id, "name": table["name"], "norm": norm, "near": near,
            "context": place["context"], "deployable": place["deployable"], "line": table["line"], "origin": table["origin"],
            "kind": table["kind"], "read_model": int(bool(table.get("read_model"))), "extra": json.dumps(extra)})
        store.insert_many("columns", [{"table_id": table_id, "file_id": file_id, "name": c["name"], "family": c.get("family"),
                                       "fk_table": c.get("fk_table"), "nullable": None if c.get("nullable") is None else int(c["nullable"]),
                                       "op": c.get("op") or "add", "line": c.get("line")} for c in table["columns"]])
    for name, rows in _row_sets(file_id, facts, place).items():
        store.insert_many(name, rows)


def _file_row(rel, stat, digest, env):
    deployable = deployable_of(rel, env["deployables"])
    ecosystem = ecosystem_of(rel)
    context = _archcontexts.context_for(env["cmap"], rel, deployable)[0]
    return {"path": rel, "kind": _archparse.classify(rel), "lang": _archparse.language(rel) or ecosystem,
            "framework": framework_for(env["root"], deployable, ecosystem, env["frameworks"]), "deployable": deployable,
            "context": context, "size": stat.st_size, "mtime_ns": stat.st_mtime_ns, "sha1": digest, "parsed_at": time.time()}


def _index_one(store, change, env, existing):
    rel, stat = change
    kind = _archparse.classify(rel)
    data = b"" if stat.st_size > MAX_BYTES and kind not in PRIORITY_KINDS else _read_bytes(os.path.join(env["root"], rel))
    row = _file_row(rel, stat, hashlib.sha1(data).hexdigest(), env)
    facts = _archparse.parse_text(rel, data.decode("utf-8", "replace")) if data else _archparse.empty_facts()
    if facts.get("workspace_root"):
        row["lang"] = "workspace"
    if rel in existing:
        file_id = existing[rel]["id"]
        store.update("files", row, {"id": file_id})
    else:
        file_id = store.insert("files", row)
    write_facts(store, file_id, facts, {"deployable": row["deployable"], "context": row["context"]})
    env["skipped_large"] += int(not data and stat.st_size > MAX_BYTES)
    return file_id


def _delete_facts(store, file_ids):
    if file_ids:
        for table in _archstore.FACT_TABLES:
            store.delete(table, {"file_id": list(file_ids)})


def _config_hash(root, rels):
    parts = ["rails-namespaces:" + ",".join(_archcontexts.rails_namespaces(rels))]
    for rel in sorted(r for r in rels if posixpath.basename(r) in CONTEXT_FILES):
        try:
            stat = os.stat(os.path.join(root, rel))
            parts.append("%s:%d:%d" % (rel, stat.st_size, stat.st_mtime_ns))
        except OSError:
            continue
    return hashlib.sha1("\n".join(parts).encode("utf-8")).hexdigest()


def _context_env(store, root, all_rels, config):
    digest = _config_hash(root, set(all_rels) | {_archconfig.CONFIG_REL})
    stored = store.get_meta("context_decl")
    changed = digest != store.get_meta("config_hash") or stored is None
    decl = _archcontexts.tool_declarations(root, all_rels) if changed else json.loads(stored)
    if changed:
        store.set_meta("context_decl", json.dumps(decl))
        store.set_meta("config_hash", digest)
    return _archcontexts.with_config(decl, config), changed
