# Diagnosing Misplaced Components

Platform-neutral. Read this when the hierarchy already exists and something feels wrong — a
component is hard to reuse, a directory keeps growing, an import goes the wrong way. Each entry is
a symptom, its diagnosis, and the fix.

The load-bearing constraints these all trace back to:

- Atoms are indivisible and import nothing from the design system.
- Molecules import only atoms and serve one cohesive function.
- Organisms are the lowest level allowed to fetch data or read global state.
- Templates define layout via slots and hold no real content.
- Pages are route entry points that fill templates with real data.

## Triage table

| Symptom | Diagnosis | Fix |
|---------|-----------|-----|
| An `atoms/` file imports from `atoms/` | Atom composing atoms | Move it to `molecules/` |
| A molecule calls `useQuery` / queries the DB | Data-awareness below the boundary | Hoist the fetch to the organism or page |
| An organism renders sidebars + header + grid | Organism doing layout | Extract the layout into a template |
| A template renders literal text or metrics | Template with hardcoded content | Replace content with slots |
| Every page rebuilds the same wrapper markup | Pages reimplementing layout | Extract the wrapper into a template |
| `AtomButton.tsx`, `OrganismHeader.tsx` | Level in the name | Drop the prefix; the directory says the level |
| A page composes atoms directly | Skipping levels | Consider extracting organisms + a template |
| An atom has 15 props | Prop explosion | Split the atom, or push variation up to the molecule |

---

## Symptom: an atom imports another atom

An `IconButton` living in `atoms/` that imports `Icon` and `Button`.

It composes two atoms, so by definition it is not indivisible — it is a molecule wearing an atom's
directory. Move `IconButton` to `molecules/` and update its imports. The rule
`atom-standalone-primitives` has the bad/good pair on every platform.

## Symptom: a molecule fetches its own data

A `UserCard` molecule calling `useQuery` to load the user it displays.

Molecules must be reusable in any context, and a molecule that fetches cannot be reused with data
you already have. Give the molecule display-ready props (`name`, `avatarUrl`, `role`) and move the
fetch up to the organism or the page that renders it. See `organism-data-awareness`.

## Symptom: an organism defines full-page structure

An organism that renders the page grid — header slot, sidebar, main column, footer.

Organisms are *sections within* a layout, not the layout. Extract the spatial structure into a
template with slots; the organism becomes one of the things the page drops into a slot. See
`template-layout-skeleton`.

## Symptom: a template renders real content

A `DashboardLayout` that renders `<h1>Dashboard</h1>` and a specific set of metrics.

Then it is only usable for the dashboard, which defeats the point of a template. Replace hardcoded
content with slots (`children`, `header`, `sidebar`) and let pages fill them. See
`template-layout-skeleton`.

## Symptom: every page rebuilds the same wrapper

Each page manually writes `<div className="min-h-screen"><header>…</header><main>…</main></div>`.

The repetition *is* the template you have not extracted yet. Pull the shared wrapper into a
template and use it across the pages. See `page-template-instance`.

## Symptom: the level is in the component name

`AtomButton.tsx`, `MoleculeSearchForm.tsx`, `OrganismHeader.tsx`.

The directory already encodes the level, so the prefix is noise — and it goes stale the moment the
component is promoted. Name components by what they are: `Button.tsx`, `SearchForm.tsx`,
`Header.tsx`. See `org-naming-conventions` for the full anti-pattern list.

## Symptom: a page composes atoms directly, skipping levels

A page that reaches past templates and organisms straight into atoms.

This is not strictly forbidden — a genuinely trivial page may not need an organism. But it is a
signal: the hierarchy exists to promote reuse, and a page assembling atoms by hand is usually
hiding an organism that a second page will want later.

```tsx
// SMELL: the page hand-assembles what should be a reusable section
export function DashboardPage() {
  const { data } = useQuery({ queryKey: ["metrics"], queryFn: fetchMetrics });

  return (
    <div>
      <Heading level={2}>Overview</Heading>
      <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {data?.map((m) => (
          <div key={m.id} className="rounded-lg border p-4">
            <Text size="sm" color="muted">{m.label}</Text>
            <Text weight="bold">{m.formattedValue}</Text>
          </div>
        ))}
      </div>
    </div>
  );
}
```

```tsx
// BETTER: the section is an organism the page (and any other page) can reuse
export function DashboardPage() {
  return (
    <DashboardLayout header={<Header />}>
      <Heading level={1}>Dashboard</Heading>
      <MetricsGrid />
    </DashboardLayout>
  );
}
```

Ask before extracting: would a second page want this section? If yes, it is an organism today.

## Symptom: an atom has too many props

An atom with fifteen props covering every possible variation.

Atoms stay minimal. A prop list that long means one of two things, and they have different fixes:

```tsx
// BAD: one atom absorbing every variation any caller ever needed
interface ButtonProps {
  label: string;
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  leadingIcon?: IconName;      // -> composition, not configuration
  trailingIcon?: IconName;     // -> composition, not configuration
  badgeCount?: number;         // -> composition, not configuration
  tooltip?: string;            // -> a different component's job
  href?: string;               // -> this is a Link, not a Button
  loading?: boolean;
  fullWidth?: boolean;
  rounded?: boolean;
  elevated?: boolean;
  // ...
}
```

```tsx
// GOOD: the atom keeps the variation that is genuinely styling
interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  label: string;
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
}

// Composition moves up a level: IconButton is a molecule (Icon + Button),
// and `href` belongs to a separate Link atom, not to Button.
```

The two fixes:

1. **Split the atom** when the props describe different components hiding in one (`href` means you
   want a `Link`).
2. **Push the variation up** when the props describe composition (`leadingIcon`, `badgeCount`) —
   that belongs to the consuming molecule, not the atom.

See `atom-standalone-primitives` for what atoms can and cannot do, and `atom-theming-tokens` for
which variation should be a token rather than a prop at all.
