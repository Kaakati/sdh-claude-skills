# Monorepo & Large-Codebase Setup

How to run this configuration in a monorepo (many packages) or a large
single-tree codebase, so Claude loads only the conventions and files the current
task touches. Based on [Claude Code: large codebases](https://code.claude.com/docs/en/large-codebases),
adapted to this repo's stack and its **wrapper-directory-agnostic** detection.

## How this config fits the guide

The Claude Code guide describes two ways to scope instructions: per-directory
`CLAUDE.md` files, and **path-scoped rules/skills in a central `.claude/` or plugin**. This
repo uses the central model — all conventions ship as the `sdh` plugin's `std-*` skills that
auto-load by file path. The guide endorses this when "you want all conventions in one
place, or the same rule applies to many scattered paths."

Crucially, the rules and hooks here detect frameworks by **canonical structure
and marker files, not by a forced wrapper name** (see the root `README.md` →
*Project Directory Convention*). So the monorepo layout below is a recommendation,
not a requirement — name your package directories whatever you like.

## 1. Choose where to start Claude

| Start from | File access | CLAUDE.md loaded | Use when |
|------------|-------------|------------------|----------|
| **Repo root** | every file | root + each subdir's on demand | task spans multiple packages |
| **A package dir** | that subtree | that package's + every ancestor's | work scoped to one package |

`.claude/settings.json` loads only from your **starting** directory (it is not
inherited like `CLAUDE.md`). Starting inside a package is the cleanest way to
keep other packages' instructions out of context.

## 2. Layer CLAUDE.md by directory

Keep the repo-root `CLAUDE.md` for repository-wide rules, and add a small
`CLAUDE.md` inside each package for its stack. Ready-to-copy templates:

| Template | Drop into your… |
|----------|------------------|
| `docs/templates/backend.CLAUDE.md` | Rails package (`backend/`, `api/`, `server/`, …) |
| `docs/templates/mobile.CLAUDE.md` | React Native package (`mobile/`, `app/`, …) |
| `docs/templates/web.CLAUDE.md` | Vite SPA package (`web/`, `frontend/`, …) |
| `docs/templates/next.CLAUDE.md` | Next.js package (`next/`, `site/`, …) |
| `docs/templates/shared.CLAUDE.md` | shared TS package (`shared/`, `common/`, …) |

```bash
cp docs/templates/backend.CLAUDE.md  your-api-dir/CLAUDE.md
cp docs/templates/web.CLAUDE.md      your-web-dir/CLAUDE.md
```

Commit them so teammates inherit them; each directory's owner maintains its file.
Starting Claude in `your-api-dir/` then loads that file plus the root `CLAUDE.md`,
with no other package's instructions in context.

## 3. Exclude packages you never touch

Use `claudeMdExcludes` in `.claude/settings.local.json` (personal) or
`.claude/settings.json` (team) to skip CLAUDE.md + rules under packages outside
your area. See `.claude/settings.local.json.template`.

```json
{ "claudeMdExcludes": ["**/legacy/**", "**/packages/admin-*/**"] }
```

## 4. Block reads of generated & vendored code

Already configured in the committed `.claude/settings.json` `permissions.deny`:
`dist/`, `build/`, `.next/`, `coverage/`, `*.generated.*`, `*.min.js/css`,
`vendor/`, Rails `public/assets/` + `public/packs/`, `tmp/cache/`. (`.gitignore`d
paths like `node_modules/` are already excluded from search.) Add machine-specific
ones to `.claude/settings.local.json`.

## 5. Reduce file reads with code intelligence

Install a language-server plugin so Claude jumps to definitions/references
instead of scanning files — valuable as the tree grows:

```shell
/plugin install typescript-lsp@claude-plugins-official   # web, mobile, next, shared
/plugin install ruby-lsp@claude-plugins-official          # backend (if available for your setup)
```

Enable for everyone via the `enabledPlugins` project setting. Each developer needs
the language-server binary on their machine.

## 6. Work across packages

When a task spans packages (e.g. a shared type plus its call sites) and you
started inside one package, grant access to siblings:

```bash
claude --add-dir ../shared            # one-off
```
```json
{ "permissions": { "additionalDirectories": ["../shared", "../web"] } }   # committed/local
```

Note: `additionalDirectories` grants file access only — it does **not** load that
directory's CLAUDE.md/rules/skills. `--add-dir` loads skills, and loads CLAUDE.md
+ rules only with `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD=1`.

## 7. Worktrees for agent teams

This config uses agent teams and worktree isolation heavily (see the
`std-agent-teams` skill). For large repos, scope what each worktree checks
out so they start fast and don't duplicate deps:

- `worktree.symlinkDirectories` — already set in `.claude/settings.json`
  (`node_modules`, `vendor/bundle`) so worktrees symlink instead of copying.
- `worktree.sparsePaths` — set in `.claude/settings.local.json` to the package
  dirs a task needs (always include `.claude`). All worktrees in a session share
  the list, so include every package any teammate needs.

```json
{ "worktree": { "sparsePaths": [".claude", "backend", "shared"] } }
```

## 8. Per-package skills (optional)

Beyond the central skills here, a package can define its own under
`<package>/.claude/skills/<name>/SKILL.md`; they load on demand only when Claude
works in that package. Use a `paths:` frontmatter glob to scope a root-level skill
to certain files wherever they appear.

## 9. How auto-detection helps

- **Rules** auto-load via wrapper-agnostic globs (`**/app/**/*.rb`,
  `**/src/pages/**`, …) regardless of package name.
- **Hooks** detect the framework from markers (`Gemfile`, `next.config.*`,
  `vite.config.*`, `metro.config.js`, `react-native` in `package.json`) so the
  right checks fire under any wrapper.
- The **SessionStart hook** reports which framework area you launched in and which
  rules apply — see `session-start-check.py`.

## Put it together

```text
your-monorepo/
  CLAUDE.md                         # repo-wide rules (this config's root)
  .claude/                          # rules, hooks, skills, agents, settings.json
  api/                              # named anything — detected as Rails via Gemfile
    CLAUDE.md                       # from docs/templates/backend.CLAUDE.md
    Gemfile
    app/  lib/  config/  db/  spec/
  frontend/                         # detected as Vite via vite.config.ts
    CLAUDE.md                       # from docs/templates/web.CLAUDE.md
    vite.config.ts
    src/  tests/
  shared/
    CLAUDE.md                       # from docs/templates/shared.CLAUDE.md
    src/
```

Starting Claude in `api/` loads the root + `api/CLAUDE.md`, auto-loads the Rails
rules for `app/**/*.rb`, runs the Rails hooks, skips build artifacts, and (with
`additionalDirectories`/`sparsePaths`) can reach and worktree `shared/`.
