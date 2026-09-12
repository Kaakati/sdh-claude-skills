# Adopting on an eroded codebase

Most client codebases already hold duplicates, cycles and second libraries. Reporting all of them
on day one teaches a team to ignore the tool. Blocking all of them stops delivery. The pattern that
works is **record existing, block new**. Shopify rolled packwerk out that way: legacy violations
were recorded while CI blocked new ones. ArchUnit's `FreezingArchRule` does the same.

The same Shopify team later reported the cost: todo lists pile up faster than anyone works them
off. A baseline nobody burns down locks the erosion in. So every baseline here comes with a visible
count, a trend, and dates that expire.

## 1. Build the first baseline and read it

The first complete index build stamps the baseline automatically. It happens at the first session
start after install, or on the first scan. Check it, then read what was frozen:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/hooks/run-python.sh ${CLAUDE_PLUGIN_ROOT}/skills/orthogonality/scripts/arch_index.py --status --require-complete --cache-dir ${CLAUDE_PLUGIN_DATA}/orthogonality
bash ${CLAUDE_PLUGIN_ROOT}/hooks/run-python.sh ${CLAUDE_PLUGIN_ROOT}/skills/orthogonality/scripts/arch_scan.py --format markdown --write-report --cache-dir ${CLAUDE_PLUGIN_DATA}/orthogonality
```

- **An incomplete index** (`--status --require-complete` exits `1`) means a budget or a size cap was
  hit. Check `coverage.truncated`, and add generated or legacy trees to config `ignore` before
  trusting the counts.
- **The markdown report** ends with the frozen table: counts per detector. Those numbers are the
  starting line of the burn-down.
- **`--write-report`** leaves `.claude/orthogonality/last-scan.json` (gitignored) for
  `architecture-advisor` to plan against.

## 2. Declare what you already know

Declarations change what is a finding at all, so they come before triage:

1. **Contexts.** If the team already uses packwerk, import-linter or tach, those declarations are
   read as they are. Otherwise add `contexts` to `.claude/orthogonality.json`
   (`@skills/orthogonality/references/context-maps.md`). Declared contexts turn inferred `info` into
   precise findings, and make legitimate second models in other contexts quiet.
2. **Known exceptions.** A client-mandated library becomes a `house_overrides` entry; a move in
   progress becomes a `migrations` entry with an `until` date; a read model becomes an
   `intentional_duplicates` entry. Each names an ADR
   (`@skills/orthogonality/references/declaring-intent.md`).
3. **Re-stamp once**, with a reason, if the declarations surfaced legacy findings that belong in the
   starting line:

```bash
bash ${CLAUDE_PLUGIN_ROOT}/hooks/run-python.sh ${CLAUDE_PLUGIN_ROOT}/skills/orthogonality/scripts/arch_scan.py --update-baseline --reason "contexts declared in .claude/orthogonality.json" --cache-dir ${CLAUDE_PLUGIN_DATA}/orthogonality
```

## 3. Triage in order of the cost of waiting

| Order | Findings | Why first |
|---|---|---|
| 1 | CM1 second libraries, CM2 second client wrappers | every new import of the second one makes removal more expensive |
| 2 | BC3 cross-context writes, DK3 copied facts | two writers, or two copies, drift with every write |
| 3 | DK1, DK2 duplicate concepts | each new column and association lands in one copy or the other |
| 4 | BC2 cycles, BC1 undeclared dependencies | they block extraction and parallel work, but do not corrupt data |
| 5 | DK6 clones, MF1, MF2 | they cost only when that code next changes |

For each finding, **fix it through its owner skill** (the finding names it), **declare it** with an
ADR, or **leave it frozen** on purpose. Record which one in the ticket.

## 4. Burn it down, visibly

```bash
bash ${CLAUDE_PLUGIN_ROOT}/hooks/run-python.sh ${CLAUDE_PLUGIN_ROOT}/skills/orthogonality/scripts/arch_scan.py --baseline-report --cache-dir ${CLAUDE_PLUGIN_DATA}/orthogonality
```

The baseline report prints the frozen count per detector and its trend across re-stamps.

- **Target: every frozen count falls between releases.** Take one detector family per iteration,
  starting from the triage order above. The whole backlog does not need to go at once.
- **A count that only rises** means `--update-baseline` is being used to make findings disappear.
  Re-stamp only when the ground truth changed (contexts declared, a module extracted), and always
  with a `--reason`, which the report keeps.
- **Put the numbers where the team looks**, in the sprint review or the release notes. A count
  nobody reads is the todo file Shopify never worked off.

## 5. Let declarations expire

- **Give every migration an `until` date** the team believes. When it passes, the finding returns,
  marked `expired`. That is the reminder, not a failure of the process.
- **Extending a date is a decision.** Update the ADR with the new date and the reason, then the entry.
- **Once the old library is gone,** delete the `migrations` entry. A stale entry suppresses nothing,
  but it misleads readers.

## 6. Move CI from reporting to failing

| Stage | CI runs | Move on when |
|---|---|---|
| A. report | `arch_scan.py --changed-since origin/<base> --fail-on never --format markdown` | contexts are declared, and the first triage is done |
| B. fail on new warnings | the two-step job in `@skills/orthogonality/references/scans-and-tools.md`: baseline from the base commit, then `--new-only --fail-on warn` | the job has stayed within its budget for a few weeks |
| C. strict | stage B plus `--strict`, so an incomplete scan or a tool error fails too | — |

- **Never gate on `--fail-on info`.** `info` is advice: name-only matches, inferred contexts, patterns
  still being tuned. Failing a build on a guess teaches people to disable the job.
- **Community boundary tools** join the gate once each has its own baseline (`package_todo.yml`,
  dependency-cruiser known violations). Pin their versions.
- **The hooks never become the gate.** They stay advisory: nothing asks or denies, and any developer
  can switch hooks off. The pull-request check is the fitness function.

## Sources

- Shopify Engineering — Enforcing Modularity in Rails Apps with Packwerk — https://shopify.engineering/enforcing-modularity-rails-apps-packwerk
- Shopify Engineering — A Packwerk Retrospective — https://shopify.engineering/a-packwerk-retrospective
- TNG Technology Consulting — ArchUnit User Guide (`FreezingArchRule`) — https://www.archunit.org/userguide/html/000_Index.html
- Thoughtworks (Paula Paul, Rosemary Wang) — Fitness function-driven development — https://www.thoughtworks.com/en-us/insights/articles/fitness-function-driven-development
- Thoughtworks — Architectural fitness function | Technology Radar — https://www.thoughtworks.com/radar/techniques/architectural-fitness-function
- arXiv / ICPC 2021 (Li, Liang, Soliman, Avgeriou) — Understanding Architecture Erosion: The Practitioners' Perceptive — https://arxiv.org/abs/2103.11392
- arXiv / ICSA 2022 (Li, Soliman, Liang, Avgeriou) — Symptoms of Architecture Erosion in Code Reviews — https://arxiv.org/abs/2201.01184
- Sander Verweij — dependency-cruiser command line interface (known-violations baseline) — https://github.com/sverweij/dependency-cruiser/blob/main/doc/cli.md
- Anthropic — Claude Code docs, Hooks reference: hook locations, allowManagedHooksOnly, disableAllHooks — https://code.claude.com/docs/en/hooks#hook-locations
