#!/usr/bin/env python3
"""Orthogonality index storage: `${CLAUDE_PLUGIN_DATA}/orthogonality/<key>/index.sqlite`. The key joins
sha1(normcase(realpath(root)))[:16], basename(root)[:24] and "v" + SCHEMA_VERSION: the parser generation is
part of it, so sessions on two plugin versions (the data directory outlives every version) never share or
wipe one database. `SDH_ORTHOGONALITY_DIR` overrides the root; without CLAUDE_PLUGIN_DATA it is
`<tempdir>/sdh-orthogonality`. A rebuildable cache, never a record. SQLite and the JSON fallback (`_archstate`)
share one row API: select(table, where, columns, distinct) / insert / insert_many / delete / update / get_meta
/ set_meta / begin / commit / snapshot / restore / close; `where` maps a column to a scalar, None (IS NULL) or a
collection (IN). Readers never lock: busy or unreadable raises `StoreError`, never finished `IndexIncomplete`.
"""
import hashlib
import json
import os
import tempfile
import time

SCHEMA_VERSION = "3"  # the parser generation: bump it whenever a parser or a stored fact changes
BUSY_MS = 200
IN_CHUNK = 900
_HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))

SCHEMA = (
    ("meta", "key TEXT PRIMARY KEY, value TEXT"),
    ("files", "id INTEGER PRIMARY KEY, path TEXT UNIQUE, kind TEXT, lang TEXT, framework TEXT, "
              "deployable TEXT, context TEXT, size INTEGER, mtime_ns INTEGER, sha1 TEXT, parsed_at REAL"),
    ("tables", "id INTEGER PRIMARY KEY, file_id INTEGER, name TEXT, norm TEXT, near TEXT, context TEXT, "
               "deployable TEXT, line INTEGER, origin TEXT, kind TEXT, read_model INTEGER, extra TEXT"),
    ("columns", "table_id INTEGER, file_id INTEGER, name TEXT, family TEXT, fk_table TEXT, "
                "nullable INTEGER, op TEXT, line INTEGER"),
    ("models", "id INTEGER PRIMARY KEY, file_id INTEGER, symbol TEXT, norm TEXT, tbl TEXT, context TEXT, "
               "deployable TEXT, line INTEGER, abstract INTEGER, sti_parent TEXT, proxy INTEGER, framework TEXT"),
    ("consts", "file_id INTEGER, symbol TEXT, line INTEGER"),
    ("refs", "file_id INTEGER, line INTEGER, symbol TEXT, scope TEXT, lang TEXT, type_only INTEGER, "
             "src_context TEXT, dst_path TEXT, dst_context TEXT"),
    ("writes", "file_id INTEGER, line INTEGER, symbol TEXT, op TEXT, tbl TEXT"),
    ("factories", "file_id INTEGER, line INTEGER, kind TEXT, target TEXT, deployable TEXT"),
    ("handlers", "file_id INTEGER, line INTEGER, kind TEXT, exception TEXT, deployable TEXT"),
    ("pagination", "file_id INTEGER, line INTEGER, style TEXT, deployable TEXT"),
    ("deps", "file_id INTEGER, line INTEGER, ecosystem TEXT, package TEXT, grp TEXT, deployable TEXT"),
    ("variants", "file_id INTEGER, line INTEGER, kind TEXT, variant TEXT, deployable TEXT"),
    ("jsonb", "file_id INTEGER, line INTEGER, field TEXT, key TEXT, confidence TEXT"), ("markers", "file_id INTEGER, line INTEGER, detector TEXT, reason TEXT"),
    ("tf", "file_id INTEGER, line INTEGER, block TEXT, type TEXT, name TEXT, source TEXT, version TEXT"),
    ("txns", "file_id INTEGER, line INTEGER, end_line INTEGER"),
    ("contexts", "name TEXT PRIMARY KEY, source TEXT, declared INTEGER, parent TEXT, data TEXT"),
    ("findings_baseline", "fingerprint TEXT PRIMARY KEY, detector TEXT, subject TEXT, first_seen TEXT"),
    ("baseline_history", "taken_at TEXT, detector TEXT, count INTEGER, reason TEXT"), ("tool_seen", "fingerprint TEXT PRIMARY KEY, tool TEXT, first_seen TEXT"),
    ("status", "at TEXT, source TEXT, message TEXT"), ("coverage", "key TEXT PRIMARY KEY, value TEXT"),
)
TABLE_NAMES = tuple(name for name, _ in SCHEMA)
FACT_TABLES = ("tables", "columns", "models", "consts", "refs", "writes", "factories", "handlers",
               "pagination", "deps", "variants", "jsonb", "markers", "tf", "txns")
ID_TABLES = ("files", "tables", "models")
INDEXES = ("files(deployable)", "files(kind)", "tables(name)", "tables(norm)", "tables(near)", "tables(deployable)", "columns(table_id)",
           "columns(name)", "columns(family)", "models(symbol)", "models(tbl)", "models(norm)", "models(deployable)", "consts(symbol)",
           "refs(src_context, dst_context, type_only)", "refs(dst_path)", "writes(tbl)", "factories(deployable)", "handlers(deployable)",
           "pagination(deployable)", "deps(deployable)", "variants(deployable, kind)") + tuple("%s(file_id)" % table for table in FACT_TABLES)


class StoreError(Exception):
    """The index exists but cannot be read now (busy, locked, corrupt, or from another schema)."""


class IndexIncomplete(StoreError):
    """The index exists but no refresh pass has finished yet: a first build still running, or one that was killed."""


def sqlite_module():
    try:
        import sqlite3
        return sqlite3
    except ImportError:
        return None


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def plugin_version():
    try:
        with open(os.path.join(_HOOKS_DIR, "..", ".claude-plugin", "plugin.json"), encoding="utf-8") as handle:
            return str(json.load(handle).get("version") or "unknown")
    except (OSError, ValueError, AttributeError):
        return "unknown"


def project_key(root):
    real = os.path.normcase(os.path.realpath(root))
    base = os.path.basename(os.path.normpath(root))[:24] or "root"
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in base)
    return "%s-%s-v%s" % (hashlib.sha1(real.encode("utf-8")).hexdigest()[:16], safe, SCHEMA_VERSION)


def cache_root(explicit=None):
    """--cache-dir, else SDH_ORTHOGONALITY_DIR, else $CLAUDE_PLUGIN_DATA/orthogonality, else tempdir."""
    for candidate in (explicit, os.environ.get("SDH_ORTHOGONALITY_DIR")):
        if candidate:
            return os.path.abspath(candidate)
    data = os.environ.get("CLAUDE_PLUGIN_DATA")
    if data:
        return os.path.join(os.path.abspath(data), "orthogonality")
    return os.path.join(tempfile.gettempdir(), "sdh-orthogonality")


def index_dir(root, cache_dir=None):
    return os.path.join(cache_root(cache_dir), project_key(root))


def _where_sql(where):
    """(" WHERE ...", params), or (None, None) when an empty IN list can match nothing."""
    clauses, params = [], []
    for key in sorted(where or {}):
        value = where[key]
        if isinstance(value, (list, tuple, set, frozenset)):
            if not value:
                return None, None
            clauses.append('"%s" IN (%s)' % (key, ",".join("?" * len(value))))
            params.extend(list(value))
        elif value is None:
            clauses.append('"%s" IS NULL' % key)
        else:
            clauses.append('"%s" = ?' % key)
            params.append(value)
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", params


def _chunked(where):
    for key, value in sorted((where or {}).items()):
        if isinstance(value, (list, tuple, set, frozenset)) and len(value) > IN_CHUNK:
            values = sorted(value, key=str)
            return [dict(where, **{key: values[i:i + IN_CHUNK]}) for i in range(0, len(values), IN_CHUNK)]
    return [where or {}]


class SqliteStore(object):
    kind = "sqlite"

    def __init__(self, conn, directory, writable):
        self.conn, self.directory, self.writable = conn, directory, writable

    def select(self, table, where=None, columns=None, distinct=False):
        cols = ", ".join('"%s"' % c for c in columns) if columns else "*"
        rows = []
        for part in _chunked(where):
            clause, params = _where_sql(part)
            if clause is not None:
                rows.extend(self._fetch("SELECT %s%s FROM %s%s" % ("DISTINCT " if distinct else "", cols, table, clause), params))
        return rows

    def _fetch(self, sql, params):
        try:
            cursor = self.conn.execute(sql, params)
        except sqlite_module().Error as exc:
            raise StoreError("%s: %s" % (type(exc).__name__, exc))
        names = [d[0] for d in cursor.description]
        return [dict(zip(names, row)) for row in cursor.fetchall()]

    def _insert_sql(self, table, keys, verb):
        return "%s INTO %s (%s) VALUES (%s)" % (verb, table, ", ".join('"%s"' % k for k in keys), ",".join("?" * len(keys)))

    def insert(self, table, row):
        keys = sorted(row)
        return self.conn.execute(self._insert_sql(table, keys, "INSERT"), [row[k] for k in keys]).lastrowid

    def insert_many(self, table, rows):
        if rows:
            keys = sorted(rows[0])
            self.conn.executemany(self._insert_sql(table, keys, "INSERT OR REPLACE"), [[r.get(k) for k in keys] for r in rows])

    def delete(self, table, where):
        for part in _chunked(where):
            clause, params = _where_sql(part)
            if clause is not None:
                self.conn.execute("DELETE FROM %s%s" % (table, clause), params)

    def update(self, table, values, where):
        keys = sorted(values)
        for part in _chunked(where):
            clause, params = _where_sql(part)
            if clause is not None:
                self.conn.execute("UPDATE %s SET %s%s" % (table, ", ".join('"%s" = ?' % k for k in keys), clause), [values[k] for k in keys] + params)

    def get_meta(self, key, default=None):
        rows = self.select("meta", {"key": key})
        return rows[0]["value"] if rows else default

    def set_meta(self, key, value):
        self.conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (key, str(value)))

    def begin(self):
        if not self.conn.in_transaction:
            self.conn.execute("BEGIN")

    def commit(self):
        if self.conn.in_transaction:
            self.conn.execute("COMMIT")

    def snapshot(self):
        self.conn.execute("SAVEPOINT arch_base")

    def restore(self):
        self.conn.execute("ROLLBACK TO arch_base")
        self.conn.execute("RELEASE arch_base")

    def close(self):
        try:
            self.commit()
            self.conn.close()
        except Exception:
            pass


def _create_schema(conn):
    for name, columns in SCHEMA:
        conn.execute("CREATE TABLE IF NOT EXISTS %s (%s)" % (name, columns))
    for spec in INDEXES:
        conn.execute("CREATE INDEX IF NOT EXISTS ix_%s ON %s" % ("".join(c if c.isalnum() else "_" for c in spec), spec))


def _schema_version(conn):
    try:
        row = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
        return row[0] if row else None
    except Exception:
        return None


def _connect(path, writable):
    sqlite3 = sqlite_module()
    if not writable:
        from urllib.request import pathname2url
        conn = sqlite3.connect("file:%s?mode=ro" % pathname2url(path), uri=True, timeout=BUSY_MS / 1000.0, isolation_level=None)
        conn.execute("PRAGMA busy_timeout=%d" % BUSY_MS)
        return conn
    conn = sqlite3.connect(path, timeout=5.0, isolation_level=None)
    for pragma in ("PRAGMA journal_mode=WAL", "PRAGMA synchronous=NORMAL"):
        try:
            conn.execute(pragma)
        except sqlite3.Error:
            pass
    return conn


def _move_aside(path):
    """Move a corrupt database (and its WAL files) aside, or delete it; StoreError when neither works."""
    for suffix in ("", "-wal", "-shm"):
        for action in (lambda p: os.replace(p, p + ".corrupt"), os.remove):
            try:
                action(path + suffix)
                break
            except OSError:
                continue
    if os.path.exists(path):
        raise StoreError("the index at %s is corrupt and held open by another process" % path)


def _writable_sqlite(path, directory):
    """Open for writing; a corrupt file is moved aside and rebuilt, another schema is dropped."""
    conn = None
    try:
        conn = _connect(path, True)
        version = _schema_version(conn)
        conn.execute("SELECT count(*) FROM sqlite_master").fetchone()
    except sqlite_module().DatabaseError as exc:
        if conn is not None:
            conn.close()
        _move_aside(path)
        conn, version = _connect(path, True), "corrupt: %s" % exc
    if version not in (None, SCHEMA_VERSION):
        for name in TABLE_NAMES:
            conn.execute("DROP TABLE IF EXISTS %s" % name)
    _create_schema(conn)
    store = SqliteStore(conn, directory, True)
    if str(version).startswith("corrupt"):
        store.insert("status", {"at": now_iso(), "source": "store", "message": "index was unreadable (%s); rebuilt" % version})
    return store


def open_store(root, cache_dir=None, write=False):
    """The index store for `root`; None when none exists and `write` is False. Raises StoreError."""
    directory = index_dir(root, cache_dir)
    if sqlite_module() is None:
        import _archstate
        return _archstate.open_json_store(directory, write)
    path = os.path.join(directory, "index.sqlite")
    if write:
        os.makedirs(directory, exist_ok=True)
        return _writable_sqlite(path, directory)
    if not os.path.isfile(path):
        return None
    try:
        conn = _connect(path, False)
        version = _schema_version(conn)
    except sqlite_module().Error as exc:
        raise StoreError("%s: %s" % (type(exc).__name__, exc))
    if version != SCHEMA_VERSION:
        conn.close()
        raise IndexIncomplete("no refresh pass has finished yet") if version is None else StoreError(
            "index schema %s is not %s; it rebuilds at the next refresh" % (version, SCHEMA_VERSION))
    return SqliteStore(conn, directory, False)
