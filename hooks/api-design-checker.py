#!/usr/bin/env python3
"""
PostToolUse hook: API design checker for controller and API route files.

Replaces the agent-based API design hook with a deterministic command hook.
Checks files under backend/app/controllers/, mobile/src/api/, web/src/api/, next/src/actions/
for common API design violations per the `std-api-design` skill.
Exits silently (exit 0, no output) for non-matching files.
"""
import re

import _hooklib as hooklib


# Only check files under these canonical framework-internal directories
# (wrapper-agnostic: matches under backend/, api/, mobile/, web/, next/, root, etc.)
ALLOWED_DIRS = (
    "app/controllers",
    "src/api",
    "src/actions",
)

# Common verbs that should not appear in URL route paths
ROUTE_VERBS = (
    "get", "create", "update", "delete", "remove", "fetch",
    "add", "edit", "list", "find", "search", "post", "put",
)


def check_verbs_in_routes(content):
    """Check for verbs in URL route path definitions."""
    warnings = []
    # Match common route definition patterns:
    # Rails: get '/getUser', resources :createOrders
    # JS/TS: '/api/getUser', '/api/createOrder', router.get('/deleteItem')
    # `[A-Z]` is the ONLY thing distinguishing `/getUser` (a verb in a path) from `/posts`
    # (a plural noun that merely starts with "post"). `re.IGNORECASE` made `[A-Z]` match
    # lowercase too, voiding that discriminator — so `/posts`, `/addresses`, `/listings` and
    # `/editions` were all warned at with "use plural nouns for resources", which they already
    # are. No IGNORECASE here: the uppercase letter IS the signal.
    #
    # The verb must also start a path SEGMENT (after `/`), not appear anywhere in one — else
    # `/user/deleteMe` and `/undeleteUser` are indistinguishable.
    route_pattern = re.compile(
        r"""['"](/(?:[a-zA-Z_][\w-]*/)*("""
        + "|".join(ROUTE_VERBS)
        + r""")[A-Z]\w*)\b"""
    )
    for match in route_pattern.finditer(content):
        path_segment = match.group(1)
        verb = match.group(2)
        warnings.append(
            f"WARNING: Verb '{verb}' in URL path '{path_segment}'. "
            f"Use plural nouns for resources per the `std-api-design` skill."
        )
    return warnings


def check_unwrapped_array_response(content):
    """Check for JSON responses returning arrays not wrapped in a data key."""
    warnings = []
    # Rails: render json: [...] or render json: SomeModel.all
    # Look for render json: followed by array literal
    pattern_rails = re.compile(r"render\s+json:\s*\[")
    if pattern_rails.search(content):
        warnings.append(
            "WARNING: Collection response not wrapped in data key "
            "per the `std-api-design` skill. Use { data: [...] } format."
        )

    # JS/TS: res.json([...]) or return Response.json([...])
    pattern_js = re.compile(r"\.(json|send)\s*\(\s*\[")
    if pattern_js.search(content):
        warnings.append(
            "WARNING: Collection response not wrapped in data key "
            "per the `std-api-design` skill. Use { data: [...] } format."
        )

    return warnings


# The envelope this stack actually commits to — `std-api-design/references/errors-rails.md` and
# `errors-typescript.md` agree, and `std-api-design/SKILL.md:54` states the casing rule outright:
# JSON response keys are camelCase. So the key is `requestId`, never `request_id`.
#
# The old check grepped the rendered block for the SUBSTRING "request_id" and warned
# "missing code/request_id". Three things were wrong with that, and they compounded:
#
# 1. IT NAMED A REMEDY THAT PRODUCES A VIOLATION. The message told you to add `request_id` to an
#    API whose stated convention is camelCase. Ch. 25 — a denial must name a remedy, and this one
#    named the bug.
# 2. IT PASSED CANONICAL CODE ONLY BY LUCK. errors-rails.md writes `requestId: request.request_id`
#    — the substring appears on the VALUE side, via the Rails accessor. Change the value to
#    `requestId: rid` (identical envelope, correct casing) and the hook flagged it. A gate that
#    flags correct code is a gate people learn to ignore — this file's own sibling checks say so.
# 3. IT LOOKED FOR KEYS ANYWHERE IN THE BLOCK. `code` matched `status_code`, `error_code`, and any
#    comment mentioning the word.
#
# Now it matches KEY positions (`requestId:` / `"requestId":`), which is the thing the convention
# is actually about.
KEY_REQUEST_ID = re.compile(r"""(?:\brequestId\s*:|["']requestId["']\s*:)""")
KEY_SNAKE_REQUEST_ID = re.compile(r"""(?:^|[{,\s])(?:request_id\s*:|["']request_id["']\s*:)""", re.M)
KEY_CODE = re.compile(r"""(?:^|[{,\s])(?:code\s*:|["']code["']\s*:)""", re.M)


def check_error_response_format(content):
    """Check rendered error bodies carry `code` and `requestId`, per the canonical envelope.

    Blind spot, stated rather than hidden: this only sees an inline hash literal
    (`render json: { error: ... }`). The canonical helper in errors-rails.md builds `body` and
    calls `render json: body`, which this cannot follow — resolving the variable means parsing
    Ruby, and guessing means false positives. That trade is deliberate: the inline literal is what
    gets written when someone is NOT using the helper, which is exactly the case worth catching.
    """
    warnings = []
    error_render = re.compile(r"render\s+json:\s*\{[^}]*\berror\b[^}]*\}", re.DOTALL)
    for match in error_render.finditer(content):
        block = match.group(0)
        missing = []
        if not KEY_CODE.search(block):
            missing.append("code")
        if not KEY_REQUEST_ID.search(block):
            # Distinguish "absent" from "present but snake_case" — different bug, different fix.
            if KEY_SNAKE_REQUEST_ID.search(block):
                warnings.append(
                    "WARNING: Error response uses `request_id`; JSON response keys are camelCase "
                    "on this stack — use `requestId: request.request_id` per the "
                    "`std-api-design` skill."
                )
                continue
            missing.append("requestId")
        if missing:
            warnings.append(
                f"WARNING: Error response missing {'/'.join(missing)}. The envelope is "
                f"`error`, `code`, `status`, optional `details`, `requestId` per the "
                f"`std-api-design` skill."
            )

    return warnings


def check_post_returns_200(content):
    """Check for POST actions returning 200 instead of 201."""
    warnings = []
    # Rails: in a create action, render ... status: :ok or status: 200
    # Heuristic: look for def create ... render ... status: :ok
    create_pattern = re.compile(
        r"def\s+create\b.*?(?=\bdef\s|\Z)", re.DOTALL
    )
    for match in create_pattern.finditer(content):
        block = match.group(0)
        if re.search(r"status:\s*(:ok|200)\b", block):
            warnings.append(
                "WARNING: POST create action returns 200 instead of 201 "
                "Created per the `std-api-design` skill."
            )

    # JS/TS: router.post with res.status(200) or without explicit status
    post_pattern = re.compile(
        r"\.(post)\s*\([^)]*\)\s*.*?res\.status\(200\)", re.DOTALL
    )
    if post_pattern.search(content):
        warnings.append(
            "WARNING: POST handler returns 200 instead of 201 "
            "Created per the `std-api-design` skill."
        )

    return warnings


def check(event):
    file_path = hooklib.get_file_path(event)

    if not file_path:
        return []

    # Check canonical directory (wrapper-agnostic)
    if not hooklib.under_any(file_path, ALLOWED_DIRS):
        return []

    # Read and analyze file
    content = hooklib.read_file(file_path)
    if not content:
        return []

    warnings = []
    warnings.extend(check_verbs_in_routes(content))
    warnings.extend(check_unwrapped_array_response(content))
    warnings.extend(check_error_response_format(content))
    warnings.extend(check_post_returns_200(content))

    deduped = []
    if warnings:
        seen = set()
        for w in warnings:
            if w not in seen:
                seen.add(w)
                deduped.append(w)

    return deduped


if __name__ == "__main__":
    hooklib.run_post_checker(check)
