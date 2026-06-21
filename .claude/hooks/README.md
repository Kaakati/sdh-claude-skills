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

## Debug Mode

Set `CLAUDE_HOOKS_DEBUG=1` to see which Python interpreter the launcher selects:

```bash
CLAUDE_HOOKS_DEBUG=1 bash .claude/hooks/run-python.sh .claude/hooks/security-scan.py
# stderr: [run-python] Using: python3 (Python 3.12.1)
```

## Hook Inventory

| Script | Event | Purpose |
|--------|-------|---------|
| `run-python.sh` | — | Cross-platform Python 3 launcher |
| `security-scan.py` | PreToolUse | Blocks writes to protected files, detects hardcoded secrets |
| `dangerous-command-blocker.py` | PreToolUse | Blocks destructive shell commands |
| `pre-commit-check.py` | PreToolUse | Validates conventional commit format, blocks force pushes |
| `migration-validator.py` | PreToolUse | Validates migration reversibility, SQL injection, destructive ops |
| `deployment-gate.py` | PreToolUse | Requires confirmation for deploys |
| `auto-format.py` | PostToolUse | Auto-formats edited files (rubocop, prettier, black, terraform fmt) |
| `test-runner.py` | PostToolUse | Reminds to run tests for modified code |
| `audit-logger.py` | PostToolUse | Logs all tool executions for compliance (JSON-lines) |
| `vague-request-detector.py` | UserPromptSubmit | Suggests requirements-consultant for ambiguous inputs |

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
