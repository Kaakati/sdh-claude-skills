#!/usr/bin/env python3
"""The orthogonality index refresh entry point: take the writer lock, run incremental passes, and
record meta and coverage. Used by the SessionStart index hook, the watcher, and `arch_index.py`.

    refresh(root, {"cache_dir", "budget", "rebuild", "paths"}) -> stats
    file_facts(root, rel, text=None, hints=None) -> facts   (the checker parses the edited file only)
    seed_worktree(root, cache_dir=None) -> bool             (copy the main checkout's index once)

A timed-out pass keeps every file it finished: each file's old facts are deleted immediately before
its new facts are written, so a file the pass never reached keeps its previous facts and row. Only a
finished pass stamps the schema version, so a pass that was killed resumes from the files it committed
(and re-resolves every reference) instead of starting over. Facts are dropped only on --rebuild or for
an index another parser generation stamped, and only by a full pass: a pass limited to a few paths that
meets such an index marks it dirty, and the full pass that follows drops and rebuilds it. A full pass
that finishes clears the failures the checker's note reports.
"""
import os
import shutil
import time

import _archconfig
import _archcontexts
import _archgraph
import _archindex as ix
import _archparse
import _archstate
import _archstore
import _hookpaths
import _teamgate

UNSUPPORTED = ["registry.map_imperatively mappings", "constantize/send and importlib dynamic references",
               "JS config files (ESLint, dependency-cruiser) are never evaluated", "migration replay ignores rename_table"]


def refresh(root, options=None):
    """Refresh the index for `root`; {"locked": True} when another writer holds the lock."""
    opts = {"cache_dir": None, "budget": ix.DEFAULT_BUDGET, "rebuild": False, "paths": None}
    opts.update(options or {})
    directory = _archstore.index_dir(root, opts["cache_dir"])
    if not _archstate.acquire_lock(directory):
        _archstate.mark_dirty(directory)
        return {"locked": True, "complete": False, "parsed": 0, "deleted": 0, "timed_out": False}
    try:
        store = _archstore.open_store(root, opts["cache_dir"], write=True)
        try:
            stats = _deferred(store, opts) or _pass(store, root, opts)
            while not stats["timed_out"] and _archstate.take_dirty(directory):
                _archstate.touch_lock(directory)
                more = _pass(store, root, dict(opts, paths=None, rebuild=False))
                stats.update(parsed=stats["parsed"] + more["parsed"], deleted=stats["deleted"] + more["deleted"],
                             complete=more["complete"], files=more["files"], timed_out=more["timed_out"])
            return stats
        finally:
            store.close()
    finally:
        _archstate.release_lock(directory)


def _stale(store):
    """True for an index another parser generation stamped; never for one no pass has finished yet."""
    version = store.get_meta("schema_version")
    return version is not None and version != _archstore.SCHEMA_VERSION


def _deferred(store, opts):
    """A limited pass never drops a stale index: it marks it dirty for the full pass that follows (None otherwise)."""
    if opts["paths"] is None or not _stale(store):
        return None
    _archstate.mark_dirty(store.directory)
    return {"parsed": 0, "deleted": 0, "touched": 0, "timed_out": False, "complete": False, "files": 0, "stale": True}


def _maybe_wipe(store, rebuild):
    if not (rebuild or _stale(store)):
        return False
    store.begin()
    for table in _archstore.FACT_TABLES + ("files", "contexts", "coverage", "status"):
        store.delete(table, {})
    store.delete("meta", {"key": ["context_decl", "config_hash", "complete", "built_at"]})
    store.commit()
    return True


def _targets(root, paths, config):
    if paths is None:
        return ix.enumerate_files(root, config)
    rels = sorted({p.replace("\\", "/") for p in paths if _archparse.classify(p) and not ix.excluded(p, config)})
    return rels, {}


def _deleted_and_live(paths, existing, rels, missing):
    """(rows to delete, every path the index will hold) for a full pass (`paths` None) or a limited one."""
    gone = missing if paths is not None else sorted(set(existing) - set(rels))
    deleted = [r for r in gone if r in existing]
    live = sorted((set(existing) | set(rels)) - set(deleted)) if paths is not None else rels
    return deleted, live


def _parse_changes(store, changed, env, limits):
    """Index each changed file until the deadline. (file ids, timed out?)."""
    existing, deadline = limits
    ids = []
    for count, change in enumerate(changed, 1):
        if time.monotonic() > deadline:
            return ids, True
        if change[0] in existing:
            ix._delete_facts(store, [existing[change[0]]["id"]])
        ids.append(ix._index_one(store, change, env, existing))
        if count % ix.BATCH == 0:
            store.commit()
            _archstate.touch_lock(store.directory)
            store.begin()
    return ids, False


def _pass(store, root, opts):
    started, clock = time.time(), time.monotonic()
    rebuilt = _maybe_wipe(store, opts["rebuild"])
    resumed = store.get_meta("schema_version") is None
    config = _archconfig.load(root)[0]
    existing = {r["path"]: r for r in store.select("files", None, ["id", "path", "size", "mtime_ns", "sha1"])}
    rels, coverage = _targets(root, opts["paths"], config)
    changed, touched, missing = ix._scan_changes(root, rels, existing, started)
    deleted, live = _deleted_and_live(opts["paths"], existing, rels, missing)
    store.begin()
    cmap, context_changed = ix._context_env(store, root, live, config)
    env = {"root": root, "deployables": ix.deployable_dirs(live), "cmap": cmap, "frameworks": {}, "skipped_large": 0}
    ix._delete_facts(store, [existing[r]["id"] for r in deleted])
    store.delete("files", {"path": deleted})
    ids, timed_out = _parse_changes(store, changed, env, (existing, clock + float(opts["budget"])))
    for file_id, stat in touched:
        store.update("files", {"mtime_ns": stat.st_mtime_ns}, {"id": file_id})
    if context_changed and not rebuilt:
        reassign_contexts(store, cmap)
    added = any(rel not in existing for rel, _ in changed)
    whole = rebuilt or context_changed or resumed or not existing
    resolve_refs(store, root, None if whole else _affected_refs(store, ids, added, deleted))
    stats = _finish(store, root, {"parsed": len(ids), "deleted": len(deleted), "touched": len(touched),
                                  "timed_out": timed_out, "rebuilt": rebuilt, "full": opts["paths"] is None,
                                  "coverage": dict(coverage, skipped_large=env["skipped_large"],
                                                   config_unparsed=cmap.get("unparsed") or [])})
    stats["seconds"] = round(time.monotonic() - clock, 3)
    return stats


def _finish(store, root, stats):
    files = len(store.select("files", None, ["id"]))
    values = {"schema_version": _archstore.SCHEMA_VERSION, "plugin_version": _archstore.plugin_version(),
              "project_root": root.replace("\\", "/"), "checked_at": _archstore.now_iso(), "files": files}
    if stats["full"]:
        code, out = _teamgate.run_git(root, ["rev-parse", "HEAD"], 3)
        values["head"] = out.strip() if code == 0 else ""
        values["complete"] = "0" if stats["timed_out"] else "1"
        store.insert_many("coverage", [{"key": k, "value": _json(v)} for k, v in stats["coverage"].items()]
                          + [{"key": "unsupported", "value": _json(UNSUPPORTED)}])
        if not stats["timed_out"]:
            store.delete("status", {"source": ["index", "watch"]})
    elif stats["timed_out"]:
        values["complete"] = "0"
    if stats["parsed"] or stats["deleted"]:
        values["built_at"] = _archstore.now_iso()
    for key, value in values.items():
        store.set_meta(key, value)
    store.commit()
    return dict(stats, files=files, root=root, locked=False, truncated=bool(stats["coverage"].get("truncated")),
                complete=store.get_meta("complete", "0") == "1")


def _json(value):
    import json
    return json.dumps(value)


def reassign_contexts(store, cmap):
    for row in store.select("files", None, ["id", "path", "deployable", "context"]):
        context = _archcontexts.context_for(cmap, row["path"], row["deployable"])[0]
        if context != row["context"]:
            for table, key in (("files", "id"), ("tables", "file_id"), ("models", "file_id")):
                store.update(table, {"context": context}, {key: row["id"]})


def _resolve_one(ref, src, maps, root):
    symbol, lang = ref["symbol"], ref["lang"]
    if lang == "rb":
        return next((maps["consts"][n] for n in _archgraph.ruby_candidates(symbol, ref["scope"]) if n in maps["consts"]), None)
    if lang == "py":
        return _archgraph.resolve_first(_archgraph.python_candidates(symbol, src["path"], src["deployable"]), maps["paths"])
    if lang == "js":
        return _archgraph.resolve_first(_archgraph.js_candidates(symbol, src["path"], root, src["deployable"]), maps["paths"])
    return None


def resolve_refs(store, root, file_ids=None):
    """Re-resolve the refs of `file_ids` (all refs when None) against the whole index."""
    files = {f["id"]: f for f in store.select("files", None, ["id", "path", "deployable", "context"])}
    maps = {"paths": {f["path"]: f for f in files.values()}, "consts": {}}
    for row in store.select("consts", None, ["symbol", "file_id"]):
        maps["consts"].setdefault(row["symbol"], files.get(row["file_id"], {}).get("path"))
    rows = store.select("refs", None if file_ids is None else {"file_id": list(file_ids)})
    store.delete("refs", {} if file_ids is None else {"file_id": list(file_ids)})
    for ref in rows:
        src = files.get(ref["file_id"])
        dst = _resolve_one(ref, src, maps, root) if src else None
        ref.update(src_context=src["context"] if src else ref["src_context"], dst_path=dst,
                   dst_context=maps["paths"][dst]["context"] if dst in maps["paths"] else None)
    store.insert_many("refs", rows)
    return len(rows)


def _affected_refs(store, changed_ids, added, deleted_paths):
    ids = set(changed_ids)
    if added:
        ids |= {r["file_id"] for r in store.select("refs", {"dst_path": None}, ["file_id"], distinct=True)}
    if deleted_paths:
        ids |= {r["file_id"] for r in store.select("refs", {"dst_path": list(deleted_paths)}, ["file_id"], distinct=True)}
    return ids


def file_facts(root, rel, text=None, hints=None):
    """Facts for one file, read from disk unless `text` is given."""
    if text is None:
        text = _hookpaths._read_text(os.path.join(root, rel))
    return _archparse.parse_text(rel, text, hints)


def seed_worktree(root, cache_dir=None):
    """Copy the main checkout's index into a linked worktree that has none. True when seeded."""
    target = os.path.join(_archstore.index_dir(root, cache_dir), "index.sqlite")
    if os.path.exists(target) or _archstore.sqlite_module() is None:
        return False
    code, out = _teamgate.run_git(root, ["rev-parse", "--absolute-git-dir", "--git-common-dir"], 3)
    lines = out.splitlines()
    if code != 0 or len(lines) < 2:
        return False
    common = os.path.abspath(os.path.join(root, lines[1]))
    if os.path.normcase(os.path.abspath(lines[0])) == os.path.normcase(common) or os.path.basename(common) != ".git":
        return False
    source = os.path.join(_archstore.index_dir(os.path.dirname(common), cache_dir), "index.sqlite")
    if not os.path.isfile(source):
        return False
    os.makedirs(os.path.dirname(target), exist_ok=True)
    sqlite3 = _archstore.sqlite_module()
    src, dst = sqlite3.connect(source), sqlite3.connect(target)
    try:
        src.backup(dst)
    finally:
        src.close()
        dst.close()
    return True
