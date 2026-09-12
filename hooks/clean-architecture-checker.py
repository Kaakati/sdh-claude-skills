#!/usr/bin/env python3
"""
PostToolUse hook: Clean Architecture layer boundary checker.

Checks source files for layer boundary violations per the `std-clean-architecture` skill.
Exits silently for non-source files.
"""
import os
import re

import _hooklib as hooklib
# IMPORT_OF is the module specifier of an import, whatever its binding form: default
# (`import axios from`), named, namespace (`import * as api from`), type-only
# (`import type { X } from`), side-effect (`import 'x'`), dynamic `import('x')`, and `require('x')`.
# It lives in `_archgraph`, which the orthogonality hooks read too, so the two import readers cannot
# drift apart. The pattern it replaced accepted only `import { ... } from` and the bare forms, so
# `import axios from 'axios'` — and the Next.js mapping guide's own BAD example,
# `import type { ReactNode } from 'react'` — reached neither rule.
from _archgraph import IMPORT_OF


SOURCE_EXTENSIONS = (".rb", ".py", ".ts", ".tsx", ".js", ".jsx")

FRAMEWORK_IMPORT = re.compile(IMPORT_OF + r"(?:react|react-native|next|@next/|vue|angular)")
# `@/src/api/` is the Next.js spelling the mapping guide writes; `../../api/` a nested page's.
API_CLIENT_IMPORT = re.compile(IMPORT_OF + r"(?:axios|(?:\.\.?/)+(?:api|services)/|@/(?:src/)?api/)")
COMMENT_LINE = re.compile(r"^[ \t]*#.*$", re.M)

# Rack's status names (Rack::Utils::SYMBOL_TO_STATUS_CODE), minus the two a domain enum also
# uses (`:accepted`, `:found`). `status: :paid` is an enum write — the house Sidekiq example in
# rails-architect/references/rails-patterns.md does `order.update!(status: :paid)` — and the old
# `status:\s*:\w+` read every state transition as "use case knows about HTTP".
RACK_STATUS = (
    "ok|created|no_content|moved_permanently|see_other|not_modified|bad_request|unauthorized|"
    "payment_required|forbidden|not_found|method_not_allowed|not_acceptable|conflict|gone|"
    "precondition_failed|unprocessable_entity|unprocessable_content|too_many_requests|"
    "internal_server_error|not_implemented|bad_gateway|service_unavailable|gateway_timeout"
)
RB_RESPONSE = re.compile(
    r"\brender\s*\(?\s*(?:json|plain|html|xml|body|js|status|nothing)\s*:|(?<![.\w])head\s*\(?\s*:\w+")
RB_STATUS_VALUE = re.compile(r"\b(?:http_)?status:\s*(?::(?:" + RACK_STATUS + r")\b|[1-5]\d\d\b)")
STATUS_ASSIGN = re.compile(r"\b(?:status|http_status)\s*=\s*\d{3}\b")
# std-fastapi: "HTTPException only in routers; services raise domain exceptions". Django's analog
# is an HttpResponse/JsonResponse built in services.py instead of the view.
PY_HTTP = re.compile(r"\b(?:HTTPException|JSONResponse|JsonResponse|HttpResponse\w*)\b|\bstatus\.HTTP_\d{3}_")

SERVICE_HTTP_WARNING = (
    "WARNING: Service returns HTTP concepts — use case knows about HTTP. "
    "Return Result objects per the `std-clean-architecture` skill."
)
PY_SERVICE_HTTP_WARNING = (
    "WARNING: Service raises or returns HTTP (HTTPException, a JSON/HTTP response, a status "
    "code) — a use case that knows about HTTP cannot run from a Celery task or a script. Raise a "
    "domain exception and let the one app-level exception handler map it, per the `std-fastapi` "
    "skill (Django: the DRF `EXCEPTION_HANDLER`, per the `std-django` skill)."
)


def check_rails_model_imports(content, file_path):
    """Models should not import from controllers or serializers."""
    if not hooklib.under(file_path, "app/models"):
        return []
    warnings = []
    if re.search(r"require.*controllers/", content) or re.search(
        r"require.*serializers/", content
    ):
        warnings.append(
            "WARNING: Model imports controller/serializer — entity depends on "
            "adapter. Move logic to a service per the `std-clean-architecture` skill."
        )
    return warnings


def _is_service(file_path, ext):
    """Rails `app/services`; a Python services package (FastAPI `app/services`, the std-python
    src layout) or a Django app's `services.py`."""
    if ext == ".py":
        return hooklib.under(file_path, "services") or os.path.basename(file_path) == "services.py"
    return hooklib.under(file_path, "app/services")


def _rb_http_concept(code):
    """render/head, an integer status, or `status:` carrying a Rack status as a bare hash key.

    Inside a call's parentheses `status:` is a keyword argument — `update!(status: :created)`,
    `where(status: :not_found)` — which is data, not a response; only at paren depth 0 does it
    build the `{ status: :unprocessable_entity, body: ... }` hash the mapping guide calls a leak."""
    if RB_RESPONSE.search(code) or STATUS_ASSIGN.search(code):
        return True
    return any(code.count("(", 0, m.start()) == code.count(")", 0, m.start())
               for m in RB_STATUS_VALUE.finditer(code))


def check_service_http_concepts(content, file_path):
    """Services should not return HTTP status codes, render, or raise HTTP errors."""
    ext = os.path.splitext(file_path)[1]
    if not _is_service(file_path, ext):
        return []
    code = COMMENT_LINE.sub("", content) if ext in (".rb", ".py") else content
    if ext == ".rb":
        return [SERVICE_HTTP_WARNING] if _rb_http_concept(code) else []
    if ext == ".py":
        return [PY_SERVICE_HTTP_WARNING] if (PY_HTTP.search(code) or STATUS_ASSIGN.search(code)) else []
    return [SERVICE_HTTP_WARNING] if STATUS_ASSIGN.search(code) else []


def check_domain_framework_imports(content, file_path):
    """Domain types should not import framework modules."""
    if not hooklib.under(file_path, "src/domain"):
        return []
    if FRAMEWORK_IMPORT.search(content):
        return [
            "WARNING: Domain type imports framework module — entity depends on "
            "framework per the `std-clean-architecture` skill."
        ]
    return []


def _starts_with_use_client(content):
    """True when the file's first statement, after comments, is the 'use client' directive.

    A loop rather than a regex: `(?:\\s+|//...)*` nests quantifiers and backtracks exponentially
    on a file that opens with a run of blank lines and no directive."""
    text = content.lstrip()
    while text.startswith(("//", "/*")):
        line_comment = text.startswith("//")
        end = text.find("\n") if line_comment else text.find("*/")
        if end < 0:
            return False
        text = text[end + (1 if line_comment else 2):].lstrip()
    return text.startswith(("'use client'", '"use client"'))


def _is_server_component(content, file_path):
    """An App Router file with no 'use client' directive renders on the server — the layer the
    Next.js mapping guide says FETCHES data (its GOOD `app/orders/page.tsx` imports the API module
    directly), and where "use a hook" is impossible. Expo Router keeps client screens in `app/`
    too, so a React Native package is never exempt."""
    if _starts_with_use_client(content):
        return False
    return hooklib.detect_framework(file_path) != "react-native"


def check_screen_direct_api_import(content, file_path, ext):
    """Screens/pages should not import API clients directly."""
    is_page = hooklib.under_any(file_path, ("src/screens", "src/pages"))
    in_app_dir = not is_page and ext in (".tsx", ".jsx") and hooklib.under(file_path, "app")
    if not (is_page or in_app_dir):
        return []
    if in_app_dir and _is_server_component(content, file_path):
        return []
    if not API_CLIENT_IMPORT.search(content):
        return []
    return [
        "WARNING: Screen/page imports API client directly — use a hook as "
        "intermediary per the `std-clean-architecture` skill."
    ]


def check(event):
    file_path = hooklib.get_file_path(event)
    if not file_path:
        return []

    _, ext = os.path.splitext(file_path)
    if ext not in SOURCE_EXTENSIONS:
        return []

    content = hooklib.read_file(file_path)
    if not content:
        return []

    warnings = []
    warnings.extend(check_rails_model_imports(content, file_path))
    warnings.extend(check_service_http_concepts(content, file_path))
    warnings.extend(check_domain_framework_imports(content, file_path))
    warnings.extend(check_screen_direct_api_import(content, file_path, ext))

    return warnings


if __name__ == "__main__":
    hooklib.run_post_checker(check)
