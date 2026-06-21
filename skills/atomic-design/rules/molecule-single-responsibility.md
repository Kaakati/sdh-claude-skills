---
title: "Molecule Single Responsibility"
id: molecule-single-responsibility
impact: HIGH
tags: [atomic-design, molecules]
platforms: [phlex, reactjs, nextjs, react-native]
---

# Molecule Single Responsibility

Each molecule should serve one cohesive function. If a molecule handles multiple unrelated concerns, split it into separate molecules. A molecule answers one question: "What does this group of atoms do together?"

## Incorrect

A molecule that handles search, filtering, AND sorting -- three unrelated concerns bundled into one component.

```tsx
// web/src/components/molecules/FormControls/FormControls.tsx
// WRONG: Three unrelated responsibilities in one molecule
import { Input } from "@/components/atoms/Input";
import { Button } from "@/components/atoms/Button";
import { Select } from "@/components/atoms/Select";

interface FormControlsProps {
  onSearch: (query: string) => void;
  onFilter: (category: string) => void;
  onSort: (field: string) => void;
  categories: string[];
  sortFields: string[];
}

export function FormControls({
  onSearch,
  onFilter,
  onSort,
  categories,
  sortFields,
}: FormControlsProps) {
  return (
    <div className="flex gap-4">
      {/* Search concern */}
      <Input name="search" placeholder="Search..." />
      <Button label="Search" onClick={() => onSearch("")} />

      {/* Filter concern */}
      <Select name="category" options={categories} onChange={onFilter} />

      {/* Sort concern */}
      <Select name="sort" options={sortFields} onChange={onSort} />
      <Button label="Sort" onClick={() => onSort("")} />
    </div>
  );
}
```

```ruby
# backend/app/components/molecules/form_controls.rb
# WRONG: Multiple responsibilities
class Components::Molecules::FormControls < Components::Base
  def initialize(categories:, sort_fields:)
    @categories = categories
    @sort_fields = sort_fields
  end

  def view_template
    div(class: "flex gap-4") do
      # Search
      render Components::Atoms::Input.new(name: "search", placeholder: "Search...")
      render Components::Atoms::Button.new(label: "Search", type: :submit)

      # Filter
      render Components::Atoms::Select.new(name: "category", options: @categories)

      # Sort
      render Components::Atoms::Select.new(name: "sort", options: @sort_fields)
    end
  end
end
```

## Correct

Split into three focused molecules, each with a single responsibility.

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
      render Components::Atoms::Input.new(name: "q", type: :search, placeholder: @placeholder)
      render Components::Atoms::Button.new(label: "Search", type: :submit, variant: :primary)
    end
  end
end

# backend/app/components/molecules/filter_group.rb
class Components::Molecules::FilterGroup < Components::Base
  def initialize(label:, name:, options:)
    @label = label
    @name = name
    @options = options
  end

  def view_template
    div(class: "flex items-center gap-2") do
      render Components::Atoms::Label.new(text: @label, html_for: @name)
      render Components::Atoms::Select.new(name: @name, options: @options)
    end
  end
end

# backend/app/components/molecules/sort_selector.rb
class Components::Molecules::SortSelector < Components::Base
  def initialize(fields:, current_sort: nil)
    @fields = fields
    @current_sort = current_sort
  end

  def view_template
    div(class: "flex items-center gap-2") do
      render Components::Atoms::Label.new(text: "Sort by", html_for: "sort")
      render Components::Atoms::Select.new(name: "sort", options: @fields, selected: @current_sort)
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

export function SearchForm({ placeholder = "Search...", onSubmit }: SearchFormProps) {
  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    onSubmit(formData.get("q") as string);
  };

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-2">
      <Input name="q" type="search" placeholder={placeholder} />
      <Button label="Search" type="submit" />
    </form>
  );
}

// web/src/components/molecules/FilterGroup/FilterGroup.tsx
import { Label } from "@/components/atoms/Label";
import { Select } from "@/components/atoms/Select";

interface FilterGroupProps {
  label: string;
  name: string;
  options: Array<{ value: string; label: string }>;
  onChange: (value: string) => void;
}

export function FilterGroup({ label, name, options, onChange }: FilterGroupProps) {
  return (
    <div className="flex items-center gap-2">
      <Label htmlFor={name}>{label}</Label>
      <Select id={name} name={name} options={options} onChange={onChange} />
    </div>
  );
}

// web/src/components/molecules/SortSelector/SortSelector.tsx
import { Label } from "@/components/atoms/Label";
import { Select } from "@/components/atoms/Select";

interface SortSelectorProps {
  fields: Array<{ value: string; label: string }>;
  currentSort?: string;
  onChange: (field: string) => void;
}

export function SortSelector({ fields, currentSort, onChange }: SortSelectorProps) {
  return (
    <div className="flex items-center gap-2">
      <Label htmlFor="sort">Sort by</Label>
      <Select id="sort" name="sort" options={fields} value={currentSort} onChange={onChange} />
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

export function SearchForm({ placeholder = "Search...", onSubmit }: SearchFormProps) {
  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    onSubmit(formData.get("q") as string);
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
import { useState } from "react";
import { View } from "react-native";
import { Input } from "@/components/atoms/Input";
import { Button } from "@/components/atoms/Button";

interface SearchFormProps {
  placeholder?: string;
  onSubmit: (query: string) => void;
}

export function SearchForm({ placeholder = "Search...", onSubmit }: SearchFormProps) {
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

// mobile/src/components/molecules/FilterGroup/FilterGroup.tsx
import { View } from "react-native";
import { Label } from "@/components/atoms/Label";
import { Select } from "@/components/atoms/Select";

interface FilterGroupProps {
  label: string;
  options: Array<{ value: string; label: string }>;
  onChange: (value: string) => void;
}

export function FilterGroup({ label, options, onChange }: FilterGroupProps) {
  return (
    <View className="flex-row items-center gap-2">
      <Label>{label}</Label>
      <Select options={options} onChange={onChange} />
    </View>
  );
}
```

## Additional Context

**Single responsibility test -- ask these questions:**
1. Can you describe the molecule in one short phrase without "and"?
   - "A search form" -- good
   - "A search form and filter controls" -- split it
2. Would changing one feature force changes to unrelated parts?
   - If adding a sort direction toggle forces changes to the search input, they should be separate
3. Can different pages reuse parts of this molecule independently?
   - If pages need search without filters, or filters without sort, they should be separate molecules

**Common molecules and their single responsibility:**
| Molecule | Responsibility | Atoms Used |
|----------|---------------|------------|
| `SearchForm` | Text search input with submit | Input + Button |
| `FormField` | Labeled input with error display | Label + Input + HelpText |
| `NavLink` | Navigation link with icon | Icon + Link |
| `FilterGroup` | Labeled dropdown filter | Label + Select |
| `SortSelector` | Sort field selector | Label + Select |
| `StatCard` | Single metric display | Heading + Text |
| `AvatarGroup` | Grouped user avatars | Avatar (multiple) |

**When to combine vs. split:**
- Combine when atoms always appear together and represent one interaction (Label + Input = FormField)
- Split when atoms serve different user intents even if they appear near each other visually
