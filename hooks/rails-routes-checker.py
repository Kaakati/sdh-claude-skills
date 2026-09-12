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

The false-NEGATIVE trap beside it: the same API-only app must also hand Sidekiq::Web a session
(`Sidekiq::Web.use ActionDispatch::Cookies`, `...Session::CookieStore`) before the dashboard
works at all. That middleware is required and is not authentication, so it must not silence the
warning; neither must `Sidekiq::Web.app_url`, which only sets the dashboard's "Back to App" link.

Returns no warnings for non-matching files.
"""
import os
import re

import _hooklib as hooklib

MOUNT = re.compile(r"^\s*mount\s+Sidekiq::Web\b", re.M)

# Wrappers that constitute authentication in routes.rb itself. `authenticate` is Devise's route
# helper; `constraints` covers a custom constraint class.
ROUTE_GUARD = re.compile(r"^\s*(?:authenticate\b|authenticated\b|constraints\b)")
INLINE_CONSTRAINT = re.compile(r"\bconstraints:\s*\S")
OPENS_BLOCK = re.compile(r"\bdo\s*(?:\|[^|]*\|)?\s*(?:#.*)?$")

# Authentication applied to the Rack app itself, conventionally in an initializer: Basic/Digest
# auth, or any other middleware handed to Sidekiq::Web that is not session plumbing.
INIT_AUTH = re.compile(r"Rack::Auth::(?:Basic|Digest)\b")
WEB_USE = re.compile(r"Sidekiq::Web\.use\s*\(?\s*([\w:]+)")
SESSION_MIDDLEWARE = re.compile(r"Session|Cookies?\b|Flash\b|Rack::Protection|MethodOverride")


def _protects_rack_app(content):
    """True if an initializer's content authenticates the Sidekiq Rack app."""
    if INIT_AUTH.search(content):
        return True
    return any(not SESSION_MIDDLEWARE.search(m.group(1)) for m in WEB_USE.finditer(content))


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
    return any(_protects_rack_app(hooklib.read_file(os.path.join(init_dir, name)))
               for name in names if name.endswith(".rb"))


def _mount_is_guarded(content, match_start):
    """True if the mount carries its own `constraints:`, or sits inside an authenticate/constraints
    block.

    Indentation-based rather than a Ruby parse. Walking up from the mount, only a `do` line
    indented LESS than every enclosing line found so far can contain it, and each one found
    narrows that limit. The earlier walk compared every line with the mount's own indent, so a
    guard block that had already CLOSED above the mount — a sibling, not a parent — counted as
    wrapping it, and an unauthenticated mount passed silently.
    """
    line_start = content.rfind("\n", 0, match_start) + 1
    mount_line = content[line_start:].split("\n", 1)[0]
    if INLINE_CONSTRAINT.search(mount_line):
        return True
    limit = len(mount_line) - len(mount_line.lstrip())
    for line in reversed(content[:line_start].split("\n")):
        indent = len(line) - len(line.lstrip())
        if not line.strip() or indent >= limit or not OPENS_BLOCK.search(line):
            continue
        if ROUTE_GUARD.match(line):
            return True
        limit = indent
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
    if not ("/" + norm).endswith("/config/routes.rb"):
        return []

    content = hooklib.read_file(file_path)
    if not content:
        return []

    return check_sidekiq_web_unauthenticated(content, file_path)


if __name__ == "__main__":
    hooklib.run_post_checker(check)
