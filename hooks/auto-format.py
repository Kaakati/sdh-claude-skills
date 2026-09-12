#!/usr/bin/env python3
"""
PostToolUse hook: Auto-format files after edits.
Reads JSON from stdin, extracts the edited file, runs the appropriate formatter.

A missing formatter is NOT an error — this plugin has to work on day one in a
repo it did not design, where rubocop or prettier may simply not be installed.
But it is not silent either: Ch. 13 says such a hook "should say so once and exit
0, not crash on every write", and Ch. 9 adds that silent failure is invisible
failure. So the first edit of a filetype whose formatter is absent prints one
actionable line naming the binary; every later edit stays quiet.

WHICH binary runs is the project's, not whatever is first on PATH — the `toolchain` skill's
rule that a bare `rubocop` is a different program from `bundle exec rubocop`:
  * prettier               -> the nearest node_modules/.bin (what pnpm exec / npx resolve)
  * rubocop, htmlbeautifier -> `bundle exec` when the nearest Gemfile.lock pins it
  * ruff                   -> the nearest .venv
  * anything unresolved    -> PATH, as before
On Windows those are usually .cmd/.bat shims. CreateProcess appends only .exe to a bare name, so
`subprocess.run(["prettier", ...])` raised FileNotFoundError on every edit; the RESOLVED path is
what runs now. A .cmd/.bat goes through cmd.exe, whose argument parsing Python cannot escape for,
so a file path carrying a cmd metacharacter is refused rather than handed to it.

Never touches files the shadcn CLI owns (components.json `aliases.ui`): they are vendored
upstream source, and reformatting them turns every later `shadcn add --diff` into noise.

Signals post-edit-dispatch through `hooklib.formatter_marker`: matching PostToolUse hooks run in
parallel, and a checker reading the file mid-rewrite would see "" and pass every rule.

Requires no external dependencies beyond Python 3.
"""
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _hooklib as hooklib  # noqa: E402


FORMATTER_MAP = {
    # `-a/--autocorrect` ("only when it's safe"), NOT `-A/--autocorrect-all`
    # ("safe and unsafe"). RuboCop 1.87's own default.yml marks 53 cops
    # `SafeAutoCorrect: false` — its maintainers flag those corrections as able to change
    # behaviour. This hook runs unattended on every write and discards the formatter's output,
    # so `-A` silently applied semantic rewrites to code nobody re-read. A formatter may
    # reshape code; it must not change what the code MEANS. Unsafe corrections are a
    # deliberate human act: run `rubocop -A` yourself and read the diff.
    "rb":    ("rubocop", ["rubocop", "--autocorrect", "--fail-level=error"]),
    "rake":  ("rubocop", ["rubocop", "--autocorrect", "--fail-level=error"]),
    "js":    ("prettier", ["prettier", "--write"]),
    "jsx":   ("prettier", ["prettier", "--write"]),
    "ts":    ("prettier", ["prettier", "--write"]),
    "tsx":   ("prettier", ["prettier", "--write"]),
    "css":   ("prettier", ["prettier", "--write"]),
    "scss":  ("prettier", ["prettier", "--write"]),
    "json":  ("prettier", ["prettier", "--write"]),
    "yaml":  ("prettier", ["prettier", "--write"]),
    "yml":   ("prettier", ["prettier", "--write"]),
    "erb":   ("htmlbeautifier", ["htmlbeautifier"]),
    # `ruff format`, NOT `ruff check --fix`: format is the layout-only, black-compatible
    # half (the house toolchain per std-python); `--fix` applies lint rewrites, which is
    # the deliberate-human-act category this hook must never run unattended.
    "py":    ("ruff", ["ruff", "format", "--quiet"]),
    "tf":    ("terraform", ["terraform", "fmt"]),
    "tfvars": ("terraform", ["terraform", "fmt"]),
}


# How to get each formatter, so the notice names a remedy instead of just a gap.
INSTALL_HINT = {
    "rubocop": "add it to your Gemfile and bundle install, or gem install rubocop",
    "prettier": "add it as a devDependency with the lockfile's package manager, e.g. "
                "pnpm add -D prettier or npm install --save-dev prettier",
    "htmlbeautifier": "add it to your Gemfile and bundle install, or gem install htmlbeautifier",
    "ruff": "uv add --dev ruff (lands in .venv), or uv tool install ruff",
    "terraform": "https://developer.hashicorp.com/terraform/install",
}

BUNDLED = ("rubocop", "htmlbeautifier")
FORMAT_TIMEOUT = 20  # below the 30 s hook timeout, so a hung formatter is reported, not killed silently
CMD_METACHARACTERS = frozenset('%^&|<>"!')


def _walk_up(start):
    """`start` and its ancestors, stopping at the repository root."""
    for directory in hooklib._ancestors(start):
        yield directory
        if os.path.exists(os.path.join(directory, ".git")):
            return


def _nearest(start, candidates):
    """First existing `<ancestor>/<candidate>` file, nearest ancestor first."""
    for directory in _walk_up(start):
        for rel in candidates:
            path = os.path.join(directory, rel)
            if os.path.isfile(path):
                return path
    return None


def _node_bin(binary, start):
    name = binary + ".cmd" if os.name == "nt" else binary
    return _nearest(start, (os.path.join("node_modules", ".bin", name),))


def _venv_bin(binary, start):
    tail = ("Scripts", binary + ".exe") if os.name == "nt" else ("bin", binary)
    return _nearest(start, tuple(os.path.join(venv, *tail) for venv in (".venv", "venv")))


def _bundle_exec(binary, start):
    """(argv, Gemfile dir) for `bundle exec <binary>` when the nearest Gemfile.lock pins it."""
    lock = _nearest(start, ("Gemfile.lock",))
    bundle = shutil.which("bundle")
    pinned = lock and re.search(r"^\s+" + re.escape(binary) + r" \(", hooklib.read_file(lock), re.M)
    return ([bundle, "exec", binary], os.path.dirname(lock)) if pinned and bundle else None


def resolve_formatter(binary, file_path):
    """(argv prefix, bundle dir or None) for the project's own `binary`, else PATH's; or None."""
    start = os.path.dirname(os.path.abspath(file_path))
    if binary in BUNDLED:
        local = _bundle_exec(binary, start)
        if local:
            return local
    found = {"prettier": _node_bin, "ruff": _venv_bin}.get(binary, lambda *_: None)(binary, start)
    found = found or shutil.which(binary)
    return ([found], None) if found else None


def _is_vendored(file_path):
    """True for a shadcn CLI-owned file. A missing or broken helper formats as before."""
    try:
        from _vendored import is_vendored_ui
        return bool(is_vendored_ui(file_path))
    except Exception:
        return False


def _unsafe_for_cmd(executable, file_path):
    """True when Windows would hand this path to cmd.exe and it carries a metacharacter."""
    return (os.name == "nt" and executable.lower().endswith((".cmd", ".bat"))
            and any(ch in CMD_METACHARACTERS for ch in file_path))


def _set_marker(marker, state):
    """Tell post-edit-dispatch whether this edit's file is still being rewritten.

    Best effort by design: an unwritable marker costs the dispatcher its ordering (it stops
    waiting after its grace period), never an edit.
    """
    if not marker:
        return
    try:
        os.makedirs(os.path.dirname(marker), exist_ok=True)
        with open(marker, "w", encoding="utf-8") as handle:
            handle.write(state)
    except OSError:
        pass


def _run(event, binary, argv, bundle_dir):
    env = dict(os.environ, BUNDLE_GEMFILE=os.path.join(bundle_dir, "Gemfile")) if bundle_dir else None
    try:
        result = subprocess.run(argv, cwd=bundle_dir, env=env, stdin=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                timeout=FORMAT_TIMEOUT)
    except subprocess.TimeoutExpired:
        hooklib.notice_once(event, f"formatter-timeout-{binary}",
                            f"sdh: `{binary}` did not finish within {FORMAT_TIMEOUT}s and was stopped; "
                            "check the file it was formatting. Nothing is blocked. "
                            "This notice appears once per session.")
        return
    except Exception as exc:
        # A formatter exiting non-zero is normal (unfixable offenses) and does not land
        # here. This is the formatter failing to RUN — swallowing that silently would
        # leave the user watching formatting quietly never happen.
        hooklib.notice_once(event, f"formatter-failed-{binary}",
                            f"sdh: `{binary}` could not be run — {type(exc).__name__}: {exc}. "
                            "Files are not being auto-formatted. Nothing is blocked. "
                            "This notice appears once per session.")
        return
    if result.returncode >= 2:
        _notice_exit(event, binary, result)


def _notice_exit(event, binary, result):
    """Exit >= 2 is a formatter that did not format (RuboCop: config/load error), not an offense."""
    first = (result.stderr or b"").decode("utf-8", "replace").strip().splitlines()[:1]
    detail = first[0][:200] if first else "no error output"
    hooklib.notice_once(event, f"formatter-exit-{binary}",
                        f"sdh: `{binary}` exited {result.returncode} ({detail}), so the file was not "
                        "formatted: a configuration or load error, or a file it could not parse. "
                        "Run it by hand to see the full error. Nothing is blocked. "
                        "This notice appears once per session.")


def format_file(event, file_path, ext):
    """Run the project's formatter for `ext` on `file_path`, announcing each failure kind once."""
    if _is_vendored(file_path):
        return
    binary, command = FORMATTER_MAP[ext]
    resolved = resolve_formatter(binary, file_path)
    if resolved is None:
        # Say so once per session, then never again for this formatter.
        hooklib.notice_once(event, f"missing-formatter-{binary}",
                            f"sdh: `{binary}` is not on PATH (and not pinned in this project), so "
                            f".{ext} files will not be auto-formatted this session. Install it "
                            f"({INSTALL_HINT.get(binary, binary)}), or ignore this — nothing is "
                            "blocked either way. This notice appears once per session.")
        return
    prefix, bundle_dir = resolved
    if _unsafe_for_cmd(prefix[0], file_path):
        hooklib.notice_once(event, f"formatter-unsafe-path-{binary}",
                            f"sdh: skipped `{binary}` on '{os.path.basename(file_path)}': it runs "
                            "through a .cmd/.bat shim here, and cmd.exe would read a character in "
                            "that path (% ^ & | < > \" !) as shell syntax. Format it by hand. "
                            "Nothing is blocked. This notice appears once per session.")
        return
    _run(event, binary, prefix + command[1:] + [file_path], bundle_dir)


def main():
    event = hooklib.load_event()
    file_path = hooklib.get_file_path(event)
    ext = os.path.splitext(file_path)[1].lstrip(".")
    if not file_path or ext not in FORMATTER_MAP or not os.path.isfile(file_path):
        sys.exit(0)
    marker = hooklib.formatter_marker(event)
    _set_marker(marker, "running")
    try:
        format_file(event, file_path, ext)
    finally:
        _set_marker(marker, "done")
    sys.exit(0)


if __name__ == "__main__":
    main()
