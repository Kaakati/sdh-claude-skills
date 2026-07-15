#!/usr/bin/env python3
"""PostToolUse hook: Rails routing security checks.

Currently one check, because only one thing in `config/routes.rb` is both silently
catastrophic and mechanically decidable: mounting `Sidekiq::Web` with no authentication.

`mount Sidekiq::Web => '/sidekiq'` with nothing wrapping it exposes every job's **arguments** —
which on this stack routinely carry user ids, emails and tokens — and lets any visitor retry or
kill jobs. It is a two-line mistake with no error message, and this repo commits to Sidekiq
(CLAUDE.md: Redis + Sidekiq queues), so it is reachable by construction.

Why a hook rather than a line in the security-auditor agent: Ch. 7's placement test. This must
hold whether or not anybody runs an audit, so it is not context.

The false-positive trap this check exists to avoid: the idiomatic protection for an API-only app
does NOT live in routes.rb. `Sidekiq::Web.use Rack::Auth::Basic` goes in
`config/initializers/sidekiq.rb`, so a routes.rb-only check would flag correctly-secured apps —
a gate that flags correct code is a gate people learn to ignore. So the initializers are read
from disk before warning.

Returns no warnings for non-matching files.
"""
import os
import re

import _hooklib as hooklib

MOUNT = re.compile(r"^\s*mount\s+Sidekiq::Web\b", re.M)

# Wrappers that constitute authentication in routes.rb itself. `authenticate` is Devise's route
# helper; `constraints` covers a custom constraint class.
ROUTE_GUARD = re.compile(r"^\s*(?:authenticate\b|authenticated\b|constraints\b)", re.M)

# Protection applied to the Rack app itself, conventionally in an initializer.
INIT_GUARD = re.compile(
    r"Sidekiq::Web\.use\b|Rack::Auth::Basic|Sidekiq::Web\.app_url|"
    r"Sidekiq::Web\.set\s*\(?\s*:session_secret",
)


def _initializers_guard_it(routes_path):
    """True if a sibling initializer protects the Rack app.

    Walks up from config/routes.rb to the Rails root, then reads config/initializers/*.rb.
    Returning True on an unreadable tree is deliberate: silence beats a false accusation.
    """
    d = os.path.dirname(os.path.abspath(routes_path))
    # config/routes.rb -> config/ -> <rails root>
    root = os.path.dirname(d)
    init_dir = os.path.join(root, "config", "initializers")
    if not os.path.isdir(init_dir):
        return False
    try:
        names = os.listdir(init_dir)
    except OSError:
        return True  # cannot tell; do not accuse
    for name in names:
        if not name.endswith(".rb"):
            continue
        content = hooklib.read_file(os.path.join(init_dir, name))
        if content and INIT_GUARD.search(content):
            return True
    return False


def _mount_is_guarded(content, match_start):
    """True if the mount sits inside an authenticate/constraints block.

    Indentation-based rather than a Ruby parse: a guarded mount is nested inside a `do` block, so
    it is indented under a guard line that appears above it.
    """
    before = content[:match_start]
    lines = before.split("\n")
    mount_line = content[match_start:].split("\n")[0]
    mount_indent = len(mount_line) - len(mount_line.lstrip())
    if mount_indent == 0:
        return False  # top-level mount cannot be inside a block
    for line in reversed(lines):
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        if indent < mount_indent and ROUTE_GUARD.match(line) and line.rstrip().endswith("do"):
            return True
        if indent == 0 and line.strip().startswith("end"):
            return False
    return False


def check_sidekiq_web_unauthenticated(content, file_path):
    warnings = []
    for m in MOUNT.finditer(content):
        if _mount_is_guarded(content, m.start()):
            continue
        if _initializers_guard_it(file_path):
            continue
        warnings.append(
            "WARNING: `Sidekiq::Web` is mounted with no authentication. It exposes every job's "
            "arguments (user ids, emails, tokens) and lets any visitor retry or kill jobs. "
            "Wrap the mount in an `authenticate`/`constraints` block, or protect the Rack app "
            "with `Sidekiq::Web.use Rack::Auth::Basic` in `config/initializers/sidekiq.rb`. "
            "Note: Devise's `authenticate` route helper needs Warden session middleware, which "
            "an API-only Rails app does not load by default — see the `std-security` skill."
        )
        break  # one warning is enough
    return warnings


def check(event):
    file_path = hooklib.get_file_path(event)
    if not file_path:
        return []

    norm = hooklib.normalize(file_path)
    if not norm.endswith("config/routes.rb"):
        return []

    content = hooklib.read_file(file_path)
    if not content:
        return []

    return check_sidekiq_web_unauthenticated(content, file_path)


if __name__ == "__main__":
    hooklib.run_post_checker(check)
