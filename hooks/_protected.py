#!/usr/bin/env python3
"""Protected files and provider-format keys: one table, for every gate that enforces it.

`security-scan.py` denies both in Edit/Write/NotebookEdit and MCP writes. The same bytes written
through a shell passed every gate: `printf 'STRIPE_SECRET_KEY=sk_live_...' >> .env`, a
`cat > stripe.rb <<'EOF'` here-document carrying a live key, `echo ... | tee config/master.key`.
mcp-install-gate already reads shell writes for `.mcp.json`, because "gating only the CLI would be a
gate with a door next to it". `shell_write_verdict` judges that door for the shell gate that
already lexes every command, and both gates read the tables below, so the tables cannot drift.

(Not `_secrets.py`: the house floor's `Read(**/*secret*)` deny would hide that name from Claude.)

Stdlib only. `_shell` is imported inside `shell_write_verdict`, so a broken lexer never takes
security-scan's file writes down with it.
"""

import os
import re

from _hookpaths import normalize

ENV_TEMPLATE_SUFFIXES = (".example", ".sample", ".template", ".dist")
KEY_FILE = re.compile(r"^(?:id_(?:rsa|dsa|ecdsa|ed25519)(?:_[\w-]+)?|master\.key|production\.config|deploy\.config)$")
PROTECTED_DIRS = ("secrets", "credentials", "private")
# Source files inside such a directory are code ABOUT secrets (a Terraform module, a rotator
# service, a React route), not secrets; their content is still scanned.
CODE_SUFFIXES = (".rb", ".rake", ".erb", ".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".tf",
                 ".go", ".java", ".kt", ".swift", ".php", ".cs", ".vue", ".svelte", ".css", ".scss",
                 ".md", ".mdx")
ENV_FILE = "an environment file"
KEY_MATERIAL = "key material or deploy config"

PROVIDER_SECRETS = [(re.compile(pattern), label) for pattern, label in (
    (r"\bsk-ant-(?:api|admin)\d{2}-[A-Za-z0-9_\-]{80,}", "Anthropic API key"),
    (r"\bsk-(?:proj|svcacct|admin)-[A-Za-z0-9_\-]{20,}", "OpenAI API key"),
    (r"\bsk-[A-Za-z0-9]{48,}", "OpenAI API key (legacy format)"),
    (r"\b(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{24,}", "Stripe secret key"),
    (r"\bwhsec_[A-Za-z0-9]{32,}", "Stripe webhook signing secret"),
    (r"\bgithub_pat_[A-Za-z0-9_]{60,}", "GitHub fine-grained token"),
    (r"\bgh[pousr]_[A-Za-z0-9_]{36,}", "GitHub token"),
    (r"\bglpat-[A-Za-z0-9_\-]{20,}", "GitLab token"),
    (r"\bxox[abprs]-\d{6,}-[A-Za-z0-9\-]{8,}", "Slack token"),
    (r"https://hooks\.slack\.com/services/T[A-Z0-9]{6,}/B[A-Z0-9]{6,}/[A-Za-z0-9]{20,}", "Slack webhook URL"),
    (r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b", "AWS access key ID"),
    (r"(?i:aws_secret_access_key)[\"']?\s*[:=]\s*[\"']?[A-Za-z0-9/+=]{40}\b", "AWS secret access key"),
    (r"\bGOCSPX-[A-Za-z0-9_\-]{28}\b", "Google OAuth client secret"),
    (r"\bnpm_[A-Za-z0-9]{36}\b", "npm token"),
    (r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED |PGP )?PRIVATE KEY(?: BLOCK)?-----(?:\\n|\s)+[A-Za-z0-9+/=]{40,}",
     "Private key"),
)]


def project_parts(path, event):
    """Lower-cased path segments inside the project (CLAUDE_PROJECT_DIR, else the event cwd);
    the last four segments when the file lies outside both — never the whole absolute path.

    Case folds on EVERY operating system, deliberately unlike `_hooklib.match_path`: a protected
    name is semantic, and a repository travels between NTFS, APFS and ext4 checkouts, so `.ENV` or
    `Secrets/db.yml` gets the same decision on every machine. CODE_SUFFIXES keeps a
    `Private/Route.tsx` component allowed everywhere."""
    norm = normalize(path).lower()
    event = event if isinstance(event, dict) else {}
    for base in (os.environ.get("CLAUDE_PROJECT_DIR"), event.get("cwd")):
        prefix = normalize(base if isinstance(base, str) else "").lower().rstrip("/")
        if prefix and norm.startswith(prefix + "/"):
            return [part for part in norm[len(prefix) + 1:].split("/") if part]
    return [part for part in norm.split("/") if part][-4:]


def protected_reason(parts):
    """ENV_FILE, KEY_MATERIAL, "a data file inside a <dir>/ directory", or None."""
    name = parts[-1] if parts else ""
    if name in (".env", ".envrc") or (name.startswith(".env.") and not name.endswith(ENV_TEMPLATE_SUFFIXES)):
        return ENV_FILE
    if KEY_FILE.match(name):
        return KEY_MATERIAL
    directory = next((part for part in parts[:-1] if part in PROTECTED_DIRS), None)
    if directory and not name.endswith(CODE_SUFFIXES):
        return "a data file inside a {}/ directory".format(directory)
    return None


def provider_secret(text):
    """The label of the first provider-format key in `text`, or None."""
    for pattern, label in PROVIDER_SECRETS:
        for match in pattern.finditer(text):
            if "EXAMPLE" not in match.group(0):  # AWS's documented AKIAIOSFODNN7EXAMPLE
                return label
    return None


# --- The shell door ----------------------------------------------------------------------------

_DISCARDED = ("/dev/null", "/dev/stdout", "/dev/stderr", "$null", "nul")


def shell_write_verdict(command, event):
    """("deny" | "ask", reason) for a shell command that writes a protected file, or writes a
    provider-format key into any file; None otherwise.

    Deny: a provider key in the text a pipeline writes through a redirect or `tee` (a here-document,
    a here-string, echo/printf arguments), whatever the file; a write to an environment file or key
    material, unless it is seeded from a committed template (`cp .env.example .env`, the onboarding
    step). Ask: a data file inside a project's secrets/, credentials/ or private/ directory.
    A command that only USES a key (`gh secret set X --body ...`, a curl header) writes no file."""
    import _shell as shell  # here, not at the top: see the module docstring

    for pipeline in shell.command_pipelines(command or ""):
        verdict = _pipeline_verdict(shell, pipeline, event)
        if verdict:
            return verdict
    return None


def _pipeline_verdict(shell, pipeline, event):
    streamed = [target for target in _stream_targets(shell, pipeline) if target.lower() not in _DISCARDED]
    label = provider_secret("\n".join(_stream_text(shell, pipeline))) if streamed else None
    if label:
        return "deny", (f"BLOCKED [SECRETS]: this command writes a {label} into '{streamed[0]}'. Read it "
                        "from the environment or a secrets manager instead — see the `std-security` skill.")
    for target in shell.written_files(pipeline):
        reason = protected_reason(project_parts(target, event))
        if not reason or (reason == ENV_FILE and _seeded_from_template(shell, pipeline)):
            continue
        if reason in (ENV_FILE, KEY_MATERIAL):
            return "deny", (f"BLOCKED [SECRETS]: this command writes '{target}', a protected file ({reason}). "
                            "A person edits protected files outside Claude Code. For a new environment "
                            "variable, add a placeholder to `.env.example`; to create `.env` from it, run "
                            "`cp .env.example .env` — see the `std-security` skill.")
        return "ask", (f"This command writes '{target}', {reason}. Approve only if it holds no credential "
                       "(a fixture, a public certificate); otherwise keep the value in a secrets manager "
                       "— see the `std-security` skill.")
    return None


def _stream_targets(shell, pipeline):
    """Files a pipeline writes its text into: redirect targets and `tee` operands."""
    targets = [target for segment in pipeline for op, target in segment.redirects
               if op in shell.WRITE_REDIRECTS]
    return targets + [arg for program in shell.programs(pipeline) if program.name == "tee"
                      for arg in program.args if not arg.startswith("-")]


def _stream_text(shell, pipeline):
    """The text a pipeline writes: here-document bodies, here-strings, echo/printf arguments."""
    texts = [body for segment in pipeline for body in segment.heredocs]
    texts += [target for segment in pipeline for op, target in segment.redirects if op == "<<<"]
    return texts + [" ".join(program.args) for program in shell.programs(pipeline)
                    if program.name in ("echo", "printf")]


def _seeded_from_template(shell, pipeline):
    """`cp .env.example .env`, `install .env.sample .env`, `cat .env.example > .env`: every source
    is a committed environment template, so no secret enters the file this way."""
    for program in shell.programs(pipeline):
        operands = [arg for arg in program.args if not arg.startswith("-")]
        sources = operands[:-1] if program.name in ("cp", "install") else operands if program.name == "cat" else []
        if sources and all(_is_env_template(source) for source in sources):
            return True
    return False


def _is_env_template(path):
    name = normalize(path).rsplit("/", 1)[-1].lower()
    return name.startswith(".env") and name.endswith(ENV_TEMPLATE_SUFFIXES)
