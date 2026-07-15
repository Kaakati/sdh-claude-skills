# Claude Code Hooks

Deterministic quality gates that run on every Claude Code action.

## System Requirements

- **Python 3.6+** — all hook logic is in Python
- **Bash** — the `run-python.sh` launcher requires a POSIX shell (Git Bash on Windows)

No other dependencies are required. Optional formatters (rubocop, prettier, black, terraform) are used by `auto-format.py` when available but silently skipped if missing.

## Cross-Platform Architecture

All hooks route through `run-python.sh`, a lightweight launcher that:

1. Tries `python3` first (Linux/macOS default)
2. Falls back to `python` (Windows, conda, pyenv)
3. Validates the found interpreter is Python 3 (skips the broken Windows Microsoft Store stub)
4. Forces UTF-8 I/O via `PYTHONUTF8=1` so non-ASCII output (em dashes, arrows) is emitted
   as valid UTF-8 instead of the legacy Windows codepage (cp1252), which Claude Code would
   otherwise render as `�`
5. Passes through all arguments via `exec` (zero overhead)

This eliminates the `python3` not-found error on Windows and works identically on all platforms.

### Line endings

`run-python.sh` **must** keep LF line endings — under bash, CRLF produces
`bad interpreter: /usr/bin/env bash^M`. The repo's `.gitattributes` pins `*.sh` (and all
text) to `eol=lf`, so every clone gets LF regardless of `core.autocrlf`. Do not re-save the
launcher with CRLF.

## Architecture

### Shared library (`_hooklib.py`)

Every hook imports `_hooklib`, which centralizes event parsing, file reading, path
normalization, the run loops, and framework detection so individual hooks stay small and
consistent. Key helpers:

| Helper | Purpose |
|--------|---------|
| `load_event()` | Parse the hook JSON from stdin; `{}` on any parse error |
| `get_file_path(event)` / `get_content(event)` | Pull `file_path` / write content |
| `read_file(path)` | UTF-8 read, `errors="replace"`, `""` on error |
| `under(path, "app/models")` | Match canonical structure under **any** wrapper dir |
| `detect_framework(path)` | `rails` / `nextjs` / `vite` / `react-native` / `None` via markers |
| `run_post_checker(check)` | Run loop for advisory checkers (`check(event) -> list[str]`) |
| `run_pre_blocker(check, fail_closed=)` | Run loop for PreToolUse gates; `deny()` / `ask()` |

### Advisory dispatcher (`post-edit-dispatch.py`)

The 12 advisory PostToolUse checkers run **in one process** via the dispatcher, which reads
the event once and calls each checker's `check(event)` in-process. This replaces 12 separate
hook entries — ~12 fewer Python cold-starts per edit. Each checker is isolated: a crash in
one is swallowed so it cannot suppress the others. `auto-format.py` stays a separate hook
entry (it mutates files and may invoke slow formatters with their own timeout).

### Wrapper-directory-agnostic detection

Checkers detect frameworks by **canonical internal structure** (`app/models`, `src/pages`,
`src/screens`) and **on-disk markers** (`Gemfile`, `next.config.*`, `vite.config.*`,
`metro.config.js`, `react-native` in `package.json`) — never by a forced top-level folder
name. Rails works under `backend/`, `api/`, or the repo root; a Vite app under `web/`,
`frontend/`, or root; etc. See the root `README.md` → *Project Directory Convention*.

### Fail-closed or fail-open — decided, not defaulted

Every hook eventually crashes (a schema change, a missing binary, malformed input). What happens
**then** is a security property, chosen consciously per hook — never inherited by accident.

| Hook | Stance | Why |
|------|--------|-----|
| `security-scan.py` | **fail-closed** | A gate that cannot evaluate must not pass. An exception in the secret scanner is the strongest possible reason *not* to allow the write. |
| `dangerous-command-blocker.py` | **fail-closed** | Same: an unevaluated destructive command is not a safe one. |
| `pre-commit-check.py` | fail-open | Workflow convention, not safety. A bug here must not block every Bash command. |
| `migration-validator.py` | fail-open (`ask`) | Confirmation gate; the write itself isn't destructive. |
| `deployment-gate.py` | fail-open (`ask`) | Confirmation gate. |
| all 12 advisory checkers | fail-open | *"The linter's crash should cost you a lint report, not a session."* A fail-closed formatter is an outage generator. |
| `audit-logger.py` | fail-open | Logging must never block a tool — but see below. |

**The cost of fail-closed is availability**: a bug in a fail-closed gate on `Edit|Write` bricks all
edits until fixed. That is the correct trade for the small deny tier, and the wrong one everywhere else.

### Silent failure is invisible failure

A fail-open hook that swallows its own exception **looks identical to one that passed** — so a dead
gate can masquerade as a green one for months. Every fail-open path here therefore reports itself:

```
HOOK ERROR: code-quality-checker.py failed to run — ValueError: bad regex.
Its checks did NOT execute, so its rules were not enforced on this edit.
```

- `_hooklib.hook_error(label, exc)` is the single emitter; `run_post_checker` and the dispatcher
  both route through it, naming the failing checker so the message is actionable.
- `audit-logger.py` is the sharpest case: a silent write failure leaves **invisible holes in the
  audit trail plus false confidence that it is complete** — strictly worse than having no trail. It
  announces every gap.
- A healthy hook stays **silent** — the signal must not become noise.

This is enforced by fixture tests (`[fail-open visibility]` in the harness), because a guarantee
that isn't tested is a guarantee that decays.

### Exit-code / decision convention

| Hook type | Mechanism | "allow" | "block / warn" |
|-----------|-----------|---------|----------------|
| PreToolUse gate | `permissionDecision` JSON on stdout, always exit 0 | no JSON | `deny` (block) or `ask` (confirm) |
| PostToolUse checker | stdout lines, always exit 0 | no output | `WARNING: …` lines (advisory) |

**Fail-closed gates:** `security-scan.py` and `dangerous-command-blocker.py` run with
`fail_closed=True` — if the check itself errors, they emit a `deny` rather than silently
allowing the action. Advisory checkers and `ask`-style gates fail open.

## Debug Mode

Set `CLAUDE_HOOKS_DEBUG=1` to see which Python interpreter the launcher selects:

```bash
CLAUDE_HOOKS_DEBUG=1 bash .claude/hooks/run-python.sh .claude/hooks/security-scan.py
# stderr: [run-python] Using: python3 (Python 3.12.1)
```

## Hook Inventory

| Script | Event | Purpose |
|--------|-------|---------|
| `run-python.sh` | — | Cross-platform Python 3 launcher (UTF-8, interpreter discovery) |
| `_hooklib.py` | — | Shared library: event parsing, file IO, framework detection, run loops |
| `security-scan.py` | PreToolUse | Blocks writes to protected files, detects hardcoded secrets (**fail-closed**) |
| `dangerous-command-blocker.py` | PreToolUse | Blocks destructive shell commands (**fail-closed**) |
| `pre-commit-check.py` | PreToolUse | Validates conventional commit format, blocks force pushes |
| `migration-validator.py` | PreToolUse | Validates migration reversibility, SQL injection, destructive ops |
| `deployment-gate.py` | PreToolUse | Requires confirmation for deploys |
| `auto-format.py` | PostToolUse | Auto-formats edited files (rubocop, prettier, black, terraform fmt) |
| `post-edit-dispatch.py` | PostToolUse | Runs all 12 advisory checkers in one process (see below) |
| `audit-logger.py` | PostToolUse | Logs all tool executions for compliance (JSON-lines) |
| `vague-request-detector.py` | UserPromptSubmit | Suggests requirements-consultant for ambiguous inputs |

**Advisory checkers** (dispatched by `post-edit-dispatch.py`, each `check(event) -> list[str]`):
`test-runner`, `code-quality-checker`, `error-handling-checker`, `test-coverage-checker`,
`clean-architecture-checker`, `i18n-checker`, `accessibility-checker`, `api-design-checker`,
`monitoring-checker`, `atomic-design-checker`, `terraform-checker`, `design-token-checker`.

## Optional Formatters

`auto-format.py` uses these formatters when available:

| Extension | Formatter |
|-----------|-----------|
| `.rb`, `.rake` | `rubocop --autocorrect-all` |
| `.js`, `.jsx`, `.ts`, `.tsx`, `.css`, `.scss`, `.json`, `.yaml`, `.yml` | `prettier --write` |
| `.erb` | `htmlbeautifier` |
| `.py` | `black --quiet` |
| `.tf`, `.tfvars` | `terraform fmt` |

## Running Tests

```bash
python .claude/hooks/tests/run-all.py
```

The test harness uses `sys.executable` to invoke hook scripts, so it works regardless of whether your system uses `python` or `python3`.
