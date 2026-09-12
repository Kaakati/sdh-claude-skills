#!/usr/bin/env python3
"""Project-local tool resolution for the orthogonality tool runner (`_archtools.py`, its only importer).

`resolve_formatter` and `unsafe_for_cmd` mirror `auto-format.py`'s `resolve_formatter` and `_unsafe_for_cmd`:
auto-format keeps its own copy until it migrates to this module, so change both together. The order
the runner resolves a project's own binary in:
  * `node_modules/.bin/<tool>` (a `.cmd` shim on Windows), nearest ancestor first
  * `.venv` / `venv` (`Scripts/<tool>.exe` on Windows, `bin/<tool>` elsewhere)
  * `bundle exec <tool>` when the nearest Gemfile.lock pins the gem and `bundle` is on PATH
  * a project binstub, `bin/<tool>`
PATH is consulted only when the caller asks for it.

Nothing here installs, fetches or launches a package runner. `npx`, `pnpm dlx`, `yarn dlx`,
`bunx`, `uvx`, `uv run` and `pipx run` can download a package that is not installed, so a resolved
argv never starts with one (the `toolchain` skill: check whether a tool exists, never install it).

On Windows a `.cmd`/`.bat` shim runs through cmd.exe, whose argument parsing Python cannot escape
for, so `unsafe_for_cmd` refuses an argument carrying a cmd metacharacter.
"""
import os
import re
import shutil

import _hookpaths

CMD_METACHARACTERS = frozenset('%^&|<>"!')
BUNDLED_FORMATTERS = ("rubocop", "htmlbeautifier")
LOCAL_SOURCES = ("node", "venv", "bundle", "bin")


def walk_up(start):
    """`start` and its ancestors, stopping at the repository root."""
    for directory in _hookpaths._ancestors(start):
        yield directory
        if os.path.exists(os.path.join(directory, ".git")):
            return


def nearest(start, candidates):
    """First existing `<ancestor>/<candidate>` file, nearest ancestor first."""
    for directory in walk_up(start):
        for rel in candidates:
            path = os.path.join(directory, rel)
            if os.path.isfile(path):
                return path
    return None


def node_bin(binary, start):
    name = binary + ".cmd" if os.name == "nt" else binary
    return nearest(start, (os.path.join("node_modules", ".bin", name),))


def venv_bin(binary, start):
    tail = ("Scripts", binary + ".exe") if os.name == "nt" else ("bin", binary)
    return nearest(start, tuple(os.path.join(venv, *tail) for venv in (".venv", "venv")))


def bundle_exec(binary, start):
    """(argv, Gemfile dir) for `bundle exec <binary>` when the nearest Gemfile.lock pins it."""
    lock = nearest(start, ("Gemfile.lock",))
    bundle = shutil.which("bundle")
    text = _hookpaths._read_text(lock) if lock else ""
    pinned = lock and re.search(r"^\s+" + re.escape(binary) + r" \(", text, re.M)
    return ([bundle, "exec", binary], os.path.dirname(lock)) if pinned and bundle else None


def binstub(binary, start):
    """(argv, project dir) for `bin/<binary>`: a .cmd/.bat stub or `ruby bin/<binary>` on Windows, an
    executable file elsewhere."""
    if os.name == "nt":
        shim = nearest(start, tuple(os.path.join("bin", binary + ext) for ext in (".cmd", ".bat")))
        if shim:
            return [shim], os.path.dirname(os.path.dirname(shim))
    path = nearest(start, (os.path.join("bin", binary),))
    if not path:
        return None
    if os.name == "nt":
        ruby = shutil.which("ruby")
        return ([ruby, path], os.path.dirname(os.path.dirname(path))) if ruby else None
    return ([path], os.path.dirname(os.path.dirname(path))) if os.access(path, os.X_OK) else None


def _single(found):
    return ([found], None) if found else None


def resolve_local(binary, start, sources=LOCAL_SOURCES):
    """(argv prefix, cwd or None) for the project's own `binary`, trying `sources` in order; or None."""
    finders = {
        "node": lambda: _single(node_bin(binary, start)),
        "venv": lambda: _single(venv_bin(binary, start)),
        "bundle": lambda: bundle_exec(binary, start),
        "bin": lambda: binstub(binary, start),
    }
    for source in sources:
        found = finders[source]() if source in finders else None
        if found:
            return found
    return None


def resolve_tool(binary, start, sources=LOCAL_SOURCES, allow_path=False):
    """`resolve_local`, then PATH only when `allow_path` (standalone binaries: squawk, jscpd, pks)."""
    found = resolve_local(binary, start, sources)
    if found or not allow_path:
        return found
    return _single(shutil.which(binary))


def resolve_formatter(binary, file_path):
    """(argv prefix, bundle dir or None) for the project's own formatter, else PATH's; or None.

    The exact order auto-format has always used: `bundle exec` for rubocop/htmlbeautifier when the
    lockfile pins them, `node_modules/.bin` for prettier, the project venv for ruff, then PATH.
    """
    start = os.path.dirname(os.path.abspath(file_path))
    if binary in BUNDLED_FORMATTERS:
        local = bundle_exec(binary, start)
        if local:
            return local
    finder = {"prettier": node_bin, "ruff": venv_bin}.get(binary)
    found = (finder(binary, start) if finder else None) or shutil.which(binary)
    return ([found], None) if found else None


def unsafe_for_cmd(executable, text):
    """True when Windows would hand `text` to cmd.exe through a shim and it carries a metacharacter."""
    return (os.name == "nt" and str(executable).lower().endswith((".cmd", ".bat"))
            and any(ch in CMD_METACHARACTERS for ch in str(text)))
