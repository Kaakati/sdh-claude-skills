#!/usr/bin/env python3
"""Orthogonality index side files: the writer lock (`_archlock`, re-exported here), the watcher's state,
atomic JSON writes, and the JSON fallback store used when Python was built without sqlite3.

refresh.lock  O_CREAT|O_EXCL, holds "pid timestamp host"; broken when older than LOCK_STALE_SECONDS, or
              at once when its holder on this host no longer runs (`_archlock`).
watch.state   {"dirty": 0|1, "pending": [paths]}: a writer that cannot take the lock sets dirty=1, and
              the lock holder runs one more pass before releasing; `pending` holds paths a watcher could
              not index while another writer held the lock, which the first baseline leaves out.
index.json    the fallback store, written to index.json.new and moved with os.replace, retried
              REPLACE_RETRIES times REPLACE_DELAY apart (Windows refuses a replace onto a file
              another process holds open); when every retry fails the next load picks up .new.
"""
import copy
import json
import os
import time

import _archstore
from _archlock import LOCK_NAME, LOCK_STALE_SECONDS, acquire_lock, lock_held, release_lock, touch_lock  # noqa: F401

STATE_NAME = "watch.state"
REPLACE_RETRIES = 5
REPLACE_DELAY = 0.05
MAX_PENDING = 200


def atomic_write(path, text):
    """Write `text` to `path` via `<path>.new` + os.replace with retries. True when it landed."""
    staging = path + ".new"
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(staging, "w", encoding="utf-8") as handle:
            handle.write(text)
    except OSError:
        return False
    for _ in range(REPLACE_RETRIES):
        try:
            os.replace(staging, path)
            return True
        except OSError:
            time.sleep(REPLACE_DELAY)
    return False


def read_state(directory):
    try:
        with open(os.path.join(directory, STATE_NAME), encoding="utf-8") as handle:
            state = json.load(handle)
        return state if isinstance(state, dict) else {}
    except (OSError, ValueError):
        return {}


def write_state(directory, **changes):
    state = read_state(directory)
    state.update(changes)
    atomic_write(os.path.join(directory, STATE_NAME), json.dumps(state))
    return state


def mark_dirty(directory):
    write_state(directory, dirty=1)


def take_dirty(directory):
    """True (and cleared) when another writer asked for one more pass."""
    if read_state(directory).get("dirty"):
        write_state(directory, dirty=0)
        return True
    return False


def pending(directory):
    """Paths a watcher could not index because another writer held the lock."""
    return [p for p in read_state(directory).get("pending") or [] if isinstance(p, str)]


def add_pending(directory, paths):
    merged = set(pending(directory)) | {p for p in paths or [] if isinstance(p, str)}
    write_state(directory, pending=sorted(merged)[:MAX_PENDING])


def clear_pending(directory):
    write_state(directory, pending=[])


def _matches(row, where):
    for key, value in (where or {}).items():
        got = row.get(key)
        if isinstance(value, (list, tuple, set, frozenset)):
            if got not in value:
                return False
        elif got != value:
            return False
    return True


class JsonStore(object):
    """The same row API as SqliteStore, held in memory and written as one JSON file on commit."""
    kind = "json"

    def __init__(self, path, data, writable):
        self.path, self.writable, self.directory = path, writable, os.path.dirname(path)
        self.data = data
        self._saved = None

    def _rows(self, table):
        return self.data["rows"].setdefault(table, [])

    def select(self, table, where=None, columns=None, distinct=False):
        big = {k: set(v) for k, v in (where or {}).items() if isinstance(v, (list, tuple)) and len(v) > 8}
        clause = dict(where or {}, **big)
        rows = [r for r in self._rows(table) if _matches(r, clause)]
        if columns:
            rows = [{c: r.get(c) for c in columns} for r in rows]
        if distinct:
            seen, unique = set(), []
            for row in rows:
                key = json.dumps(row, sort_keys=True)
                if key not in seen:
                    seen.add(key)
                    unique.append(row)
            rows = unique
        return [dict(r) for r in rows]

    def insert(self, table, row):
        row = dict(row)
        if table in _archstore.ID_TABLES and not row.get("id"):
            counters = self.data.setdefault("next_id", {})
            row["id"] = counters.get(table, 1)
            counters[table] = row["id"] + 1
        self._rows(table).append(row)
        return row.get("id")

    def insert_many(self, table, rows):
        for row in rows:
            self._upsert(table, row)

    def _upsert(self, table, row):
        unique = {"meta": "key", "files": "path", "contexts": "name", "coverage": "key",
                  "findings_baseline": "fingerprint", "tool_seen": "fingerprint"}.get(table)
        if unique:
            self.data["rows"][table] = [r for r in self._rows(table) if r.get(unique) != row.get(unique)]
        self.insert(table, row)

    def delete(self, table, where):
        self.data["rows"][table] = [r for r in self._rows(table) if not _matches(r, where)]

    def update(self, table, values, where):
        for row in self._rows(table):
            if _matches(row, where):
                row.update(values)

    def get_meta(self, key, default=None):
        rows = self.select("meta", {"key": key})
        return rows[0]["value"] if rows else default

    def set_meta(self, key, value):
        self._upsert("meta", {"key": key, "value": str(value)})

    def begin(self):
        pass

    def commit(self):
        if self.writable:
            atomic_write(self.path, json.dumps(self.data, separators=(",", ":")))

    def snapshot(self):
        self._saved = copy.deepcopy(self.data)

    def restore(self):
        if self._saved is not None:
            self.data, self._saved = self._saved, None

    def close(self):
        pass


def _load_json(path):
    for candidate in (path + ".new", path):
        try:
            with open(candidate, encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict) and isinstance(data.get("rows"), dict):
                return data
        except (OSError, ValueError):
            continue
    return None


def open_json_store(directory, write):
    """The fallback store; None when absent and not writing. Another schema starts it empty. One no pass has
    finished yet (no stamp) keeps its rows for the writer that resumes it, and raises IndexIncomplete to readers."""
    path = os.path.join(directory, "index.json")
    data = _load_json(path)
    stamps = [r.get("value") for r in ((data or {}).get("rows", {}).get("meta") or []) if r.get("key") == "schema_version"]
    other = bool(stamps) and _archstore.SCHEMA_VERSION not in stamps
    if not write:
        if data is not None and not stamps:
            raise _archstore.IndexIncomplete("no refresh pass has finished yet")
        if data is not None and other:
            raise _archstore.StoreError("index schema changed; it rebuilds at the next refresh")
        return JsonStore(path, data, False) if data is not None else None
    if data is None or other:
        data = {"rows": {name: [] for name in _archstore.TABLE_NAMES}, "next_id": {}}
    os.makedirs(directory, exist_ok=True)
    return JsonStore(path, data, True)
