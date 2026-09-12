#!/usr/bin/env python3
"""
PostToolUse hook: API design checker for controller and API route files.

Replaces the agent-based API design hook with a deterministic command hook.
Checks files under app/controllers/, src/api/ and src/actions/ (any wrapper directory), Next.js
App Router route handlers (`app/**/route.ts`, `route.js`) — and, for `.py` only, FastAPI routers
under app/routers/ and app/api/ — for common API design violations per the `std-api-design` skill.
Exits silently (exit 0, no output) for non-matching files.
"""
import os
import re

import _hooklib as hooklib


# Canonical framework-internal directories, matched under any wrapper (backend/, api/, root, ...).
ALLOWED_DIRS = ("app/controllers", "src/api", "src/actions")

# FastAPI's boundary dirs — claimed for `.py` ONLY. `app/api` is also where Next.js
# App Router keeps route.ts handlers; gating on extension keeps this a Python
# extension rather than a silent scope change for every Next repo.
PY_ALLOWED_DIRS = ("app/routers", "app/api")

# Next.js App Router route handlers — the TypeScript HTTP endpoints on this stack.
# `std-api-design/references/errors-typescript.md` draws its BAD error body from exactly this file
# (`app/api/orders/route.ts`) and the skill applies the envelope to "every error — from every
# endpoint", yet route handlers were outside every scope above. Keyed on the file NAME the App
# Router requires, so the rest of `app/api/` (helpers, the .py-only FastAPI claim) stays out.
ROUTE_HANDLER_FILES = ("route.ts", "route.js")
POST_HANDLER = re.compile(r"\bexport\s+(?:async\s+)?function\s+POST\b|\bexport\s+const\s+POST\b")

# Common verbs that should not appear in URL route paths
ROUTE_VERBS = (
    "get", "create", "update", "delete", "remove", "fetch",
    "add", "edit", "list", "find", "search", "post", "put",
)

UNWRAPPED_WARNING = (
    "WARNING: Collection response not wrapped in data key "
    "per the `std-api-design` skill. Use { data: [...] } format."
)
POST_200_WARNING = "WARNING: POST {} returns 200 instead of 201 Created per the `std-api-design` skill."


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
    """A collection rendered as a bare array: Rails `render json: [...]`; JS/TS `res.json([...])`,
    `Response.json([...])`, `NextResponse.json([...])`."""
    warnings = []
    if re.search(r"render\s+json:\s*\[", content):
        warnings.append(UNWRAPPED_WARNING)
    if re.search(r"\.(json|send)\s*\(\s*\[", content):
        warnings.append(UNWRAPPED_WARNING)
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
# is actually about — plus the JS shorthand property (`{ error, code, requestId }`), a key with no
# colon that a route handler writes when the variable already has the key's name.
def _key(name):
    return re.compile(r"(?:^|[{,\s])(?:" + name + r"""\s*:|["']""" + name + r"""["']\s*:)"""
                      r"|(?:^|[{,])\s*" + name + r"\s*(?=[,}])", re.M)


KEY_REQUEST_ID = _key("requestId")
KEY_SNAKE_REQUEST_ID = re.compile(r"""(?:^|[{,\s])(?:request_id\s*:|["']request_id["']\s*:)""", re.M)
KEY_CODE = _key("code")
KEY_ERROR = _key("error")

# Where an inline error body starts, per stack. Each ends on the body's opening `{`.
RAILS_RENDER_HASH = re.compile(r"render\s+json:\s*\{")
FASTAPI_RESPONSE_DICT = re.compile(r"JSONResponse\s*\((?:[^()]*?\bcontent\s*=\s*|\s*)\{")
ROUTE_RESPONSE_OBJECT = re.compile(r"\b(?:Response|NextResponse)\.json\s*\(\s*\{")


def _envelope_warnings(block):
    """Missing/miscased envelope keys for one rendered error block (any language —
    the KEY_* patterns match both Ruby symbol keys and quoted dict/object keys)."""
    missing = [] if KEY_CODE.search(block) else ["code"]
    if not KEY_REQUEST_ID.search(block):
        # Distinguish "absent" from "present but snake_case" — different bug, different fix.
        if KEY_SNAKE_REQUEST_ID.search(block):
            return ["WARNING: Error response uses `request_id`; JSON response keys are camelCase "
                    "on this stack — use `requestId: request.request_id` per the "
                    "`std-api-design` skill."]
        missing.append("requestId")
    if not missing:
        return []
    return [f"WARNING: Error response missing {'/'.join(missing)}. The envelope is "
            f"`error`, `code`, `status`, optional `details`, `requestId` per the "
            f"`std-api-design` skill."]


def _literal(text, start, limit=4000):
    """The `{...}` literal opening at text[start], through its matching `}`, skipping strings.
    `[^}]*`, used before, stopped at the first `}` — and the envelope's `details: [{ field }]`
    puts one BEFORE `requestId`, so a complete envelope was reported as missing it."""
    depth, quote = 0, None
    end = min(len(text), start + limit)
    for i in range(start, end):
        ch = text[i]
        if quote:
            quote = None if ch == quote and text[i - 1] != "\\" else quote
        elif ch in "\"'`":
            quote = ch
        elif ch in "{}":
            depth += 1 if ch == "{" else -1
            if depth == 0:
                return text[start:i + 1]
    return text[start:end]


def _error_body_warnings(content, opener):
    """Envelope warnings for every inline body `opener` finds that carries an `error` key."""
    warnings = []
    for match in opener.finditer(content):
        body = _literal(content, match.end() - 1)
        if KEY_ERROR.search(body):
            warnings.extend(_envelope_warnings(body))
    return warnings


def check_error_response_format(content):
    """Check rendered error bodies carry `code` and `requestId`, per the canonical envelope.

    Blind spot, stated rather than hidden: this only sees an inline hash literal
    (`render json: { error: ... }`). The canonical helper in errors-rails.md builds `body` and
    calls `render json: body`, which this cannot follow — resolving the variable means parsing
    Ruby, and guessing means false positives. That trade is deliberate: the inline literal is what
    gets written when someone is NOT using the helper, which is exactly the case worth catching.
    """
    return _error_body_warnings(content, RAILS_RENDER_HASH)


def check_post_returns_200(content):
    """Rails: `def create` ... `status: :ok|200`. Express: `.post(...)` ... `res.status(200)`."""
    warnings = []
    for match in re.finditer(r"def\s+create\b.*?(?=\bdef\s|\Z)", content, re.DOTALL):
        if re.search(r"status:\s*(:ok|200)\b", match.group(0)):
            warnings.append(POST_200_WARNING.format("create action"))
    if re.search(r"\.(post)\s*\([^)]*\)\s*.*?res\.status\(200\)", content, re.DOTALL):
        warnings.append(POST_200_WARNING.format("handler"))
    return warnings


def check_route_handler_error_envelope(content):
    """`Response.json({ error: ... })` / `NextResponse.json(...)` bodies carry the envelope.

    Same helper blind spot as the Rails check: `Response.json(validationErrorBody(...))` — the
    errors-typescript.md GOOD form — is a call, not a literal, and is not read."""
    return _error_body_warnings(content, ROUTE_RESPONSE_OBJECT)


def check_route_handler_post_200(content):
    """An exported POST handler that sets `status: 200`. Only the explicit 200 is flagged: a POST
    returning the default is often no creation at all (a webhook receiver), the same line the
    Rails and Express checks draw."""
    for match in POST_HANDLER.finditer(content):
        following = re.search(r"\bexport\s", content[match.end():])
        body = content[match.end():match.end() + following.start()] if following else content[match.end():]
        if re.search(r"\bstatus\s*:\s*200\b", body):
            return [POST_200_WARNING.format("route handler")]
    return []


def check_fastapi_unwrapped_list(content):
    """`response_model=list[XRead]` serializes a bare JSON array — the house
    collection envelope is `{ data: [...] }` (std-api-design), so list responses
    need a wrapper schema."""
    if re.search(r"response_model\s*=\s*(?:list|List)\s*\[", content):
        return [
            "WARNING: Collection response not wrapped in data key per the "
            "`std-api-design` skill. Use a wrapper schema ({ data: [...] }), not "
            "response_model=list[...]."
        ]
    return []


def check_fastapi_error_envelope(content):
    """Hand-built JSONResponse error bodies bypass the ONE app-level exception handler std-fastapi
    prescribes — when they exist anyway, they must still carry the envelope keys. Same
    inline-literal blind spot as the Rails check, for the same reason."""
    return _error_body_warnings(content, FASTAPI_RESPONSE_DICT)


def check_fastapi_post_default_200(content):
    """FastAPI's `.post()` decorator defaults to 200; creation returns 201 on this stack. The
    decorator window runs to the following `def` so multi-line decorator args are read whole.
    `status.HTTP_200_OK` is the same 200 in FastAPI's named-constant spelling."""
    warnings = []
    for match in re.finditer(
            r"@\w+\.post\s*\((.*?)\n\s*(?:async\s+)?def\s", content, re.DOTALL):
        args = match.group(1)
        if re.search(r"status_code\s*=\s*(?:200\b|status\.HTTP_200_OK\b)", args):
            warnings.append(
                "WARNING: POST route sets status_code=200; creation returns 201 "
                "Created per the `std-api-design` skill."
            )
        elif "status_code" not in args:
            warnings.append(
                "WARNING: POST route without status_code= defaults to 200 — set "
                "status_code=201 for creations per the `std-api-design` skill."
            )
    return warnings


PY_CHECKS = (check_fastapi_unwrapped_list, check_fastapi_error_envelope, check_fastapi_post_default_200)
ROUTE_HANDLER_CHECKS = (check_unwrapped_array_response, check_route_handler_error_envelope,
                        check_route_handler_post_200)
RB_JS_CHECKS = (check_unwrapped_array_response, check_error_response_format, check_post_returns_200)


def checks_for(file_path, ext):
    """The content checks for this file, or None when it is out of scope. FastAPI dirs stay
    .py-only; a Next.js route handler is recognised by its file name instead."""
    if ext == ".py":
        return PY_CHECKS if hooklib.under_any(file_path, PY_ALLOWED_DIRS) else None
    if os.path.basename(file_path) in ROUTE_HANDLER_FILES and hooklib.under(file_path, "app"):
        return ROUTE_HANDLER_CHECKS
    return RB_JS_CHECKS if hooklib.under_any(file_path, ALLOWED_DIRS) else None


def check(event):
    file_path = hooklib.get_file_path(event)
    if not file_path:
        return []
    checks = checks_for(file_path, os.path.splitext(file_path)[1])
    if checks is None:
        return []
    content = hooklib.read_file(file_path)
    if not content:
        return []
    warnings = check_verbs_in_routes(content)
    for run_check in checks:
        warnings.extend(run_check(content))
    return list(dict.fromkeys(warnings))


if __name__ == "__main__":
    hooklib.run_post_checker(check)
