---
title: "Molecules Compose Only Atoms"
id: molecule-atom-composition
impact: HIGH
tags: [atomic-design, molecules]
platforms: [phlex, reactjs, nextjs, react-native]
---

# Molecules Compose Only Atoms

Molecules are simple groups of atoms that function together as a unit. A molecule must only import and compose atoms -- never other molecules, organisms, templates, or pages. This strict composition rule keeps the dependency graph clean and prevents circular dependencies.

## Incorrect

A molecule importing another molecule violates the composition hierarchy.

```tsx
// web/src/components/molecules/SearchBar/SearchBar.tsx
// WRONG: Molecule importing another molecule
import { FormField } from "@/components/molecules/FormField";
import { Button } from "@/components/atoms/Button";

export function SearchBar() {
  return (
    <form>
      <FormField label="Search" name="query" />
      <Button label="Search" />
    </form>
  );
}
```

```ruby
# backend/app/components/molecules/search_bar.rb
# WRONG: Molecule importing another molecule
class Components::Molecules::SearchBar < Components::Base
  def view_template
    form(class: "flex gap-2") do
      render Components::Molecules::FormField.new(label: "Search", name: "query")
      render Components::Atoms::Button.new(label: "Search")
    end
  end
end
```

A molecule importing an organism -- even worse, skipping an entire level.

```tsx
// WRONG: Molecule importing an organism
import { Header } from "@/components/organisms/Header";

export function PageHeader() {
  return <Header title="Dashboard" />;
}
```

## Correct

Molecules compose only atoms into a cohesive functional unit.

### Phlex (Rails)

```ruby
# backend/app/components/molecules/search_form.rb
class Components::Molecules::SearchForm < Components::Base
  def initialize(placeholder: "Search...", action: nil)
    @placeholder = placeholder
    @action = action
  end

  def view_template
    form(action: @action, method: :get, class: "flex items-center gap-2") do
      render Components::Atoms::Input.new(
        name: "q",
        type: :search,
        placeholder: @placeholder,
      )
      render Components::Atoms::Button.new(
        label: "Search",
        variant: :primary,
        size: :md,
        type: :submit,
      )
    end
  end
end
```

```ruby
# backend/app/components/molecules/form_field.rb
class Components::Molecules::FormField < Components::Base
  def initialize(label:, name:, type: :text, error: nil, required: false, placeholder: nil)
    @label = label
    @name = name
    @type = type
    @error = error
    @required = required
    @placeholder = placeholder
  end

  def view_template
    div(class: "flex flex-col gap-1") do
      render Components::Atoms::Label.new(text: @label, html_for: @name, required: @required)
      render Components::Atoms::Input.new(
        name: @name,
        type: @type,
        placeholder: @placeholder,
        aria_invalid: @error.present?,
        aria_describedby: @error ? "#{@name}-error" : nil,
      )
      if @error
        render Components::Atoms::HelpText.new(text: @error, variant: :error, id: "#{@name}-error")
      end
    end
  end
end
```

### ReactJS (Vite SPA)

```tsx
// web/src/components/molecules/SearchForm/SearchForm.tsx
import { type FormEvent } from "react";
import { Input } from "@/components/atoms/Input";
import { Button } from "@/components/atoms/Button";

interface SearchFormProps {
  placeholder?: string;
  onSubmit: (query: string) => void;
}

export function SearchForm({
  placeholder = "Search...",
  onSubmit,
}: SearchFormProps) {
  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const query = formData.get("q") as string;
    onSubmit(query);
  };

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-2">
      <Input name="q" type="search" placeholder={placeholder} />
      <Button label="Search" type="submit" />
    </form>
  );
}
```

```tsx
// web/src/components/molecules/FormField/FormField.tsx
import { Input } from "@/components/atoms/Input";
import { Label } from "@/components/atoms/Label";
import { HelpText } from "@/components/atoms/HelpText";

interface FormFieldProps {
  label: string;
  name: string;
  type?: string;
  placeholder?: string;
  error?: string;
  required?: boolean;
}

export function FormField({
  label,
  name,
  type = "text",
  placeholder,
  error,
  required = false,
}: FormFieldProps) {
  return (
    <div className="flex flex-col gap-1">
      <Label htmlFor={name} required={required}>
        {label}
      </Label>
      <Input
        id={name}
        name={name}
        type={type}
        placeholder={placeholder}
        aria-invalid={!!error}
        aria-describedby={error ? `${name}-error` : undefined}
      />
      {error && <HelpText id={`${name}-error`} variant="error">{error}</HelpText>}
    </div>
  );
}
```

### Next.js (App Router)

```tsx
// next/src/components/molecules/SearchForm/SearchForm.tsx
"use client";

import { type FormEvent } from "react";
import { Input } from "@/components/atoms/Input";
import { Button } from "@/components/atoms/Button";

interface SearchFormProps {
  placeholder?: string;
  onSubmit: (query: string) => void;
}

export function SearchForm({
  placeholder = "Search...",
  onSubmit,
}: SearchFormProps) {
  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const query = formData.get("q") as string;
    onSubmit(query);
  };

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-2">
      <Input name="q" type="search" placeholder={placeholder} />
      <Button label="Search" type="submit" />
    </form>
  );
}
```

### React Native

```tsx
// mobile/src/components/molecules/SearchForm/SearchForm.tsx
import { View } from "react-native";
import { Input } from "@/components/atoms/Input";
import { Button } from "@/components/atoms/Button";

interface SearchFormProps {
  placeholder?: string;
  onSubmit: (query: string) => void;
}

export function SearchForm({
  placeholder = "Search...",
  onSubmit,
}: SearchFormProps) {
  const [query, setQuery] = useState("");

  const handleSubmit = () => {
    onSubmit(query);
    setQuery("");
  };

  return (
    <View className="flex-row items-center gap-2">
      <View className="flex-1">
        <Input
          name="search"
          placeholder={placeholder}
          value={query}
          onChangeText={setQuery}
          onSubmitEditing={handleSubmit}
          returnKeyType="search"
        />
      </View>
      <Button label="Search" onPress={handleSubmit} />
    </View>
  );
}
```

## Additional Context

**The import rule is strict and directional:**
```
Atoms      -> (nothing)
Molecules  -> Atoms ONLY
Organisms  -> Atoms + Molecules
Templates  -> Atoms + Molecules + Organisms
Pages      -> Everything
```

**How to validate:**
- Every import statement in a molecule file should resolve to `atoms/` or to external libraries (React, utilities, types)
- If you find an import from `molecules/`, `organisms/`, `templates/`, or `pages/` -- the component is misclassified

**When a molecule needs another molecule:**
- Promote the consuming component to an **organism** if it composes multiple molecules
- Or, flatten the shared logic into atoms and recompose

**Molecules CAN import:**
- Atoms from the design system
- External utility libraries (`clsx`, `twMerge`, `date-fns`)
- Type definitions and interfaces
- Hooks for internal UI state (`useState`, `useRef`) but NOT data-fetching hooks

**Molecules CANNOT import:**
- Other molecules
- Organisms, templates, or pages
- Data-fetching hooks (`useQuery`, `useSWR`)
- Global state stores (`useStore`)
