# Lint, Typecheck, Build — what each tier actually catches

Load-bearing rules restated (hold even if you read nothing else):

1. **Prettier owns layout; eslint owns correctness.** Overlap them and they fight forever.
2. **`tsc --noEmit` is not optional** — Vite and Next do not typecheck during dev.
3. **`--fix` unattended: only what cannot change behaviour.**

---

## The commands, per stack

```bash
# Rails
bundle exec rubocop                    # lint
bundle exec rubocop -a                 # fix, SAFE only
bundle exec rubocop -A                 # fix incl. UNSAFE — a human runs this and reads the diff
bundle exec erb_lint app/views         # if you lint ERB

# TypeScript (Vite SPA, Next.js, React Native)
pnpm exec prettier --check .           # layout, CI form
pnpm exec prettier --write .           # layout, local form
pnpm exec eslint .                     # correctness
pnpm exec eslint . --fix               # correctness, autofixable subset
pnpm exec tsc --noEmit                 # THE typecheck — no output, just truth

# Terraform
terraform fmt -check -recursive        # layout, CI form
terraform fmt -recursive               # layout, local form
terraform validate                     # syntax + internal consistency (needs `terraform init`)
```

## Decision: which tier owns this complaint?

| The complaint | Owner | Not |
|---|---|---|
| Quote style, line width, trailing commas | **prettier / `rubocop -a` / `fmt`** | eslint |
| Unused variable, `any`, missing `await` | **eslint / rubocop** | prettier |
| "Property does not exist on type" | **`tsc`** | eslint |
| "Undeclared variable in a module" | **`terraform validate`** | `terraform fmt` |
| It only breaks in production | **build + tests** | any linter |

## Bad — prettier and eslint fighting

```json
// .eslintrc.json  ❌
{
  "extends": ["eslint:recommended"],
  "rules": {
    "quotes": ["error", "single"],       // prettier also has an opinion here
    "semi": ["error", "always"],         // ...and here
    "indent": ["error", 2]               // ...and here
  }
}
```

Now `eslint --fix` writes single quotes, prettier rewrites them, and CI flips depending on which
ran last. Every developer learns to distrust both, and someone eventually adds `--no-verify` to
their muscle memory.

## Good — one owner per concern

```js
// eslint.config.js (flat config)  ✅
import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import prettier from 'eslint-config-prettier';

export default [
  js.configs.recommended,
  ...tseslint.configs.recommended,
  // LAST, and this is the whole trick: it TURNS OFF every eslint rule that prettier owns.
  // eslint stops having opinions about layout; prettier stops being second-guessed.
  prettier,
  {
    rules: {
      '@typescript-eslint/no-floating-promises': 'error',   // correctness — prettier cannot see this
      '@typescript-eslint/no-explicit-any': 'error',
    },
  },
];
```

`eslint-config-prettier` must come **last** in the array — it works by disabling rules, so
anything after it re-enables the conflict.

## `--fix` is not free

| Fix | Unattended? | Why |
|---|---|---|
| `prettier --write` | **Yes** | Layout only, deterministic, no semantics |
| `rubocop -a` | **Yes** | *"only when it's safe"* — RuboCop's own guarantee |
| `terraform fmt` | **Yes** | Whitespace and alignment |
| `rubocop -A` | **No** | *"safe and unsafe"*; 53 cops are `SafeAutoCorrect: false` |
| `eslint --fix` | **Careful** | Most rules are layout-ish, but a plugin can autofix logic |

```ruby
# Why -A is a human's call. Lint/BinaryOperatorWithIdenticalOperands is `Safe: false`:
if user.role == user.role   # a real bug — a typo for `user.role == other.role`
```

An unsafe autocorrect "fixes" the symptom by rewriting the expression, and the actual bug — the
wrong operand — is now invisible. That is why this plugin's `auto-format` hook runs `-a`, never
`-A`: it runs unattended, on every write, with its output discarded. Nothing would have told you.

## `tsc --noEmit` — the check everyone omits

**Vite and Next do not typecheck during `dev` or `build`.** They transpile with esbuild/SWC,
which *strip* types without checking them. So a type error can pass local dev, pass the build,
pass a green CI that never ran `tsc`, and reach production having failed nothing.

```jsonc
// package.json  ✅
{
  "scripts": {
    "typecheck": "tsc --noEmit",
    "lint": "eslint .",
    "format:check": "prettier --check .",
    "verify": "pnpm format:check && pnpm lint && pnpm typecheck && pnpm test"
  }
}
```

```jsonc
// tsconfig.json — the settings that make tsc worth running
{
  "compilerOptions": {
    "strict": true,                              // without this, tsc agrees with almost anything
    "noEmit": true,
    "noUncheckedIndexedAccess": true,            // arr[0] is T | undefined — where real crashes live
    "noUnusedLocals": true,
    "skipLibCheck": true                         // do not typecheck node_modules; costs minutes, finds nothing
  }
}
```

`strict: true` is the difference between a typechecker and a formality — `std-reactjs` requires
it for exactly this reason.

## Terraform: `fmt` and `validate` are different questions

```bash
terraform fmt -check -recursive   # is it FORMATTED?      no init needed
terraform init -backend=false     # ...required first, because:
terraform validate                # is it INTERNALLY CONSISTENT? needs providers resolved
```

`validate` without `init` fails on a fresh checkout — the classic red CI on a green repo.
`-backend=false` is what lets CI validate without touching real state.

Neither runs `plan`. **Only `plan` sees reality**; `validate` cannot know your bucket exists.
The three-tier command gate (`terraform-command-gate.py`) governs what happens beyond that.

## CI: order by what fails fastest

```yaml
# ✅ one job, ordered cheap -> expensive. The 3-second failure should not wait on the 4-minute one.
- run: pnpm format:check     # ~3s
- run: pnpm lint             # ~20s
- run: pnpm typecheck        # ~40s
- run: pnpm test             # ~2m
- run: pnpm build            # ~4m
```

**CI must run the same scripts you run.** If CI says `eslint --max-warnings 0` and your script
says `eslint`, they are different checks and you will discover that in a PR, not on your laptop.
One definition, in `package.json` / the Rakefile, called by both.

> Don't gate on formatting in a way that blocks a fix. `--check` in CI is right; a *commit* hook
> that reformats behind your back is how people learn `--no-verify`. Let the editor format on
> save, let CI verify, and keep the two agreeing by pinning the tool
> (`references/preflight.md`).
