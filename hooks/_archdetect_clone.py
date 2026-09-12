#!/usr/bin/env python3
"""DK6 copy-paste-block, for scans and CI only (owner decision D: no edit-time clone cache).

Business-logic directories get `warn`; everything else `info`; tests only with `include_tests`.
Never compared: migrations, schema files, generated files, vendored shadcn/ui primitives
(`_vendored.is_vendored_ui`), serializer and schema modules whose duplicate is only a field list,
files over the index's 1 MB per-file cap, and clones inside one file (the `std-code-standards`
skill's territory). Files are read one at a time into a compact corpus, and the run's deadline stops
the reading and the search (the detector is then reported as not run).
Options come from `view.options`: subjects (paths), min_tokens, min_lines, include_tests, texts
(path -> text overrides, used to score a base revision). `SDH_ORTHOGONALITY_CLONES=0` skips DK6, as
the `orthogonality` skill's scans-and-tools.md documents.
"""
import os
import re

import _archclone
import _archconfig
import _archindex
import _archrules
import _hookpaths

BUSINESS = re.compile(r"(?:^|/)(?:app/services|app/models|app/jobs|app/tasks|lib|src/hooks|src/api|src/domain|src/actions|src/lib)/"
                      r"|(?:^|/)(?:services|models|tasks)\.py$|(?:^|/)services/")
NEVER = re.compile(r"(?:^|/)(?:db/migrate|migrations|alembic/versions|serializers|schemas)/|(?:^|/)db/(?:schema\.rb|structure\.sql)$"
                   r"|\.generated\.|\.min\.js$")
TESTS = re.compile(r"(?:^|/)(?:spec|specs|test|tests|__tests__)/|_spec\.rb$|_test\.(?:py|rb)$|(?:^|/)test_[^/]*\.py$|\.(?:test|spec)\.[jt]sx?$")


def _eligible(root, path, include_tests):
    if not _archclone.language(path) or NEVER.search(path):
        return False
    if TESTS.search(path) and not include_tests:
        return False
    try:
        import _vendored
        return not _vendored.is_vendored_ui(os.path.join(root, path))
    except Exception:
        return True


def _paths(view, options):
    """Eligible paths: the indexed files plus base-revision overrides, minus config `clones.ignore`."""
    overrides, include = options.get("texts") or {}, options.get("include_tests")
    ignore = (view.config.get("clones") or {}).get("ignore") or []
    paths = {f["path"] for f in view.all_files() if _eligible(view.root, f["path"], include)}
    paths |= {p for p in overrides if _eligible(view.root, p, include)}
    return sorted(p for p in paths if not _archconfig.matches(p, ignore))


def _sources(view, paths, overrides):
    """(path, text) per path, read one at a time; a file over the per-file cap is skipped, as the index skips it."""
    for path in paths:
        if _archrules.out_of_time(view):
            return
        if path in overrides:
            text = overrides[path]
        else:
            full = os.path.join(view.root, path)
            text = _hookpaths._read_text(full) if os.path.isfile(full) and os.path.getsize(full) <= _archindex.MAX_BYTES else None
        if text is not None and len(text.encode("utf-8", "replace")) <= _archindex.MAX_BYTES:
            yield path, text


def _subjects(options, paths):
    """The paths clone runs start from: every eligible path in a whole scan; the changed eligible files under
    --changed-since (none changed: no search); either narrowed to the --paths / --changed-since scope. The corpus
    still holds every eligible file, so a clone into any other file is found."""
    listed = set(paths)
    subjects = listed if options.get("subjects") is None else set(options["subjects"]) & listed
    scope = options.get("scope")
    if scope is None:
        return subjects
    exact, folders = set(scope), tuple(s.rstrip("/") + "/" for s in scope)
    return {p for p in subjects if p in exact or p.startswith(folders)}


def _finding(clone):
    warn = BUSINESS.search(clone["a"]) and BUSINESS.search(clone["b"]) and not TESTS.search(clone["a"] + " " + clone["b"])
    text = "%s:%d-%d and %s:%d-%d are a %s clone of %d tokens. Extract the shared logic once, or declare the copy with its reason." % (
        clone["a"], clone["a_start"], clone["a_end"], clone["b"], clone["b_start"], clone["b_end"], clone["kind"], clone["tokens"])
    pair = sorted((clone["a"], clone["b"]))
    return _archrules.make("DK6", {"path": clone["a"], "line": clone["a_start"], "symbol": clone["a"]}, text,
                           related=[{"path": clone["b"], "line": clone["b_start"], "symbol": clone["b"]}],
                           severity="warn" if warn else "info", confidence="medium",
                           key=("%s|%s" % tuple(pair), clone["hash"]),
                           evidence={"tokens": clone["tokens"], "kind": clone["kind"],
                                     "ranges": ["%s:%d-%d" % (clone["a"], clone["a_start"], clone["a_end"]),
                                                "%s:%d-%d" % (clone["b"], clone["b_start"], clone["b_end"])]})


def detect_dk6(view, delta, config):
    if delta is not None or os.environ.get("SDH_ORTHOGONALITY_CLONES", "").strip() == "0":
        return []
    options = getattr(view, "options", None) or {}
    paths = _paths(view, options)
    subjects = _subjects(options, paths)
    if not subjects:
        return []
    min_tokens = int(options.get("min_tokens") or (config.get("clones") or {}).get("min_tokens") or _archclone.MIN_TOKENS)
    corpus = _archclone.build_corpus(_sources(view, paths, options.get("texts") or {}), min_tokens, subjects)
    limits, clones = (min_tokens, int(options.get("min_lines") or _archclone.MIN_LINES)), []
    for path in sorted(p for p in subjects if p in corpus.ids):
        if _archrules.out_of_time(view):
            break
        clones += _archclone.clones_for(corpus, path, limits)
    return [_finding(c) for c in _archclone.dedupe(clones)]
