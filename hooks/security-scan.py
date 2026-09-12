#!/usr/bin/env python3
"""PreToolUse hook: Security scanner for file edits.

Blocks writes to protected files and detects hardcoded secrets. Fails closed:
if the scan errors, the write is denied rather than silently allowed.

Three tiers, because a fail-closed gate that denies ordinary code gets the plugin disabled:

  DENY  protected files — `.env` / `.envrc` / `.env.*` (templates such as `.env.example` excepted),
        key material (`id_rsa`, `id_ed25519`, `master.key`), and data files inside a `secrets/`,
        `credentials/` or `private/` directory of the project — and provider-format keys found by
        their prefix under any variable name or none: Anthropic, OpenAI, Stripe, GitHub (classic
        and fine-grained), GitLab, Slack, AWS, Google OAuth, npm, private key blocks
  ASK   CI workflow files (they run with repository secrets and a write token); a literal that
        only LOOKS like a credential (quoted, letters and digits, high entropy, assigned to a
        password/secret/token/api_key name); a Google `AIza` key (public by design when restricted)
  ALLOW everything else

What it no longer denies, each a verified false positive on house-documented code:
`const token = useAuthStore.getState().token` and every other identifier after `token =` (the
quote was optional); `password: "Password"` in a locale file and `POSTGRES_PASSWORD: "postgres"` in
Compose (any quoted 8+ characters matched); `web/.env.example` (a substring match on `.env`); a
Terraform `modules/secrets/main.tf` (source code ABOUT secrets); every edit to `.github/workflows/`,
which the house's own devops agent writes; and every write in a repo checked out under a folder
named `private` (the match ran on the absolute path, not the path inside the project).

It scans every tool that writes file content, through `_hooklib.get_file_path` / `get_content`:
Edit, Write, NotebookEdit (`notebook_path`, `new_source`), MultiEdit on releases that still ship
it, and the MCP file writers hooks.json routes here, named by `_hooklib.MCP_FILE_WRITE_MATCHER`
(`path`, or a move's `destination`; `content`, `edits[].newText`). Each `files[]` entry GitHub
`push_files` commits is judged as a write of its own, by its own path.

The protected-file and provider-key tables live in `_protected.py`, shared with the shell gate that
applies them to redirects, `tee` and here-documents (`_protected.shell_write_verdict`): the same
file written through the shell must meet the same decision.
"""

try:
    import _hooklib as hooklib
    import _protected as protected
except Exception as _import_error:  # a fail-closed gate whose library will not load must still deny
    import json
    import sys
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": (
            "BLOCKED: security-scan could not load _hooklib or _protected ({}), so this write was not "
            "scanned. Update or reinstall the sdh plugin, or make the change manually outside Claude "
            "Code.".format(type(_import_error).__name__)),
    }}))
    sys.exit(0)

import collections
import math
import re

CI_WORKFLOW = re.compile(r"(?:^|/)\.github/workflows/[^/]+\.ya?ml$|(?:^|/)\.gitlab-ci\.yml$")
# The registered MCP matcher, shared with mcp-install-gate through `_hooklib`: an anchored list of
# whole tool names. The verb-prefix pattern before it was unanchored ("succeeds on a match anywhere
# in the value"), so a Gmail draft and a memory entity reached this fail-closed gate, which denies
# whenever Python is missing, though neither writes a file.
MCP_WRITE_TOOL = hooklib.MCP_FILE_WRITE_TOOL

GOOGLE_API_KEY = re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")
GENERIC_SECRET = re.compile(
    r"(?i)(?<![A-Za-z0-9_\-])([A-Za-z0-9_\-]*?(?:password|passwd|pwd|secret|token|api[_\-]?key|apikey"
    r"|private[_\-]?key|secret[_\-]?key(?:[_\-]?base)?|access[_\-]?key))[\"']?\s*(?::|=>|=)\s*"
    r"([\"'])((?:(?!\2)[^\n]){8,})\2")
DYNAMIC_VALUE = re.compile(r"\$\{|#\{|<%|\{\{|%\(|process\.env|os\.environ|ENV\[|getenv|\(")
PLACEHOLDER_VALUE = re.compile(
    r"(?i)your[_\- ]|<[^>]*>|x{4,}|\*{3,}|\.{3}|change[_\-]?me|example|placeholder|dummy|redacted|fake|sample")
# Where a credential-shaped literal is the norm, not a leak: locale catalogs ("Password"), docs that
# show the anti-pattern, and test fixtures and seeds (`password: "secret123"`). Provider-format keys
# are still denied everywhere.
NO_GENERIC_SCAN = re.compile(
    r"(?:^|/)(?:locales|i18n|messages|spec|specs|test|tests|__tests__|fixtures|factories|seeds)/"
    r"|\.(?:md|mdx|rst|po|pot)$"
    r"|(?:_spec\.rb|_test\.rb|\.test\.[jt]sx?|\.spec\.[jt]sx?|(?:^|/)test_[^/]*\.py|(?:^|/)conftest\.py"
    r"|(?:^|/)seeds\.rb)$")

CI_REVIEW = (
    "This edits a CI workflow, which runs with repository secrets and a write token. Review it like "
    "production code before approving:\n"
    "- third-party actions pinned to a full commit SHA, not a tag;\n"
    "- a least-privilege `permissions:` block;\n"
    "- no `pull_request_target` job that checks out the PR head;\n"
    "- secrets only through `${{ secrets.* }}`, never echoed or written to a file.\n"
    "Approve if it holds, or reject and tell me what to change (the `std-infrastructure` skill)."
)
GOOGLE_KEY_REVIEW = (
    "A Google API key (`AIza...`) is being written. Firebase and Maps client keys are public by "
    "design, but only when restricted by app, referrer and API; an unrestricted or server key is a "
    "secret. Approve if this is a restricted client key, or reject and I will read it from the "
    "environment instead (the `std-security` skill)."
)


def _entropy(value):
    counts = collections.Counter(value)
    return -sum(count / len(value) * math.log(count / len(value), 2) for count in counts.values())


def _generic_secret(text):
    """The name a credential-shaped literal is assigned to, or None."""
    for match in GENERIC_SECRET.finditer(text):
        value = match.group(3)
        if DYNAMIC_VALUE.search(value) or PLACEHOLDER_VALUE.search(value):
            continue
        if re.search(r"[A-Za-z]", value) and re.search(r"\d", value) and _entropy(value) >= 3.0:
            return match.group(1)
    return None


def _review_concerns(parts, text):
    relative = "/".join(parts)
    concerns = [CI_REVIEW] if CI_WORKFLOW.search(relative) else []
    name = None if NO_GENERIC_SCAN.search(relative) else _generic_secret(text)
    if name:
        concerns.append(
            f"`{name}` is assigned a literal that looks like a credential (quoted, letters and "
            "digits, high entropy). If it is real, read it from the environment or the framework's "
            "encrypted credentials instead (the `std-security` skill); approve only if it is a "
            "fixture or a placeholder."
        )
    if GOOGLE_API_KEY.search(text):
        concerns.append(GOOGLE_KEY_REVIEW)
    return concerns


def _deny_protected(path, reason):
    hooklib.deny(
        f"BLOCKED: '{path}' is a protected file ({reason}). "
        "A person edits protected files outside Claude Code; do not write them another way, shell "
        "redirects included. For a new environment variable, add a placeholder to `.env.example` "
        "instead — see the `std-security` skill."
    )


def _deny_secret(path, label):
    hooklib.deny(
        f"BLOCKED: Potential {label} detected in content being written to '{path}'. "
        "Use environment variables or a secrets manager instead — see the `std-security` skill."
    )


def _denied(path, text, parts):
    """Deny a protected file, then a provider-format key; True when it denied."""
    reason = protected.protected_reason(parts)
    if reason:
        _deny_protected(path, reason)
        return True
    label = protected.provider_secret(text)
    if label:
        _deny_secret(path, label)
        return True
    return False


def check(event):
    tool = hooklib.tool_name(event)
    if tool not in ("Edit", "Write", "MultiEdit", "NotebookEdit") and not MCP_WRITE_TOOL.search(tool):
        return

    # One target, or each `files[]` entry a GitHub `push_files` commits (`get_file_entries`).
    targets = hooklib.get_file_entries(event) or [(hooklib.get_file_path(event), hooklib.get_content(event))]
    judged = [(path, text, protected.project_parts(path, event) if path else []) for path, text in targets]
    if any(_denied(path, text, parts) for path, text, parts in judged):
        return
    concerns = [concern for _path, text, parts in judged for concern in _review_concerns(parts, text)]
    if concerns:
        hooklib.ask("\n\n".join(dict.fromkeys(concerns)))


if __name__ == "__main__":
    hooklib.run_pre_blocker(check, fail_closed=True, gate_label="security-scan")
