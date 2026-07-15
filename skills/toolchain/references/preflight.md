# Preflight — is the tool there, and is it the right one?

Load-bearing rules restated (hold even if you read nothing else):

1. **Check, report, stop.** Never install a binary on someone's machine without asking.
2. **`bundle exec` / `pnpm exec` — a bare `rubocop` is a different program.**
3. **A missing tool must not block the work.** Say it once, exit 0.

---

## The two failure modes, and only one looks like a failure

**Missing** is the easy one: the command is not found, you notice immediately, someone installs
it. Annoying, obvious, over in a minute.

**Present but different** is the one that costs a day. Your `rubocop` is 1.60, CI's is 1.87.
Yours passes, CI fails, and the diff is in a cop that did not exist when your version shipped. Or
your global `prettier` is 2.x and the repo's is 3.x, so every file you touch gets reformatted and
your PR is 400 lines of noise nobody can review.

The second is why *"is it installed?"* is the less important half of preflight. **"Is it the same
one CI runs?"** is the question that matters.

## Decision: how do I invoke a tool?

| Situation | Use | Why |
|---|---|---|
| Anything in a repo with a lockfile | **`bundle exec` / `pnpm exec` / `npx`** | The pinned version, the same as CI |
| A hook or editor integration that cannot see the project | the global binary, knowingly | It cannot resolve `bundle`; accept the drift and let CI arbitrate |
| A one-off on a repo you do not own | global | Nothing to pin against |
| CI | **the lockfile's version, always** | CI *is* the arbiter; it must not float |

```bash
# ❌ whatever happens to be on PATH — yours, not the repo's
rubocop app/models/order.rb
eslint src/

# ✅ the version the manifest pins, byte-identical to CI
bundle exec rubocop app/models/order.rb
pnpm exec eslint src/
```

## Checking, without installing

```bash
# ✅ report, do not act. `command -v` is POSIX and works where `which` does not.
for tool in rubocop eslint prettier tsc terraform; do
  if command -v "$tool" >/dev/null 2>&1; then
    printf '  %-10s %s\n' "$tool" "$("$tool" --version 2>&1 | head -1)"
  else
    printf '  %-10s MISSING\n' "$tool"
  fi
done
```

```bash
# ✅ better: what does the PROJECT resolve? This is what CI will run.
bundle exec rubocop --version 2>/dev/null || echo "rubocop not in the bundle"
pnpm exec tsc --version   2>/dev/null || echo "typescript not in the workspace"
```

The second block is the useful one. The first tells you what *you* have; the second tells you
what the *repo* has, which is what actually decides whether CI goes green.

## A doctor script that reports rather than fixes

```bash
#!/usr/bin/env bash
# bin/doctor — run on a fresh machine. Reports; changes nothing.
set -uo pipefail          # NOT -e: we want every check to run, not to stop at the first gap

status=0
need() {                  # need <label> <command...>
  local label="$1"; shift
  if "$@" >/dev/null 2>&1; then
    printf '  ✓ %-22s %s\n' "$label" "$("$@" 2>&1 | head -1)"
  else
    printf '  ✗ %-22s MISSING — %s\n' "$label" "${INSTALL_HINT:-see README}"
    status=1
  fi
}

echo "Toolchain:"
INSTALL_HINT="bundle install"        need "rubocop (bundle)"  bundle exec rubocop --version
INSTALL_HINT="pnpm install"          need "eslint (workspace)" pnpm exec eslint --version
INSTALL_HINT="pnpm install"          need "tsc (workspace)"    pnpm exec tsc --version
INSTALL_HINT="https://developer.hashicorp.com/terraform/install" \
                                     need "terraform"          terraform version

echo "Services:"
INSTALL_HINT="docker compose up -d"  need "postgres"           pg_isready -q
INSTALL_HINT="docker compose up -d"  need "redis"              redis-cli ping

exit $status
```

Two deliberate choices:

- **`set -uo pipefail`, not `-euo`.** With `-e` the script dies at the first missing tool and
  reports one gap; a doctor's whole job is to report *all* of them in one pass, so you install
  once instead of five times.
- **It exits non-zero but fixes nothing.** A doctor that installs things is not a doctor, it is
  an unreviewed setup script running with your privileges.

## Never auto-install

```bash
# ❌ this is a machine-level change nobody approved
command -v rubocop >/dev/null || gem install rubocop
command -v pnpm    >/dev/null || npm install -g pnpm
```

A global install edits PATH, gem, or npm root state that outlives the task, is invisible in the
diff, and **often makes CI parity worse** — you now have a global 1.87 shadowing the bundle's
1.60 in every tool that cannot resolve `bundle exec`. The correct move is always: **name it, name
the install command, stop.**

```bash
# ✅
command -v rubocop >/dev/null || {
  echo "rubocop is not installed. Add it to the Gemfile and run: bundle install"
  echo "(Nothing is blocked — this is a notice.)"
}
```

That is exactly what this plugin's `auto-format` hook does: names the binary, names the install
command, says it **once per session**, exits 0. A toolchain that fails closed on a fresh laptop
is a toolchain people bypass, and a bypassed toolchain checks nothing.

## Fresh machine, in order

1. **Runtimes first** — the versions the repo pins (`.ruby-version`, `.node-version`,
   `.tool-versions`). A version manager (`mise`, `asdf`, `rbenv`+`nvm`) beats system packages:
   the repo tells you the version, so let it.
2. **`bundle install` / `pnpm install`** — this installs the *linters too*, because they belong
   in the manifest. If `rubocop` is not in your `Gemfile`, that is the bug.
3. **`bin/doctor`** — see what is still missing before you start, not at 5pm.
4. **Run the ladder once** (`references/lint-and-typecheck.md`). A repo that does not lint clean
   on a fresh clone has a broken contract, and you want to know that on day one.

## The version file is the source of truth

```
.ruby-version      3.3.6
.node-version      20.18.0
.terraform-version 1.9.8
```

Commit them. They are the only mechanism that makes *"what version should I have?"* answerable
without asking a human — and they are what a version manager reads automatically, which turns the
answer into an action.
