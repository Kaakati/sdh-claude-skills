#!/usr/bin/env python3
"""Dependency edges and cycles for the orthogonality detectors.

  * `IMPORT_OF`: the module-specifier prefix regex, moved here from clean-architecture-checker.py
    so both hooks read one pattern (default, named, namespace, type-only, side-effect, dynamic
    `import()` and `require()` forms).
  * Resolution candidates per language, checked by the caller against the index's file set:
    Python dotted modules (absolute and relative) under each deployable and its `src/`; TS/JS
    relative specifiers and tsconfig `paths` aliases (through `_vendored`'s JSONC reader, one
    `extends` hop), with the `@/` convention; Ruby constants from the innermost lexical scope out.
    Package-name imports (npm, PyPI, gems) are external and never resolved.
  * `strongly_connected`: iterative Tarjan, so a 10k-node chain cannot hit the recursion limit.
"""
import os
import posixpath

import _vendored

IMPORT_OF = r"""(?:\bimport\s+(?:type\s+)?[\w*{}\s,$]{1,400}?\s+from\s*|\b(?:import|require)\s*\(?\s*)['"]"""
JS_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")
_TS_CACHE = {}


class _Tarjan(object):
    def __init__(self, adjacency):
        self.adjacency, self.counter = adjacency, 0
        self.index, self.low, self.on_stack, self.stack, self.components = {}, {}, set(), [], []

    def _open(self, node, work):
        self.index[node] = self.low[node] = self.counter
        self.counter += 1
        self.stack.append(node)
        self.on_stack.add(node)
        work.append((node, iter(sorted(self.adjacency.get(node, ())))))

    def _advance(self, node, children, work):
        """True when a child was opened (the walk descends); lowlinks update on the way."""
        for child in children:
            if child not in self.index:
                self._open(child, work)
                return True
            if child in self.on_stack:
                self.low[node] = min(self.low[node], self.index[child])
        return False

    def _close(self, node, work):
        work.pop()
        if work:
            parent = work[-1][0]
            self.low[parent] = min(self.low[parent], self.low[node])
        if self.low[node] == self.index[node]:
            component = []
            while True:
                member = self.stack.pop()
                self.on_stack.discard(member)
                component.append(member)
                if member == node:
                    break
            self.components.append(sorted(component))

    def run(self):
        nodes = set(self.adjacency) | {c for children in self.adjacency.values() for c in children}
        for root in sorted(nodes):
            if root in self.index:
                continue
            work = []
            self._open(root, work)
            while work:
                node, children = work[-1]
                if not self._advance(node, children, work):
                    self._close(node, work)
        return self.components


def strongly_connected(adjacency):
    """Every strongly connected component of {node: iterable of nodes}, each sorted."""
    return _Tarjan({k: set(v) for k, v in adjacency.items()}).run()


def cycles(adjacency):
    """Components that are real cycles: two or more nodes, or one node with a self-loop."""
    return [c for c in strongly_connected(adjacency) if len(c) > 1 or c[0] in adjacency.get(c[0], ())]


def cycle_order(adjacency, members, start):
    """[start, ..., start]: one closed walk through the component, found breadth-first."""
    allowed = set(members)
    for first in sorted(n for n in adjacency.get(start, ()) if n in allowed):
        found = _walk_back(adjacency, allowed, start, first)
        if found:
            return found
    return [start, start]


def _walk_back(adjacency, allowed, start, first):
    previous, queue = {first: start}, [first]
    while queue:
        node = queue.pop(0)
        if node == start:
            return _unwind(previous, start)
        for child in sorted(c for c in adjacency.get(node, ()) if c in allowed and c not in previous):
            previous[child] = node
            queue.append(child)
    return None


def _unwind(previous, start):
    path, node = [start], previous[start]
    while node != start:
        path.append(node)
        node = previous[node]
    path.append(start)
    return list(reversed(path))


def python_source_roots(deployable):
    base = "" if deployable in ("", ".") else deployable
    return [r for r in (base, posixpath.join(base, "src") if base else "src", "") if r is not None]


def _module_of(rel, roots):
    for root in roots:
        prefix = root + "/" if root else ""
        if rel.startswith(prefix) and rel.endswith(".py"):
            module = rel[len(prefix):-3].replace("/", ".")
            return module[:-9] if module.endswith(".__init__") else module
    return None


def python_candidates(symbol, src_rel, deployable):
    """Project-relative .py paths an import symbol (`a.b`, `a.b:name`, `..c:name`) may name."""
    roots = python_source_roots(deployable)
    module, _, name = symbol.partition(":")
    level = len(module) - len(module.lstrip("."))
    module = module.lstrip(".")
    if level:
        own = _module_of(src_rel, roots) or ""
        package = own.split(".")[:-level] if not src_rel.endswith("__init__.py") else own.split(".")[:len(own.split(".")) - level + 1]
        module = ".".join([p for p in package if p] + ([module] if module else []))
    dotted_names = ([module + "." + name] if name and module else [name] if name else []) + ([module] if module else [])
    paths = []
    for dotted_name in dotted_names:
        tail = dotted_name.replace(".", "/")
        for root in roots:
            base = posixpath.join(root, tail) if root else tail
            paths.extend([base + ".py", base + "/__init__.py"])
    return paths


def ruby_candidates(symbol, scope):
    """Fully qualified constant names to try, innermost lexical scope first."""
    if symbol.startswith("::"):
        return [symbol[2:]]
    parts = [p for p in (scope or "").split("::") if p]
    names = ["::".join(parts[:i] + [symbol]) for i in range(len(parts), 0, -1)]
    return names + [symbol]


def _ts_paths(root, package_rel):
    key = (root, package_rel)
    if key not in _TS_CACHE:
        package_abs = os.path.join(root, package_rel) if package_rel not in ("", ".") else root
        found = (None, None)
        for name in ("tsconfig.json", "tsconfig.app.json", "jsconfig.json"):
            found = _vendored._ts_paths(os.path.join(package_abs, name), hops=1)
            if found[0]:
                break
        _TS_CACHE[key] = (found, package_abs)
    return _TS_CACHE[key]


def _to_rel(root, absolute):
    rel = os.path.relpath(os.path.normpath(absolute), root).replace("\\", "/")
    return None if rel.startswith("..") else rel


def js_candidates(spec, src_rel, root, package_rel):
    """Project-relative files a TS/JS specifier may resolve to; [] for a package import."""
    if spec.startswith((".", "/")):
        base = posixpath.normpath(posixpath.join(posixpath.dirname(src_rel), spec))
    else:
        (paths, base_dir), package_abs = _ts_paths(root, package_rel)
        hit = _vendored._match_mapping(paths, spec, base_dir) if paths else None
        if not hit and spec.startswith(("@/", "~/")):
            src = os.path.join(package_abs, "src")
            hit = os.path.join(src if os.path.isdir(src) else package_abs, spec[2:])
        base = _to_rel(root, hit) if hit else None
    if not base:
        return []
    stem = base[:-3] if base.endswith(".js") else base
    return [base] + [stem + ext for ext in JS_EXTENSIONS] + [base + "/index" + ext for ext in JS_EXTENSIONS]


def resolve_first(candidates, exists):
    """The first candidate `exists` accepts (a set or a callable returning a set), else None."""
    present = exists(candidates) if callable(exists) else exists
    for candidate in candidates:
        if candidate in present:
            return candidate
    return None


def context_adjacency(edges):
    """{src_context: set(dst_context)} from (src, dst) pairs, self-edges dropped."""
    adjacency = {}
    for src, dst in edges:
        if src and dst and src != dst:
            adjacency.setdefault(src, set()).add(dst)
    return adjacency
