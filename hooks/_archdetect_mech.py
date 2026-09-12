#!/usr/bin/env python3
"""Competing-mechanism detectors: CM1 second-library, CM2 second-client-wrapper, CM3
second-error-envelope, CM4 second-pagination-style, CM5 second-auth-mechanism (info), and MF2
first-of-kind-pattern (info).

CM1 reads direct dependencies only, per deployable, against `_mechanisms.json` rows for the
manifest's framework label. The house packages of a row form one mechanism; each competitor entry
(a package, or a list that works together) is another. Two mechanisms is `warn` (`info` when the
extra one is dev-only in an app concern); a single off-house mechanism is `info` (owner decision F:
silent in hooks). A workspace-root manifest counts only for tooling concerns. House overrides and
declared migrations (with `until`) come from `.claude/orthogonality.json`.

The per-site detectors (CM2-CM4, MF2) group their pool once, so a scan costs one pass over the sites,
not one pass per site. A scan limited by --paths or --changed-since (`view.options["scope"]`) takes
only the sites inside it as subjects; the pool they are compared with stays whole-index.
"""
import posixpath
import re

import _archconfig
import _archindex
import _archrules

TEST_PATH = re.compile(r"(?:^|/)(?:spec|specs|test|tests|__tests__|mocks|__mocks__|fixtures)/|_spec\.rb$|\.(?:test|spec)\.[jt]sx?$|(?:^|/)test_[^/]*\.py$")
HANDLER_FAMILY = {"fastapi-global": "global exception handler", "drf-global": "DRF exception handler",
                  "drf-override": "DRF exception handler", "envelope-builder": "error-envelope builder"}
AUTH_QUIET = re.compile(r"(?:^|/)config/initializers/|auth|webhook|jwks", re.I)


def _manifest_rows(view, delta):
    """{deployable: [dep rows with path]} for the deployables this run looks at."""
    if delta is not None:
        if delta.get("kind") != "manifest":
            return {}
        rows = [r for r in view.rows("deps", {"deployable": delta["deployable"]}) if r["file_id"] != delta.get("file_id")]
        rows += [dict(d, grp=d["group"], path=delta["path"], deployable=delta["deployable"]) for d in delta["facts"]["deps"]]
        return {delta["deployable"]: rows}
    grouped = {}
    for row in view.rows("deps"):
        grouped.setdefault(row["deployable"], []).append(row)
    return grouped


def _entries(row):
    return [[c] if isinstance(c, str) else list(c) for c in row.get("competitors") or []]


def _rows_for(view, concern, ecosystem, framework):
    return [r for r in view.registry()["concerns"][concern]["rows"] if r["ecosystem"] == ecosystem and framework in r["frameworks"]]


def _workspace_root(view, path, cache):
    if path not in cache:
        directory = posixpath.dirname(path)
        sibling = (directory + "/" if directory else "") + "pnpm-workspace.yaml"
        row = view.file_by_path(path)
        cache[path] = bool(row and row.get("lang") == "workspace") or bool(view.file_by_path(sibling))
    return cache[path]


def _mechanisms(view, concern, deployable, deps):
    """[(label packages, dep rows, is_house)] present for one concern in one deployable."""
    spec, frameworks, found, cache = view.registry()["concerns"][concern], {}, {}, {}
    for dep in deps:
        if _workspace_root(view, dep["path"], cache) and not spec.get("tooling"):
            continue
        key = (dep["ecosystem"],)
        frameworks.setdefault(key, _archindex.framework_for(view.root, deployable, dep["ecosystem"], view.cached("fw", dict)))
        for row in _rows_for(view, concern, dep["ecosystem"], frameworks[key]):
            _classify_dep(row, dep, found)
    detect = [f for r in spec["rows"] for f in r.get("detect_files") or []]
    if detect and any(view.file_by_path(posixpath.join("" if deployable == "." else deployable, f)) for f in detect):
        found.setdefault("house", {"packages": set(), "rows": [], "house": True, "row": spec["rows"][0]})
    return found


def _classify_dep(row, dep, found):
    name = dep["package"]
    if name in (row.get("companions") or []) or any(name.startswith(p) for p in row.get("companion_prefixes") or []):
        return
    if name in row["house"]:
        slot = found.setdefault("house", {"packages": set(), "rows": [], "house": True, "row": row})
    else:
        entry = next((e for e in _entries(row) if name in e), None)
        if entry is None:
            return
        slot = found.setdefault("+".join(entry), {"packages": set(), "rows": [], "house": False, "row": row})
    slot["packages"].add(name)
    slot["rows"].append(dep)


def _apply_override(view, deployable, concern, found):
    override = _archconfig.house_override(view.config, deployable, concern)
    if not override:
        return found
    for label, slot in found.items():
        slot["house"] = override["package"] in slot["packages"]
    return found


def _cm1_finding(view, deployable, concern, found):
    slots = sorted(found.values(), key=lambda s: (s["house"], -max(r["line"] for r in s["rows"])))
    subject_dep = max(slots[0]["rows"], key=lambda r: r["line"])
    other = slots[1] if len(slots) > 1 else None
    row, spec = slots[0]["row"], view.registry()["concerns"][concern]
    framework = _archindex.framework_for(view.root, deployable, subject_dep["ecosystem"], view.cached("fw", dict)) or "unlabelled"
    house = "+".join(row["house"] or row.get("js_house") or []) or "none named"
    note = (row.get("notes") or {}).get(subject_dep["package"], "")
    packages = sorted({p for s in slots for p in s["packages"]})
    migration = _archconfig.migration(view.config, deployable, concern, packages)
    if other:
        first = min(other["rows"], key=lambda r: r["line"])
        text = "%s:%d adds %s; %s (%s:%d) already covers %s for this %s deployable (house choice: %s).%s Remove one, or declare a migration with an until date." % (
            subject_dep["path"], subject_dep["line"], subject_dep["package"], first["package"], first["path"], first["line"],
            concern, framework, house, " " + note + "." if note else "")
    else:
        text = "%s:%d: %s covers %s for this %s deployable; the house choice is %s. One mechanism is orthogonal; record a client mandate as a house override." % (
            subject_dep["path"], subject_dep["line"], subject_dep["package"], concern, framework, house)
    dev_only = other and all(r["grp"] == "dev" for r in slots[0]["rows"]) and not spec.get("tooling")
    finding = _archrules.make(
        "CM1", {"path": subject_dep["path"], "line": subject_dep["line"], "symbol": subject_dep["package"], "context": deployable}, text,
        related=[{"path": first["path"], "line": first["line"], "symbol": first["package"], "context": deployable}] if other else [],
        severity="warn" if other and not dev_only else "info", confidence="high" if other else "medium",
        owner_skill=row.get("owner_skill") or spec.get("owner_skill"), suppress_config="mechanisms.migrations",
        key=("%s|%s" % (deployable, concern), "|".join(sorted("+".join(sorted(s["packages"])) for s in slots))),
        evidence={"concern": concern, "framework": framework, "house": house, "packages": packages})
    return _migration_state(finding, migration)


def _migration_state(finding, migration):
    if migration and _archconfig.expired(migration.get("until")):
        finding["expired"] = migration["until"]
    elif migration:
        finding["suppressed"] = "config"
    return finding


def detect_cm1(view, delta, config):
    found = []
    for deployable, deps in _manifest_rows(view, delta).items():
        if _archrules.out_of_time(view):
            break
        for concern in sorted(view.registry()["concerns"]):
            slots = _apply_override(view, deployable, concern, _mechanisms(view, concern, deployable, deps))
            if len(slots) >= 2 or (len(slots) == 1 and not list(slots.values())[0]["house"]):
                found.append(_cm1_finding(view, deployable, concern, slots))
    return found


def _scoped(rows, scope):
    """The rows whose path is, or lies under, one of the `scope` paths."""
    exact, folders = set(scope), tuple(s.rstrip("/") + "/" for s in scope)
    return [r for r in rows if r["path"] in exact or r["path"].startswith(folders)]


def _site_pool(view, delta, table):
    """(subject sites, all sites) for a per-deployable fact table, tests dropped."""
    if delta is not None:
        mine = [dict(s, path=delta["path"], deployable=delta["deployable"], file_id=delta.get("file_id")) for s in delta["facts"][table]]
        others = [r for r in view.rows(table, {"deployable": delta["deployable"]}) if r["file_id"] != delta.get("file_id")]
        return [s for s in mine if not TEST_PATH.search(s["path"])], [s for s in others + mine if not TEST_PATH.search(s["path"])]
    rows = [r for r in view.rows(table) if not TEST_PATH.search(r["path"])]
    scope = (getattr(view, "options", None) or {}).get("scope")
    return (rows if scope is None else _scoped(rows, scope)), rows


def _group(rows, key):
    groups = {}
    for row in rows:
        groups.setdefault(key(row), []).append(row)
    return groups


def _paths_by(rows, key, value):
    """{key(row): {value(row): set of paths}} in one pass."""
    groups = {}
    for row in rows:
        groups.setdefault(key(row), {}).setdefault(value(row), set()).add(row["path"])
    return groups


def detect_cm2(view, delta, config):
    subjects, pool = _site_pool(view, delta, "factories")
    groups = _group(pool, lambda o: (o["deployable"], o.get("target")))
    found = []
    for site in subjects:
        if _archrules.out_of_time(view):
            break
        same = [o for o in groups.get((site["deployable"], site.get("target")), ()) if o["path"] != site["path"]]
        if not site.get("target") or not same:
            continue
        other = min(same, key=lambda o: o["path"])
        text = "%s:%d creates another %s client for %s; %s:%d already does. Reuse %s." % (
            site["path"], site["line"], site["kind"], site["target"], other["path"], other["line"], other["path"])
        found.append(_archrules.make("CM2", {"path": site["path"], "line": site["line"], "symbol": site["kind"]}, text,
                                     related=[{"path": other["path"], "line": other["line"], "symbol": other["kind"]}],
                                     confidence="high" if site["target"].startswith(("env:", "host:")) else "medium",
                                     key=("%s|%s" % (site["deployable"], site["target"]), "|".join(sorted({site["path"], other["path"]}))),
                                     evidence={"target": site["target"]}))
    return found


def _handler_family(site):
    return (site["kind"], site.get("exception")) if site["kind"] == "rails-rescue" else HANDLER_FAMILY.get(site["kind"])


def detect_cm3(view, delta, config):
    subjects, pool = _site_pool(view, delta, "handlers")
    groups = _group(pool, lambda o: (o["deployable"], _handler_family(o)))
    found = []
    for site in subjects:
        if _archrules.out_of_time(view):
            break
        family = _handler_family(site)
        same = [o for o in groups.get((site["deployable"], family), ()) if o["path"] != site["path"]]
        if not family or not same:
            continue
        other = min(same, key=lambda o: o["path"])
        what = "rescue_from %s" % site["exception"] if site["kind"] == "rails-rescue" else family
        text = "%s:%d registers a second %s; %s:%d already does. The error envelope has one owner, and one place that builds it." % (
            site["path"], site["line"], what, other["path"], other["line"])
        found.append(_archrules.make("CM3", {"path": site["path"], "line": site["line"], "symbol": what}, text,
                                     related=[{"path": other["path"], "line": other["line"], "symbol": what}], confidence="high",
                                     key=("%s|%s" % (site["deployable"], what), "|".join(sorted({site["path"], other["path"]})))))
    return found


def _cm4_counts(styles, site):
    """{style: paths other than the site's} for the site's deployable, empty styles dropped."""
    counts = {style: paths - {site["path"]} for style, paths in styles.items()}
    return {style: paths for style, paths in counts.items() if paths}


def detect_cm4(view, delta, config):
    subjects, pool = _site_pool(view, delta, "pagination")
    by_deployable = _paths_by(pool, lambda o: o["deployable"], lambda o: o["style"])
    found = []
    for site in subjects:
        if _archrules.out_of_time(view):
            break
        counts = _cm4_counts(by_deployable.get(site["deployable"], {}), site)
        total = sum(len(v) for v in counts.values())
        dominant = max(counts, key=lambda s: len(counts[s])) if counts else None
        if not dominant or total < 5 or len(counts[dominant]) < 0.8 * total or site["style"] == dominant:
            continue
        text = "%s:%d paginates with %s; %s covers %d of %d existing uses in this deployable (%s). The pagination contract has one owner." % (
            site["path"], site["line"], site["style"], dominant, len(counts[dominant]), total, ", ".join(sorted(counts[dominant])[:3]))
        found.append(_archrules.make("CM4", {"path": site["path"], "line": site["line"], "symbol": site["style"]}, text,
                                     key=("%s|%s" % (site["deployable"], site["path"]), site["style"]),
                                     evidence={"dominant": dominant, "count": len(counts[dominant]), "total": total}))
    return found


def detect_cm5(view, delta, config):
    subjects, _ = _site_pool(view, delta, "variants")
    found = []
    for site in (s for s in subjects if s["kind"] == "token-code" and not AUTH_QUIET.search(s["path"])):
        packages = view.cached(("deployable-packages", site["deployable"]),
                               lambda d=site["deployable"]: {r["package"] for r in view.select("deps", {"deployable": d}, ["package"])})
        library = next((p for p in ("devise-jwt", "djangorestframework-simplejwt", "pyjwt") if p in packages), None)
        if library:
            text = "%s:%d encodes or decodes tokens by hand while %s is this deployable's auth library." % (site["path"], site["line"], library)
            found.append(_archrules.make("CM5", {"path": site["path"], "line": site["line"], "symbol": site["variant"]}, text,
                                         severity="info", confidence="low", key=(site["path"], library)))
    return found


def detect_mf2(view, delta, config):
    subjects, pool = _site_pool(view, delta, "variants")
    groups = _paths_by(pool, lambda o: (o["deployable"], o["kind"]), lambda o: o["variant"])
    found = []
    for site in (s for s in subjects if s["kind"] != "token-code"):
        if _archrules.out_of_time(view):
            break
        counts = groups.get((site["deployable"], site["kind"]), {})
        dominant = max(counts, key=lambda v: len(counts[v])) if counts else None
        if dominant and site["variant"] != dominant and len(counts.get(site["variant"], ())) <= 1 and len(counts[dominant]) >= 5:
            text = "%s:%d introduces %s %s; %s is used by %d files in this deployable (%s)." % (
                site["path"], site["line"], site["kind"], site["variant"], dominant, len(counts[dominant]), ", ".join(sorted(counts[dominant])[:3]))
            found.append(_archrules.make("MF2", {"path": site["path"], "line": site["line"], "symbol": site["variant"]}, text,
                                         severity="info", confidence="low", key=(site["path"], site["kind"])))
    return found
