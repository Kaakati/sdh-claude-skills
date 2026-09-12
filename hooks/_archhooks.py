#!/usr/bin/env python3
"""Entry points the orthogonality hooks call, so each hook script is a thin wrapper.

    checker_lines(event, budget=1.5) -> [str]   orthogonality-checker.py (dispatched PostToolUse):
        reads the index read-only, parses only the edited file, returns at most 3 lines plus notes.
    session_refresh(event, budget=120.0) -> dict orthogonality-index.py (SessionStart async):
        seeds a linked worktree, refreshes incrementally, stamps the baseline once complete.
    watch(event, budget=120.0) -> (int, str)     orthogonality-watch.py (PostToolUse asyncRewake), in
        `_archwatch`: exit 2 plus at most 5 stderr lines only for new findings after a shell install or
        generator; a crash records a status row and returns (0, "").

None of them prints, asks or denies. `SDH_ORTHOGONALITY=off` disables all three. No index is built for a
root that is no project (`_archindex.indexable_root`), and a file over the index's per-file cap is not
re-parsed at edit time. DK6 clone fingerprints are never built or read here (owner decision D).
"""
import os
import re
import time

import _archconfig
import _archcontexts
import _archindex
import _archparse
import _archparse_manifest
import _archrefresh
import _archrules
import _archstate
import _archstore
import _archview
import _hooklib
import _hookpaths

SOURCE_EXTENSIONS = (".rb", ".py", ".ts", ".tsx", ".js", ".jsx", ".sql")
ORTH_BUDGET_SECONDS = 1.5
MAX_HOOK_LINES = 3
WATCH_MAX_LINES = 5
FILE_LOCAL = ("DK4", "MF3", "MF5", "CM1")
WATCH_DETECTORS = ("CM1", "DK1", "DK2", "BC2")
NOT_BUILT = ("ORTHOGONALITY note: the index for this project is not built yet, so duplicate and boundary checks ran "
             "on the edited file only. It builds at the next session start, or with the `orthogonality` skill's arch_index.py.")
BUILDING = ("ORTHOGONALITY note: the index for this project is still being built in the background, so duplicate and "
            "boundary checks ran on the edited file only until it finishes. Per the `orthogonality` skill.")


def disabled():
    return os.environ.get("SDH_ORTHOGONALITY", "").strip().lower() in ("off", "0", "false", "no")


def in_scope(file_path):
    norm = _hookpaths.normalize(file_path or "")
    if not norm:
        return False
    return norm.endswith(SOURCE_EXTENSIONS) or _archparse_manifest.is_manifest(norm)


def _vendored_ui(file_path):
    try:
        import _vendored
        return _vendored.is_vendored_ui(file_path)
    except Exception:
        return False


def _once(event, key, text):
    return [text] if _hooklib.first_in_session(event, key) else []


def _deployable(view, root, rel):
    row = view.file_by_path(rel)
    if row:
        return row["deployable"]
    found = _hookpaths.project_root(os.path.join(root, rel))
    found_rel = _archindex.rel_path(root, os.path.join(found, "__probe__")) if found else None
    return found_rel.rsplit("/", 1)[0] if found_rel and "/" in found_rel else "."


def _over_cap(root, rel):
    try:
        return os.path.getsize(os.path.join(root, rel)) > _archindex.MAX_BYTES
    except OSError:
        return False


def _hints(view, rel):
    """What the index knows for the Python parser's MF5: JSON columns, and names that are not JSON."""
    if view.store is None or not rel.endswith(".py"):
        return None
    return {"json_fields": view.json_field_names(), "not_json": view.not_json_names()}


def _stored_facts(view, row):
    """The facts of an over-cap schema, migration, model or manifest, from its index rows (re-parsing would take seconds)."""
    facts = _archparse.empty_facts()
    if row is None:
        return facts
    columns = {}
    for column in view.select("columns", {"file_id": row["id"]}):
        columns.setdefault(column["table_id"], []).append(_archview.column_dict(column))
    facts["tables"] = [dict(_archview.table_dict(t, [], row["path"]), columns=columns.get(t["id"], []))
                       for t in view.select("tables", {"file_id": row["id"]})]
    facts["deps"] = [dict(d, group=d["grp"]) for d in view.select("deps", {"file_id": row["id"]})]
    facts["markers"] = view.select("markers", {"file_id": row["id"]})
    return facts


def build_delta(view, root, rel, text=None):
    """The edited file's facts and place: {path, file_id, deployable, context, declared, kind, facts}. None for a file
    over the index's per-file cap that the index skips too; an over-cap file the index keeps comes from its rows."""
    row, kind = view.file_by_path(rel), _archparse.classify(rel)
    large = text is None and _over_cap(root, rel)
    if large and kind not in _archindex.PRIORITY_KINDS:
        return None
    deployable = _deployable(view, root, rel)
    context, declared = _archcontexts.context_for(view.cmap, rel, deployable)
    facts = _stored_facts(view, row) if large else _archrefresh.file_facts(root, rel, text, _hints(view, rel))
    return {"path": rel, "file_id": row["id"] if row else None, "deployable": deployable, "context": context,
            "declared": declared, "kind": kind, "facts": facts}


def _open_readonly(event, root):
    """(store or None, notes): no project root, a missing, still-building or unreadable index is a once-per-session note."""
    if not _archindex.indexable_root(root):
        return None, _once(event, "orth-no-project", "ORTHOGONALITY note: %s holds no .git or package manifest, so no index is "
                           "built for it and checks ran on the edited file only. Per the `orthogonality` skill." % root)
    try:
        store = _archstore.open_store(root)
    except _archstore.IndexIncomplete:
        building = _archstate.lock_held(_archstore.index_dir(root))
        return None, _once(event, "orth-index-building" if building else "orth-index-missing", BUILDING if building else NOT_BUILT)
    except _archstore.StoreError as exc:
        if "locked" in str(exc) or "busy" in str(exc):
            return None, []
        return None, _once(event, "orth-index-unreadable", "ORTHOGONALITY note: the index for this project is unreadable (%s), so "
                           "checks ran on the edited file only. It rebuilds at the next session start, or with the `orthogonality` "
                           "skill's arch_index.py --rebuild." % exc)
    return store, (_once(event, "orth-index-missing", NOT_BUILT) if store is None else [])


def _config_notes(event, errors):
    if not errors:
        return []
    first = errors[0]
    if not _hooklib.first_in_session(event, "orth-config-" + re.sub(r"\W", "_", first["path"] + first["message"])[:60]):
        return []
    return ["ORTHOGONALITY [CFG-INVALID invalid-config] %s %s: %s; its declarations were ignored (%d problem(s)). Per the `orthogonality` skill." % (
        _archconfig.CONFIG_REL, first["path"], first["message"], len(errors))]


def _notes(event, store, not_run):
    lines = []
    skipped = sorted(d for d, why in not_run.items() if why == _archrules.BUDGET_REASON)
    if skipped and _hooklib.first_in_session(event, "orth-budget"):
        lines.append("ORTHOGONALITY note: checks stopped at the %.1fs budget; %s did not run on this edit. "
                     "Run the `orthogonality` skill's arch_scan.py for them." % (ORTH_BUDGET_SECONDS, ", ".join(skipped)))
    failures = [r for r in (store.select("status") if store is not None else []) if r["source"] in ("index", "watch")]
    if failures and _hooklib.first_in_session(event, "orth-status"):
        lines.append("ORTHOGONALITY note: a background index refresh failed (%s); checks used the index as it was. Rebuild with "
                     "the `orthogonality` skill's arch_index.py --rebuild." % failures[-1]["message"][:160])
    return lines


def _findings(view, delta, detectors, deadline):
    findings, not_run = _archrules.run_detectors(view, delta, detectors, deadline)
    findings += _archrules.marker_findings([m for m in delta["facts"]["markers"]], delta["path"])
    findings += _archrules.declaration_findings(view.config, view.root)
    _archrules.apply_suppressions(findings, view, delta)
    _archrules.mark_new(findings, view)
    return findings, not_run


def checker_lines(event, budget=ORTH_BUDGET_SECONDS):
    """The dispatched checker: warning lines for the edited file (never raises for a normal miss)."""
    started = time.monotonic()
    file_path = _hooklib.get_file_path(event)
    if disabled() or not in_scope(file_path) or _vendored_ui(file_path):
        return []
    root = _archindex.resolve_root(event.get("cwd"), file_path)
    rel = _archindex.rel_path(root, file_path) if root else None
    if not rel:
        return []
    config, errors, _ = _archconfig.load(root)
    if _archindex.excluded(rel, config):
        return _config_notes(event, errors)
    store, lines = _open_readonly(event, root)
    try:
        view = _archview.IndexView(store, root, config)
        delta = build_delta(view, root, rel)
        if delta is None:
            return _config_notes(event, errors) + lines + _once(event, "orth-large", "ORTHOGONALITY note: %s is over the index's 1 MB "
                                                                "per-file cap, so edit-time checks skip it, as the index does. "
                                                                "Per the `orthogonality` skill." % rel)
        detectors = _archrules.EDIT_TIME if store is not None else FILE_LOCAL
        findings, not_run = _findings(view, delta, detectors, started + budget)
        return _config_notes(event, errors) + lines + _archrules.hook_lines(findings, event, MAX_HOOK_LINES) + _notes(event, store, not_run)
    finally:
        if store is not None:
            store.close()


def record_status(root, source, exc):
    """Write a failure into the index status table (best effort; never raises). A failure before the first
    refresh creates the index here, so the schema version is stamped too: without it every read-only open
    reports "unreadable" and the checker's note could never show the recorded failure."""
    try:
        store = _archstore.open_store(root, write=True)
        if store.get_meta("schema_version") is None:
            store.set_meta("schema_version", _archstore.SCHEMA_VERSION)
        store.insert("status", {"at": _archstore.now_iso(), "source": source, "message": "%s: %s" % (type(exc).__name__, exc)})
        store.close()
    except Exception:
        pass


def take_baseline(root, deadline=None):
    """Stamp the baseline for edit-time detectors on a complete index (once per project). A detector that does not
    finish before `deadline` stays unstamped for the next session; findings on paths a watcher could not index
    while this build held the lock (`pending`) stay out of it, so what the session just added is never frozen."""
    directory = _archstore.index_dir(root)
    if not _archstate.acquire_lock(directory):
        return []
    try:
        store = _archstore.open_store(root, write=True)
        try:
            view = _archview.IndexView(store, root, _archconfig.load(root)[0])
            missing = [d for d in _archrules.EDIT_TIME if d not in _archrules.covered_detectors(view)]
            if not missing or store.get_meta("complete") != "1":
                return []
            findings, not_run = _archrules.run_detectors(view, None, missing, deadline)
            pending = set(_archstate.pending(directory))
            kept = [f for f in findings if f["subject"]["path"] not in pending]
            return _archrules.ensure_baseline(store, kept, [d for d in missing if d not in not_run])
        finally:
            store.close()
    finally:
        _archstate.release_lock(directory)


def session_refresh(event, budget=_archindex.DEFAULT_BUDGET):
    """SessionStart: refresh the index (startup/resume/fork), then stamp the baseline inside the same budget.
    Nothing for a root that is no project. Errors land in the status table."""
    if disabled() or (event or {}).get("source") in ("clear", "compact"):
        return {}
    started = time.monotonic()
    root = _archindex.resolve_root((event or {}).get("cwd") or os.getcwd())
    if not _archindex.indexable_root(root):
        return {}
    try:
        _archrefresh.seed_worktree(root)
        stats = _archrefresh.refresh(root, {"budget": budget})
        stats["baseline"] = take_baseline(root, started + budget) if stats.get("complete") else []
        return stats
    except Exception as exc:
        record_status(root, "index", exc)
        return {"error": "%s: %s" % (type(exc).__name__, exc)}


def classify_command(command):
    """'install' | 'generator' | 'vcs' | None for a shell command line (see `_archwatch`)."""
    import _archwatch
    return _archwatch.classify_command(command)


def watch(event, budget=_archindex.DEFAULT_BUDGET):
    """(exit code, stderr text) for the asyncRewake watcher (see `_archwatch`)."""
    import _archwatch
    return _archwatch.watch(event, budget)


def wake(findings, event, trigger):
    """(2, header + at most WATCH_MAX_LINES - 2 finding lines + footer) when a finding is new this session, else (0, "")."""
    lines = _archrules.hook_lines(findings, event, WATCH_MAX_LINES - 2)
    if not lines:
        return 0, ""
    header = "ORTHOGONALITY (background): %d new finding(s) after %s:" % (len(lines), trigger)
    return 2, "\n".join([header] + lines + ["Full list: the `orthogonality` skill's arch_scan.py."])
