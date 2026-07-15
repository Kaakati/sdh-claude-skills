---
name: toolchain
description: Linters, formatters, type-checkers and compilers for this stack — what runs on what, checking whether a tool is installed before using it, installing one (and why that is your call, not mine), rubocop/eslint/prettier/tsc/terraform, and the format → lint → typecheck → build ladder. Use when a linter is missing or not running, when setting up or fixing lint/format config, when deciding safe vs unsafe autocorrect, when `tsc`/`terraform validate`/`next build` fails, when CI lints differently from a laptop, or when someone asks "install rubocop", "why isn't prettier running", "set up eslint", or "what should CI run".
model: sonnet
---

# Toolchain — format, lint, typecheck, build

Four tiers, and they are not interchangeable. Most toolchain arguments are really people
comparing tools from different tiers.

| Tier | Question | Tools | Can it change behaviour? |
|---|---|---|---|
| **Format** | Does it *look* right? | prettier, `rubocop -a`, black, `terraform fmt` | **No** — layout only |
| **Lint** | Is it *written* right? | eslint, rubocop, `terraform validate` | Only if you let it autofix |
| **Typecheck** | Is it *consistent*? | `tsc --noEmit`, sorbet | No — it only reports |
| **Build** | Does it *compile*? | `next build`, `vite build`, Metro | No — it produces artifacts |

**Format is not lint.** Prettier will never tell you a variable is unused; eslint will never
argue about quote style if prettier owns that. Making them fight is the most common self-inflicted
toolchain wound — see `references/lint-and-typecheck.md`.

## The rule that matters most: safe ≠ unsafe autocorrect

RuboCop's own CLI:

> `-a, --autocorrect` — *"Autocorrect offenses (**only when it's safe**)."*
> `-A, --autocorrect-all` — *"Autocorrect offenses (**safe and unsafe**)."*

RuboCop 1.87's default config marks **53 cops `SafeAutoCorrect: false`** — its maintainers
flagging corrections that **can change what the code does**.

- **Unattended (a hook, a save-action, CI): `-a` only.** This plugin's `auto-format` hook runs
  `--autocorrect` for exactly this reason. A formatter may reshape code; it must never change
  what the code *means* while nobody is reading.
- **`-A` is a human action.** Run it yourself, read the diff, keep what you meant. It is a
  useful tool and a terrible default.

`prettier`, `black`, and `terraform fmt` have no equivalent hazard — they are layout-only by
design, which is why they are safe to run on every write.

## Check before you install — and ask before you install

I check whether a tool exists; **I do not install it for you.**

```bash
command -v rubocop tsc eslint terraform >/dev/null 2>&1 || echo "missing"
```

Installing a toolchain binary is a **machine-level change**: it edits your PATH, your gems, or
your global npm root, and it can quietly diverge you from CI. That is your decision. When
something is missing I will name it, name the install command, and stop.

**Missing tools must never break the work.** This plugin's `auto-format` hook says so once per
session and exits 0 — nothing is blocked because `rubocop` is absent. A toolchain that fails
closed on a fresh laptop is a toolchain people bypass.

## Project-local beats global, always

| | Global (`gem install rubocop`) | **Project-local** |
|---|---|---|
| Version | Whatever you installed, whenever | **Pinned in the manifest** |
| CI parity | Coincidence | Guaranteed |
| New teammate | "works on my machine" | `bundle install` |

```bash
bundle exec rubocop          # the version Gemfile.lock pins
```

**On the JS side, the lockfile tells you the runner — do not guess it.** This repo does not pin a
package manager (CLAUDE.md names none), and the previous version of this block mixed `pnpm exec`
and `npx` on adjacent lines, which are two different managers' runners. Read the lockfile:

| Lockfile present | Runner |
|---|---|
| `package-lock.json` | `npx eslint .` — and this is what `std-infrastructure/references/ci-pipeline.md` currently runs (`npm ci`, `npx tsc --noEmit`, `npm audit`) |
| `pnpm-lock.yaml` | `pnpm exec eslint .` |
| `yarn.lock` | `yarn eslint .` |

Using the wrong one is not cosmetic: `npx` in a pnpm workspace resolves differently, and running
`npm install` in a repo with a `pnpm-lock.yaml` silently creates a second lockfile that CI will not
read. **If the lockfile and CI disagree, that is the finding** — say so rather than picking a side.

**A bare `rubocop`/`eslint` is a different program from `bundle exec rubocop`/`<runner> exec
eslint`** whenever the global version drifts — and it always drifts. This is *pin, don't float*
(`docs/releasing.md`) applied to the tools rather than the dependencies. The one case where the
global binary is unavoidable is an editor/hook integration that cannot see your project's
`bundle`; accept that, and make CI the arbiter.

→ `references/preflight.md`

## The ladder, in order of what catches most per second

Run them in this order locally and in CI, because each tier is slower and catches less than the
one before:

1. **format** — `prettier --check`, `rubocop -a`, `terraform fmt -check`
2. **lint** — `eslint`, `rubocop`, `terraform validate`
3. **typecheck** — `tsc --noEmit` (**the one people skip, and the one that catches real bugs**)
4. **test** — see `../std-testing`
5. **build** — `next build` / `vite build` (also a typecheck, but 10× slower)

`tsc --noEmit` is the highest-value command in this list and the most often missing from CI:
Vite and Next **do not typecheck during dev** (esbuild/SWC strip types without checking them), so
without it type errors reach production having never failed anything.

→ `references/lint-and-typecheck.md`

## CI and your laptop must run the same commands

If CI runs `eslint --max-warnings 0` and you run `eslint`, CI is a different check and you will
learn that at the worst moment. Put the commands in `package.json` scripts / a Rakefile, and have
both call those — never two hand-maintained copies.

Related, owned elsewhere: the auto-format hook's behaviour and the once-per-session missing-tool
notice → `README.md` (Configuration); pinning the plugin itself → `docs/releasing.md`; the
Terraform rule set → `../terraform`.

## Deep guides (read on demand, do not preload)

- Checking what is installed, a doctor script that reports rather than fixes, global-vs-local
  version drift, the `bundle exec`/`pnpm exec` rule, and what to do on a fresh machine
  → `references/preflight.md`
- Per-stack lint/typecheck/build commands, prettier-vs-eslint boundaries, `--fix` semantics and
  what must never be auto-fixed, `tsc --noEmit`, `terraform validate` vs `fmt`, and the CI
  ordering that fails fast → `references/lint-and-typecheck.md`
