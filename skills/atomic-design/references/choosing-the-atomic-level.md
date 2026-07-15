# Choosing the Atomic Level

Platform-neutral. Read this when you are holding a component and do not yet know whether it is an
atom, a molecule, an organism, a template, or a page. Once you know the level, read the matching
`rules/<rule-id>.md` for the code pattern on your platform.

Atomic Design (Brad Frost) borrows its model from chemistry: atoms combine into molecules, which
combine into organisms. UI primitives compose into increasingly complex structures, and each level
has a fixed set of things it is allowed to do.

| Level | Meaning |
|-------|---------|
| **Atom** | An indivisible UI primitive — button, input, label |
| **Molecule** | A small group of atoms working as one unit — search form, form field |
| **Organism** | A complex section built from molecules and atoms — header, sidebar |
| **Template** | A page layout that defines *where* content goes — dashboard layout |
| **Page** | A template populated with real data — the actual dashboard |

---

## Decision: which level does this component belong to?

Walk the tree top to bottom. The first terminal you hit is the answer.

```
START: Is this component a single HTML element / native view?
  |
  YES --> Does it compose other design system components?
  |         |
  |         NO --> ATOM
  |         YES --> Not actually indivisible, re-evaluate
  |
  NO --> Does it compose ONLY atoms?
          |
          YES --> Does it serve ONE cohesive function?
          |         |
          |         YES --> MOLECULE
          |         NO --> Split into multiple molecules
          |
          NO --> Does it compose molecules + atoms into a UI section?
                  |
                  YES --> Is it a recognizable interface section?
                  |         |
                  |         YES --> ORGANISM
                  |         NO --> Might be a molecule with too much scope
                  |
                  NO --> Does it define layout structure without real content?
                          |
                          YES --> Does it use slots/children for content?
                          |         |
                          |         YES --> TEMPLATE
                          |         NO --> Refactor to use slots
                          |
                          NO --> Does it connect to routes and fetch data?
                                  |
                                  YES --> PAGE
                                  NO --> Re-evaluate the component's purpose
```

If you want the one-line version, ask these in order and stop at the first "yes":

| Question | If Yes |
|----------|--------|
| Is it a single styled HTML element? | Atom |
| Does it only use atoms and serve one purpose? | Molecule |
| Does it represent a distinct UI section? | Organism |
| Does it define where things go without saying what? | Template |
| Is it a route entry point with real data? | Page |

Rule files with the per-platform code for each terminal: `atom-standalone-primitives`,
`molecule-atom-composition`, `organism-section-boundary`, `template-layout-skeleton`,
`page-template-instance`.

---

## Decision: may this component hold state or fetch data?

The level you just chose fixes the answer. Data-awareness is a hard boundary, not a preference:
**organisms are the lowest level allowed to fetch data or read global state.** Anything below an
organism receives display-ready props.

| Level | Can Import From | Data-Aware? | Stateful? |
|-------|----------------|-------------|-----------|
| Atoms | Nothing (standalone) | No | UI state only (hover, focus) |
| Molecules | Atoms only | No | Form state only |
| Organisms | Atoms + Molecules | Yes (props/hooks) | Yes |
| Templates | Atoms + Molecules + Organisms | No (layout only) | No |
| Pages | Everything | Yes (full data) | Yes |

The "Stateful?" column is the one people miss. A molecule holding a controlled input's value is
fine — that is form state. A molecule holding a `useQuery` result is not: that is data-awareness
leaking below the organism boundary. See `organism-data-awareness` for the code pattern.

---

## Decision: does an atom already exist for this?

Before writing a new atom, check the standard set. If your component is a variation of one of these
(a different color, a different size), extend the existing atom with a prop instead of adding a
sibling.

| Atom | Purpose | Key Props |
|------|---------|-----------|
| `Button` | Actions | `label`, `variant`, `size`, `disabled` |
| `Input` | Text entry | `name`, `type`, `placeholder`, `value` |
| `Heading` | Section headings | `level`, `children` |
| `Text` | Body text | `size`, `color`, `weight`, `children` |
| `Label` | Form labels | `htmlFor`, `required`, `children` |
| `Icon` | SVG icons | `name`, `size`, `color` |
| `Avatar` | User images | `src`, `alt`, `size` |
| `Badge` | Status indicators | `label`, `variant` |
| `Spinner` | Loading indicators | `size`, `color` |
| `Divider` | Visual separators | `orientation` |
| `HelpText` | Form helper text | `variant`, `children` |
| `Select` | Dropdown selection | `name`, `options`, `value` |

Every prop on this list is a primitive or a token name — never an object, a record, or a fetched
entity. An atom that wants a `user` prop is a molecule.

---

## Decision: does a molecule already exist for this?

`molecule-single-responsibility` carries the main catalog (`SearchForm`, `FormField`, `NavLink`,
`FilterGroup`, `SortSelector`, `StatCard`, `AvatarGroup`) with the atoms each one composes. Three
further standard molecules are not in that table:

| Molecule | Atoms Used | Purpose |
|----------|-----------|---------|
| `UserMenu` | Avatar + Text + Icon | User dropdown trigger |
| `Breadcrumb` | Link + Icon | Navigation breadcrumbs |
| `Pagination` | Button + Text | Page navigation |

Each still obeys the molecule contract: composes only atoms, serves one cohesive function, accepts
display-ready props. `Pagination` receives page numbers and hrefs — it does not know how to fetch
the next page.

---

## Decision: I'm porting this component to another platform — does its level change?

No. The level is a property of the component's role, not of its implementation. A `Button` is an
atom in Phlex, in a Vite SPA, in Next.js, and in React Native.

Across platforms, these stay the same:

- The atomic classification (atom stays an atom)
- The semantic purpose (a Button triggers an action)
- The prop interface, wherever the platform allows it (`label`, `variant`, `size`)

These legitimately differ, and differing here is not a reason to reclassify:

| Concern | How it varies |
|---------|---------------|
| Rendering primitive | `<button>` on the web vs `<Pressable>` in React Native |
| Styling approach | Tailwind CSS on the web vs NativeWind in React Native |
| Platform features | Server Components in Next.js; `accessibilityRole` in React Native |

So: port the interface, rewrite the internals, keep the directory. The one place platform genuinely
changes the *rules* rather than the implementation is the Next.js server/client split — see
`references/nextjs-server-client-boundary.md`.

For the directory each level maps to on each platform, read `org-directory-structure`; for file and
class naming, read `org-naming-conventions`.
