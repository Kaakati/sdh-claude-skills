# Rule Sections

## Section Definitions

| # | Section | Prefix | Priority | Description |
|---|---------|--------|----------|-------------|
| 1 | Atoms | `atom-` | HIGH | Indivisible UI primitives -- buttons, inputs, labels, icons, headings. Cannot compose other components. Must consume design tokens. |
| 2 | Molecules | `molecule-` | HIGH | Simple groups of atoms functioning as a unit -- search forms, form fields, nav links. Compose only atoms. Single responsibility. |
| 3 | Organisms | `organism-` | MEDIUM | Complex UI sections composed of molecules and atoms -- headers, product grids, sidebars. First level that can be data-aware. |
| 4 | Templates | `template-` | MEDIUM | Page-level layout skeletons defining content areas without real data. Composed of organisms, molecules, and atoms. |
| 5 | Pages | `page-` | MEDIUM | Template instances populated with real data. Platform-specific: Views (Phlex), pages (Vite), app routes (Next.js), screens (RN). |
| 6 | Organization | `org-` | MEDIUM | Directory structure, file naming, and namespace conventions across all 4 platforms. |

## Applicability

All rules apply to these platforms unless otherwise noted:
- **Phlex (Rails)**: `backend/app/components/` and `backend/app/views/`
- **ReactJS (Vite SPA)**: `web/src/components/` and `web/src/pages/`
- **Next.js (App Router)**: `next/src/components/` and `next/app/`
- **React Native**: `mobile/src/components/` and `mobile/src/screens/`
