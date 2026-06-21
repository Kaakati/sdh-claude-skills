---
title: "Naming Conventions"
id: org-naming-conventions
impact: MEDIUM
tags: [atomic-design, organization]
platforms: [phlex, reactjs, nextjs, react-native]
---

# Naming Conventions

Follow platform-specific naming conventions for files, directories, classes, and exports. Consistency across the codebase reduces cognitive load and makes components discoverable.

## Phlex (Rails)

| Aspect | Convention | Example |
|--------|-----------|---------|
| Files | `snake_case.rb` | `search_form.rb`, `product_grid.rb` |
| Class names | `PascalCase` namespaced | `Components::Atoms::Button` |
| Namespace | `Components::{Level}::{Name}` | `Components::Molecules::SearchForm` |
| View files | `snake_case.rb` | `views/articles/index.rb` |
| View classes | `Views::{Resource}::{Action}` | `Views::Articles::Index` |
| Method args | `keyword_args:` | `def initialize(label:, variant: :primary)` |

```ruby
# File: backend/app/components/atoms/button.rb
# Class: Components::Atoms::Button
class Components::Atoms::Button < Components::Base
  def initialize(label:, variant: :primary, size: :md)
    @label = label
    @variant = variant
    @size = size
  end

  def view_template
    button(class: button_classes) { @label }
  end
end

# File: backend/app/components/molecules/search_form.rb
# Class: Components::Molecules::SearchForm
class Components::Molecules::SearchForm < Components::Base
  def initialize(placeholder: "Search...", action: nil)
    @placeholder = placeholder
    @action = action
  end

  def view_template
    form(action: @action, method: :get, class: "flex gap-2") do
      render Components::Atoms::Input.new(name: "q", placeholder: @placeholder)
      render Components::Atoms::Button.new(label: "Search", type: :submit)
    end
  end
end

# File: backend/app/views/articles/index.rb
# Class: Views::Articles::Index
class Views::Articles::Index < Views::Base
  def initialize(articles:, current_user:)
    @articles = articles
    @current_user = current_user
  end
end
```

## ReactJS (Vite SPA)

| Aspect | Convention | Example |
|--------|-----------|---------|
| Directories | `PascalCase/` | `Button/`, `SearchForm/` |
| Component files | `PascalCase.tsx` | `Button.tsx`, `SearchForm.tsx` |
| Barrel exports | `index.ts` | `export { Button } from './Button'` |
| Page files | `PascalCase` + `Page` suffix | `DashboardPage.tsx` |
| Hook files | `camelCase` with `use` prefix | `useSearchForm.ts` |
| Type files | `PascalCase.types.ts` (if separate) | `Button.types.ts` |
| Test files | `PascalCase.test.tsx` | `Button.test.tsx` |

```tsx
// File: web/src/components/atoms/Button/Button.tsx
// Export: Button
export function Button({ label, variant = "primary" }: ButtonProps) {
  return <button className={styles}>{label}</button>;
}

// File: web/src/components/atoms/Button/index.ts
export { Button } from "./Button";
export type { ButtonProps } from "./Button";

// File: web/src/components/molecules/SearchForm/SearchForm.tsx
// Export: SearchForm
export function SearchForm({ onSubmit }: SearchFormProps) {
  return (
    <form>
      <Input name="q" />
      <Button label="Search" type="submit" />
    </form>
  );
}

// File: web/src/pages/DashboardPage.tsx
// Export: DashboardPage
export function DashboardPage() {
  return <DashboardLayout>...</DashboardLayout>;
}
```

**Import paths (Vite SPA):**
```tsx
// Use path aliases configured in vite.config.ts / tsconfig.json
import { Button } from "@/components/atoms/Button";
import { SearchForm } from "@/components/molecules/SearchForm";
import { Header } from "@/components/organisms/Header";
import { DashboardLayout } from "@/components/templates/DashboardLayout";
```

## Next.js (App Router)

| Aspect | Convention | Example |
|--------|-----------|---------|
| Directories | `PascalCase/` | `Button/`, `SearchForm/` |
| Component files | `PascalCase.tsx` | `Button.tsx`, `Header.tsx` |
| Barrel exports | `index.ts` | `export { Button } from './Button'` |
| Page files | `page.tsx` (Next.js convention) | `app/dashboard/page.tsx` |
| Layout files | `layout.tsx` (Next.js convention) | `app/dashboard/layout.tsx` |
| Loading files | `loading.tsx` | `app/dashboard/loading.tsx` |
| Error files | `error.tsx` | `app/dashboard/error.tsx` |
| Server Components | No directive (default) | `export default async function Page()` |
| Client Components | `"use client"` at top | `"use client"` then export |

```tsx
// File: next/src/components/atoms/Button/Button.tsx
export function Button({ label, variant = "primary" }: ButtonProps) {
  return <button className={styles}>{label}</button>;
}

// File: next/src/components/atoms/Button/index.ts
export { Button } from "./Button";

// File: next/app/dashboard/page.tsx (Server Component page)
export const metadata = { title: "Dashboard" };

export default async function DashboardPage() {
  const data = await fetchData();
  return <DashboardLayout>...</DashboardLayout>;
}

// File: next/app/dashboard/loading.tsx
export default function DashboardLoading() {
  return <Spinner />;
}
```

**Import paths (Next.js):**
```tsx
// Use path aliases configured in tsconfig.json
import { Button } from "@/components/atoms/Button";
import { Header } from "@/components/organisms/Header";
```

## React Native

| Aspect | Convention | Example |
|--------|-----------|---------|
| Directories | `PascalCase/` | `Button/`, `SearchForm/` |
| Component files | `PascalCase.tsx` | `Button.tsx`, `Header.tsx` |
| Barrel exports | `index.ts` | `export { Button } from './Button'` |
| Screen files | `PascalCase` + `Screen` suffix | `DashboardScreen.tsx` |
| Hook files | `camelCase` with `use` prefix | `useAuth.ts` |
| Store files | `camelCase` + `Store` suffix | `authStore.ts` |
| Test files | `PascalCase.test.tsx` | `Button.test.tsx` |

```tsx
// File: mobile/src/components/atoms/Button/Button.tsx
export function Button({ label, variant = "primary" }: ButtonProps) {
  return (
    <Pressable>
      <Text>{label}</Text>
    </Pressable>
  );
}

// File: mobile/src/components/atoms/Button/index.ts
export { Button } from "./Button";
export type { ButtonProps } from "./Button";

// File: mobile/src/screens/DashboardScreen.tsx
export function DashboardScreen() {
  return <DashboardLayout>...</DashboardLayout>;
}
```

**Import paths (React Native):**
```tsx
// Use path aliases configured in babel.config.js / tsconfig.json
import { Button } from "@/components/atoms/Button";
import { Header } from "@/components/organisms/Header";
```

## Summary Table

| Platform | File Case | Dir Case | Class/Export Case | Page Suffix | Page Location |
|----------|----------|----------|-------------------|-------------|---------------|
| Phlex | `snake_case` | `snake_case` | `PascalCase` namespace | N/A (resource-based) | `backend/app/views/` |
| ReactJS (Vite) | `PascalCase` | `PascalCase` | `PascalCase` export | `Page` | `web/src/pages/` |
| Next.js | `PascalCase` / `page.tsx` | `PascalCase` / kebab | `PascalCase` export | `page.tsx` | `next/app/` |
| React Native | `PascalCase` | `PascalCase` | `PascalCase` export | `Screen` | `mobile/src/screens/` |

## Additional Context

**Naming anti-patterns to avoid:**
- Generic names: `Component.tsx`, `Wrapper.tsx`, `Container.tsx`
- Abbreviations: `Btn.tsx`, `Hdr.tsx`, `Nav.tsx` (use full words)
- Level in the name: `AtomButton.tsx`, `MoleculeSearchForm.tsx` (the directory provides context)
- Mixed casing: `searchForm.tsx` in React or `SearchForm.rb` in Rails

**When naming is ambiguous:**
- A `Card` that just renders text and an image: atom
- A `ProductCard` with title, price, and rating: molecule (multiple atoms)
- A `ProductGrid` with search, sort, and a list of ProductCards: organism
- The directory placement (`atoms/`, `molecules/`, `organisms/`) clarifies the level
