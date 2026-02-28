# Atomic Design -- Complete Reference Guide

A comprehensive guide to Atomic Design methodology applied across Phlex (Rails), ReactJS (Vite SPA), Next.js (App Router), and React Native.

---

## 1. Introduction

Atomic Design, created by Brad Frost, is a methodology for building UI component systems. It borrows from chemistry: just as atoms combine into molecules, which combine into organisms, UI primitives compose into increasingly complex structures.

The five levels are:

1. **Atoms** -- Indivisible UI primitives (buttons, inputs, labels)
2. **Molecules** -- Simple groups of atoms working as a unit (search form, form field)
3. **Organisms** -- Complex sections composed of molecules and atoms (header, sidebar)
4. **Templates** -- Page layouts that define where content goes (dashboard layout)
5. **Pages** -- Templates populated with real data (the actual dashboard)

### Composition Rules

| Level | Can Import From | Data-Aware? | Stateful? |
|-------|----------------|-------------|-----------|
| Atoms | Nothing (standalone) | No | UI state only (hover, focus) |
| Molecules | Atoms only | No | Form state only |
| Organisms | Atoms + Molecules | Yes (props/hooks) | Yes |
| Templates | Atoms + Molecules + Organisms | No (layout only) | No |
| Pages | Everything | Yes (full data) | Yes |

### Platform Mapping

| Atomic Level | Phlex (Rails) | ReactJS (Vite) | Next.js | React Native |
|-------------|---------------|----------------|---------|-------------|
| Atoms | `backend/app/components/atoms/` | `web/src/components/atoms/` | `next/src/components/atoms/` | `mobile/src/components/atoms/` |
| Molecules | `backend/app/components/molecules/` | `web/src/components/molecules/` | `next/src/components/molecules/` | `mobile/src/components/molecules/` |
| Organisms | `backend/app/components/organisms/` | `web/src/components/organisms/` | `next/src/components/organisms/` | `mobile/src/components/organisms/` |
| Templates | `backend/app/components/templates/` | `web/src/components/templates/` | `next/src/components/templates/` | `mobile/src/components/templates/` |
| Pages | `backend/app/views/` | `web/src/pages/` | `next/app/` | `mobile/src/screens/` |

---

## 2. Atoms

### Rule: `atom-standalone-primitives` (HIGH)

Atoms are indivisible. They map to a single semantic element and cannot compose other atoms.

### Rule: `atom-theming-tokens` (HIGH)

Atoms consume design tokens -- never hardcoded colors, sizes, or fonts.

### Examples

#### Button Atom

**Phlex (Rails)**
```ruby
# backend/app/components/atoms/button.rb
class Components::Atoms::Button < Components::Base
  VARIANTS = {
    primary: "bg-primary text-white hover:bg-primary-dark focus:ring-primary",
    secondary: "bg-secondary text-gray-900 hover:bg-secondary-dark focus:ring-secondary",
    ghost: "bg-transparent text-gray-700 hover:bg-gray-100 focus:ring-gray-300",
    danger: "bg-error text-white hover:bg-error-dark focus:ring-error",
  }.freeze

  SIZES = {
    sm: "px-3 py-1.5 text-sm",
    md: "px-4 py-2 text-base",
    lg: "px-6 py-3 text-lg",
  }.freeze

  def initialize(label:, variant: :primary, size: :md, type: :button, disabled: false, **attrs)
    @label = label
    @variant = variant
    @size = size
    @type = type
    @disabled = disabled
    @attrs = attrs
  end

  def view_template
    button(
      type: @type,
      class: button_classes,
      disabled: @disabled,
      **@attrs
    ) { @label }
  end

  private

  def button_classes
    [
      "inline-flex items-center justify-center font-medium rounded-lg",
      "transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2",
      VARIANTS.fetch(@variant),
      SIZES.fetch(@size),
      ("opacity-50 cursor-not-allowed" if @disabled),
    ].compact.join(" ")
  end
end
```

**ReactJS (Vite SPA)**
```tsx
// web/src/components/atoms/Button/Button.tsx
import { type ButtonHTMLAttributes, forwardRef } from "react";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
type ButtonSize = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  label: string;
  variant?: ButtonVariant;
  size?: ButtonSize;
}

const variantStyles: Record<ButtonVariant, string> = {
  primary: "bg-primary text-white hover:bg-primary-dark focus:ring-primary",
  secondary: "bg-secondary text-gray-900 hover:bg-secondary-dark focus:ring-secondary",
  ghost: "bg-transparent text-gray-700 hover:bg-gray-100 focus:ring-gray-300",
  danger: "bg-error text-white hover:bg-error-dark focus:ring-error",
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: "px-3 py-1.5 text-sm",
  md: "px-4 py-2 text-base",
  lg: "px-6 py-3 text-lg",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  function Button({ label, variant = "primary", size = "md", className, disabled, ...props }, ref) {
    return (
      <button
        ref={ref}
        className={twMerge(
          clsx(
            "inline-flex items-center justify-center font-medium rounded-lg",
            "transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2",
            variantStyles[variant],
            sizeStyles[size],
            disabled && "opacity-50 cursor-not-allowed",
            className,
          ),
        )}
        disabled={disabled}
        {...props}
      >
        {label}
      </button>
    );
  },
);
```

**Next.js (App Router)**
```tsx
// next/src/components/atoms/Button/Button.tsx
// Same as ReactJS -- atoms are framework-agnostic on the web
import { type ButtonHTMLAttributes, forwardRef } from "react";
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
type ButtonSize = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  label: string;
  variant?: ButtonVariant;
  size?: ButtonSize;
}

const variantStyles: Record<ButtonVariant, string> = {
  primary: "bg-primary text-white hover:bg-primary-dark focus:ring-primary",
  secondary: "bg-secondary text-gray-900 hover:bg-secondary-dark focus:ring-secondary",
  ghost: "bg-transparent text-gray-700 hover:bg-gray-100 focus:ring-gray-300",
  danger: "bg-error text-white hover:bg-error-dark focus:ring-error",
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: "px-3 py-1.5 text-sm",
  md: "px-4 py-2 text-base",
  lg: "px-6 py-3 text-lg",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  function Button({ label, variant = "primary", size = "md", className, disabled, ...props }, ref) {
    return (
      <button
        ref={ref}
        className={twMerge(
          clsx(
            "inline-flex items-center justify-center font-medium rounded-lg",
            "transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2",
            variantStyles[variant],
            sizeStyles[size],
            disabled && "opacity-50 cursor-not-allowed",
            className,
          ),
        )}
        disabled={disabled}
        {...props}
      >
        {label}
      </button>
    );
  },
);
```

**React Native**
```tsx
// mobile/src/components/atoms/Button/Button.tsx
import { Pressable, Text, type PressableProps } from "react-native";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
type ButtonSize = "sm" | "md" | "lg";

interface ButtonProps extends Omit<PressableProps, "children"> {
  label: string;
  variant?: ButtonVariant;
  size?: ButtonSize;
}

const variantStyles = {
  primary: { container: "bg-primary", text: "text-white" },
  secondary: { container: "bg-secondary", text: "text-gray-900" },
  ghost: { container: "bg-transparent", text: "text-gray-700" },
  danger: { container: "bg-error", text: "text-white" },
} as const;

const sizeStyles = {
  sm: { container: "px-3 py-1.5", text: "text-sm" },
  md: { container: "px-4 py-2", text: "text-base" },
  lg: { container: "px-6 py-3", text: "text-lg" },
} as const;

export function Button({
  label,
  variant = "primary",
  size = "md",
  disabled,
  ...props
}: ButtonProps) {
  const vStyle = variantStyles[variant];
  const sStyle = sizeStyles[size];

  return (
    <Pressable
      className={`items-center justify-center rounded-lg ${vStyle.container} ${sStyle.container} ${disabled ? "opacity-50" : ""}`}
      disabled={disabled}
      accessibilityRole="button"
      accessibilityLabel={label}
      {...props}
    >
      <Text className={`font-medium ${vStyle.text} ${sStyle.text}`}>
        {label}
      </Text>
    </Pressable>
  );
}
```

#### Input Atom

**Phlex (Rails)**
```ruby
# backend/app/components/atoms/input.rb
class Components::Atoms::Input < Components::Base
  def initialize(name:, type: :text, placeholder: nil, value: nil, disabled: false, **attrs)
    @name = name
    @type = type
    @placeholder = placeholder
    @value = value
    @disabled = disabled
    @attrs = attrs
  end

  def view_template
    input(
      name: @name,
      type: @type,
      placeholder: @placeholder,
      value: @value,
      disabled: @disabled,
      class: input_classes,
      **@attrs
    )
  end

  private

  def input_classes
    [
      "w-full rounded-lg border border-gray-300 px-4 py-2",
      "text-base text-gray-900 placeholder-gray-400",
      "focus:border-primary focus:ring-2 focus:ring-primary/20",
      "disabled:bg-gray-50 disabled:text-gray-400",
    ].join(" ")
  end
end
```

**ReactJS / Next.js**
```tsx
// web/src/components/atoms/Input/Input.tsx (same for next/src/)
import { type InputHTMLAttributes, forwardRef } from "react";
import { twMerge } from "tailwind-merge";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  name: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  function Input({ className, ...props }, ref) {
    return (
      <input
        ref={ref}
        className={twMerge(
          "w-full rounded-lg border border-gray-300 px-4 py-2",
          "text-base text-gray-900 placeholder-gray-400",
          "focus:border-primary focus:ring-2 focus:ring-primary/20",
          "disabled:bg-gray-50 disabled:text-gray-400",
          className,
        )}
        {...props}
      />
    );
  },
);
```

**React Native**
```tsx
// mobile/src/components/atoms/Input/Input.tsx
import { TextInput, type TextInputProps } from "react-native";

interface InputProps extends TextInputProps {
  name: string;
}

export function Input({ name, ...props }: InputProps) {
  return (
    <TextInput
      className="w-full rounded-lg border border-gray-300 px-4 py-2 text-base text-gray-900"
      placeholderTextColor="#9ca3af"
      accessibilityLabel={name}
      {...props}
    />
  );
}
```

#### Other Common Atoms

| Atom | Purpose | Key Props |
|------|---------|-----------|
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

---

## 3. Molecules

### Rule: `molecule-atom-composition` (HIGH)

Molecules compose ONLY atoms. No imports from molecules, organisms, templates, or pages.

### Rule: `molecule-single-responsibility` (HIGH)

Each molecule serves one cohesive function. If you need "and" to describe it, split it.

### Examples

#### SearchForm Molecule

**Phlex (Rails)**
```ruby
# backend/app/components/molecules/search_form.rb
class Components::Molecules::SearchForm < Components::Base
  def initialize(placeholder: "Search...", action: nil, method: :get)
    @placeholder = placeholder
    @action = action
    @method = method
  end

  def view_template
    form(action: @action, method: @method, class: "flex items-center gap-2") do
      render Components::Atoms::Input.new(
        name: "q",
        type: :search,
        placeholder: @placeholder,
      )
      render Components::Atoms::Button.new(
        label: "Search",
        type: :submit,
        variant: :primary,
      )
    end
  end
end
```

**ReactJS (Vite SPA)**
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
```

**Next.js (App Router)**
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

**React Native**
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
```

#### FormField Molecule

**Phlex (Rails)**
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

**ReactJS / Next.js**
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
      {error && (
        <HelpText id={`${name}-error`} variant="error">
          {error}
        </HelpText>
      )}
    </div>
  );
}
```

#### Other Common Molecules

| Molecule | Atoms Used | Purpose |
|----------|-----------|---------|
| `NavLink` | Icon + Link | Navigation link with icon |
| `StatCard` | Heading + Text | Single metric display |
| `UserMenu` | Avatar + Text + Icon | User dropdown trigger |
| `Breadcrumb` | Link + Icon | Navigation breadcrumbs |
| `FilterGroup` | Label + Select | Labeled dropdown filter |
| `SortSelector` | Label + Select | Sort field selector |
| `Pagination` | Button + Text | Page navigation |
| `AvatarGroup` | Avatar (multiple) | Grouped user avatars |

---

## 4. Organisms

### Rule: `organism-section-boundary` (MEDIUM)

Organisms represent distinct, recognizable interface sections.

### Rule: `organism-data-awareness` (MEDIUM)

Organisms are the lowest level that can fetch data or access global state.

### Examples

#### Header Organism

**Phlex (Rails)**
```ruby
# backend/app/components/organisms/header.rb
class Components::Organisms::Header < Components::Base
  def initialize(current_user:, notifications_count: 0)
    @current_user = current_user
    @notifications_count = notifications_count
  end

  def view_template
    header(class: "sticky top-0 z-40 border-b border-gray-200 bg-white") do
      div(class: "mx-auto flex h-16 max-w-7xl items-center justify-between px-4") do
        render Components::Atoms::Logo.new(size: :md)
        render_navigation
        render_actions
      end
    end
  end

  private

  def render_navigation
    nav(class: "hidden md:flex items-center gap-6", aria_label: "Main navigation") do
      render Components::Molecules::NavLink.new(label: "Dashboard", href: "/dashboard", icon: :home)
      render Components::Molecules::NavLink.new(label: "Projects", href: "/projects", icon: :folder)
      render Components::Molecules::NavLink.new(label: "Reports", href: "/reports", icon: :chart)
    end
  end

  def render_actions
    div(class: "flex items-center gap-4") do
      render Components::Molecules::SearchForm.new(placeholder: "Search...")
      render Components::Atoms::IconButton.new(icon: :bell, badge_count: @notifications_count)
      render Components::Molecules::UserMenu.new(user: @current_user)
    end
  end
end
```

**ReactJS (Vite SPA)**
```tsx
// web/src/components/organisms/Header/Header.tsx
import { Logo } from "@/components/atoms/Logo";
import { IconButton } from "@/components/atoms/IconButton";
import { NavLink } from "@/components/molecules/NavLink";
import { SearchForm } from "@/components/molecules/SearchForm";
import { UserMenu } from "@/components/molecules/UserMenu";

interface HeaderProps {
  currentUser: User;
  notificationsCount?: number;
  onSearch: (query: string) => void;
}

export function Header({ currentUser, notificationsCount = 0, onSearch }: HeaderProps) {
  return (
    <header className="sticky top-0 z-40 border-b border-gray-200 bg-white">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4">
        <Logo size="md" />
        <nav className="hidden md:flex items-center gap-6" aria-label="Main navigation">
          <NavLink label="Dashboard" href="/dashboard" icon="home" />
          <NavLink label="Projects" href="/projects" icon="folder" />
          <NavLink label="Reports" href="/reports" icon="chart" />
        </nav>
        <div className="flex items-center gap-4">
          <SearchForm placeholder="Search..." onSubmit={onSearch} />
          <IconButton icon="bell" badgeCount={notificationsCount} aria-label="Notifications" />
          <UserMenu user={currentUser} />
        </div>
      </div>
    </header>
  );
}
```

#### Data-Aware Organism

**ReactJS (Vite SPA) -- with TanStack Query**
```tsx
// web/src/components/organisms/MetricsGrid/MetricsGrid.tsx
import { useQuery } from "@tanstack/react-query";
import { Heading } from "@/components/atoms/Heading";
import { Spinner } from "@/components/atoms/Spinner";
import { Text } from "@/components/atoms/Text";
import { StatCard } from "@/components/molecules/StatCard";
import { fetchMetrics } from "@/api/dashboard";

export function MetricsGrid() {
  const { data: metrics, isLoading, error } = useQuery({
    queryKey: ["dashboard", "metrics"],
    queryFn: fetchMetrics,
  });

  if (isLoading) return <Spinner />;
  if (error) return <Text color="error">Failed to load metrics</Text>;

  return (
    <section aria-label="Key metrics">
      <Heading level={2}>Overview</Heading>
      <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {metrics?.map((metric) => (
          <StatCard
            key={metric.id}
            title={metric.label}
            value={metric.formattedValue}
            trend={metric.trend}
          />
        ))}
      </div>
    </section>
  );
}
```

**Next.js (App Router) -- Server Component**
```tsx
// next/src/components/organisms/MetricsGrid/MetricsGrid.tsx
import { Heading } from "@/components/atoms/Heading";
import { StatCard } from "@/components/molecules/StatCard";
import { getMetrics } from "@/lib/api/dashboard";

export async function MetricsGrid() {
  const metrics = await getMetrics();

  return (
    <section aria-label="Key metrics">
      <Heading level={2}>Overview</Heading>
      <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {metrics.map((metric) => (
          <StatCard
            key={metric.id}
            title={metric.label}
            value={metric.formattedValue}
            trend={metric.trend}
          />
        ))}
      </div>
    </section>
  );
}
```

---

## 5. Templates

### Rule: `template-layout-skeleton` (MEDIUM)

Templates define spatial layout using slots. No data fetching, no hardcoded content.

### Examples

#### DashboardLayout Template

**Phlex (Rails)**
```ruby
# backend/app/components/templates/dashboard_layout.rb
class Components::Templates::DashboardLayout < Components::Base
  def initialize(sidebar: true)
    @show_sidebar = sidebar
  end

  def view_template(&block)
    div(class: "min-h-screen bg-gray-50") do
      yield(:header) if block

      div(class: "mx-auto max-w-7xl px-4 py-6") do
        div(class: "flex gap-8") do
          if @show_sidebar
            aside(class: "w-64 shrink-0", aria_label: "Sidebar") do
              yield(:sidebar) if block
            end
          end

          main(class: "flex-1 min-w-0", role: "main") do
            yield(:content) if block
          end
        end
      end

      footer(class: "border-t border-gray-200 bg-white mt-auto") do
        yield(:footer) if block
      end
    end
  end
end
```

**ReactJS / Next.js**
```tsx
// web/src/components/templates/DashboardLayout/DashboardLayout.tsx
import { type ReactNode } from "react";

interface DashboardLayoutProps {
  header: ReactNode;
  sidebar?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
}

export function DashboardLayout({ header, sidebar, children, footer }: DashboardLayoutProps) {
  return (
    <div className="min-h-screen bg-gray-50">
      {header}
      <div className="mx-auto max-w-7xl px-4 py-6">
        <div className="flex gap-8">
          {sidebar && (
            <aside className="w-64 shrink-0" aria-label="Sidebar">{sidebar}</aside>
          )}
          <main className="flex-1 min-w-0" role="main">{children}</main>
        </div>
      </div>
      {footer && <footer className="border-t border-gray-200 bg-white mt-auto">{footer}</footer>}
    </div>
  );
}
```

**React Native**
```tsx
// mobile/src/components/templates/DashboardLayout/DashboardLayout.tsx
import { type ReactNode } from "react";
import { View, ScrollView, SafeAreaView } from "react-native";

interface DashboardLayoutProps {
  header: ReactNode;
  children: ReactNode;
  bottomNav?: ReactNode;
}

export function DashboardLayout({ header, children, bottomNav }: DashboardLayoutProps) {
  return (
    <SafeAreaView className="flex-1 bg-gray-50">
      {header}
      <ScrollView className="flex-1" contentContainerStyle={{ padding: 16 }}>
        {children}
      </ScrollView>
      {bottomNav && (
        <View className="border-t border-gray-200 bg-white">{bottomNav}</View>
      )}
    </SafeAreaView>
  );
}
```

---

## 6. Pages

### Rule: `page-template-instance` (MEDIUM)

Pages populate templates with real data. They are route entry points.

### Examples

#### Dashboard Page

**Phlex (Rails)**
```ruby
# backend/app/views/dashboard/show.rb
class Views::Dashboard::Show < Views::Base
  def initialize(current_user:, metrics:, activities:)
    @current_user = current_user
    @metrics = metrics
    @activities = activities
  end

  def view_template
    render Components::Templates::DashboardLayout.new do |layout|
      layout.header do
        render Components::Organisms::Header.new(
          current_user: @current_user,
          notifications_count: @current_user.unread_notifications_count,
        )
      end

      layout.sidebar do
        render Components::Organisms::Sidebar.new(
          nav_items: nav_items,
          active_item: :dashboard,
        )
      end

      layout.content do
        render Components::Atoms::Heading.new(text: "Dashboard", level: 1)
        render Components::Organisms::MetricsGrid.new(metrics: @metrics)
        render Components::Organisms::ActivityFeed.new(activities: @activities)
      end
    end
  end

  private

  def nav_items
    [
      { label: "Dashboard", href: dashboard_path, icon: :home },
      { label: "Articles", href: articles_path, icon: :document },
      { label: "Settings", href: settings_path, icon: :cog },
    ]
  end
end

# Controller:
# class DashboardController < ApplicationController
#   def show
#     render Views::Dashboard::Show.new(
#       current_user: current_user,
#       metrics: DashboardService.metrics(current_user),
#       activities: Activity.recent.limit(10),
#     )
#   end
# end
```

**ReactJS (Vite SPA)**
```tsx
// web/src/pages/DashboardPage.tsx
import { useQuery } from "@tanstack/react-query";
import { DashboardLayout } from "@/components/templates/DashboardLayout";
import { Header } from "@/components/organisms/Header";
import { Sidebar } from "@/components/organisms/Sidebar";
import { MetricsGrid } from "@/components/organisms/MetricsGrid";
import { ActivityFeed } from "@/components/organisms/ActivityFeed";
import { Heading } from "@/components/atoms/Heading";
import { Spinner } from "@/components/atoms/Spinner";
import { useAuthStore } from "@/stores/authStore";
import { fetchDashboardData } from "@/api/dashboard";

export function DashboardPage() {
  const currentUser = useAuthStore((s) => s.user);
  const { data, isLoading } = useQuery({
    queryKey: ["dashboard"],
    queryFn: fetchDashboardData,
  });

  if (isLoading) return <Spinner />;

  return (
    <DashboardLayout
      header={<Header currentUser={currentUser} onSearch={console.log} />}
      sidebar={<Sidebar navItems={NAV_ITEMS} activeItem="dashboard" />}
    >
      <Heading level={1}>Dashboard</Heading>
      <MetricsGrid metrics={data!.metrics} />
      <ActivityFeed activities={data!.activities} />
    </DashboardLayout>
  );
}

const NAV_ITEMS = [
  { label: "Dashboard", href: "/dashboard", icon: "home" },
  { label: "Articles", href: "/articles", icon: "document" },
  { label: "Settings", href: "/settings", icon: "cog" },
];
```

**Next.js (App Router)**
```tsx
// next/app/dashboard/page.tsx
import { Suspense } from "react";
import { DashboardLayout } from "@/components/templates/DashboardLayout";
import { Header } from "@/components/organisms/Header";
import { Sidebar } from "@/components/organisms/Sidebar";
import { MetricsGrid } from "@/components/organisms/MetricsGrid";
import { ActivityFeed } from "@/components/organisms/ActivityFeed";
import { Heading } from "@/components/atoms/Heading";
import { Spinner } from "@/components/atoms/Spinner";
import { getCurrentUser } from "@/lib/auth";

export const metadata = {
  title: "Dashboard",
  description: "Overview of key metrics and recent activity",
};

export default async function DashboardPage() {
  const currentUser = await getCurrentUser();

  return (
    <DashboardLayout
      header={<Header currentUser={currentUser} />}
      sidebar={<Sidebar navItems={NAV_ITEMS} activeItem="dashboard" />}
    >
      <Heading level={1}>Dashboard</Heading>
      <Suspense fallback={<Spinner />}>
        <MetricsGrid />
      </Suspense>
      <Suspense fallback={<Spinner />}>
        <ActivityFeed />
      </Suspense>
    </DashboardLayout>
  );
}

const NAV_ITEMS = [
  { label: "Dashboard", href: "/dashboard", icon: "home" },
  { label: "Articles", href: "/articles", icon: "document" },
  { label: "Settings", href: "/settings", icon: "cog" },
];
```

**React Native**
```tsx
// mobile/src/screens/DashboardScreen.tsx
import { useQuery } from "@tanstack/react-query";
import { DashboardLayout } from "@/components/templates/DashboardLayout";
import { Header } from "@/components/organisms/Header";
import { MetricsGrid } from "@/components/organisms/MetricsGrid";
import { ActivityFeed } from "@/components/organisms/ActivityFeed";
import { Heading } from "@/components/atoms/Heading";
import { Spinner } from "@/components/atoms/Spinner";
import { useAuthStore } from "@/stores/authStore";
import { fetchDashboardData } from "@/api/dashboard";
import { useNavigation } from "@react-navigation/native";

export function DashboardScreen() {
  const navigation = useNavigation();
  const currentUser = useAuthStore((s) => s.user);
  const { data, isLoading } = useQuery({
    queryKey: ["dashboard"],
    queryFn: fetchDashboardData,
  });

  if (isLoading) return <Spinner />;

  return (
    <DashboardLayout
      header={
        <Header
          currentUser={currentUser}
          onSearch={(q) => navigation.navigate("Search", { query: q })}
          onNotificationsPress={() => navigation.navigate("Notifications")}
          onProfilePress={() => navigation.navigate("Profile")}
        />
      }
    >
      <Heading level={1}>Dashboard</Heading>
      <MetricsGrid metrics={data!.metrics} />
      <ActivityFeed activities={data!.activities} />
    </DashboardLayout>
  );
}
```

---

## 7. Organization

### Directory Structure

See rule `org-directory-structure` for complete directory trees for all 4 platforms.

### Naming Conventions

See rule `org-naming-conventions` for platform-specific naming tables.

### Key Conventions Summary

| Platform | Files | Components | Pages |
|----------|-------|-----------|-------|
| Phlex | `snake_case.rb` | `Components::Level::Name` | `Views::Resource::Action` |
| ReactJS | `PascalCase.tsx` | `export function Name` | `DashboardPage.tsx` |
| Next.js | `PascalCase.tsx` / `page.tsx` | `export function Name` | `page.tsx` (convention) |
| React Native | `PascalCase.tsx` | `export function Name` | `DashboardScreen.tsx` |

---

## 8. Decision Tree: Determining the Right Atomic Level

Use this flowchart to classify any component:

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

### Quick Classification Questions

| Question | If Yes |
|----------|--------|
| Is it a single styled HTML element? | Atom |
| Does it only use atoms and serve one purpose? | Molecule |
| Does it represent a distinct UI section? | Organism |
| Does it define where things go without saying what? | Template |
| Is it a route entry point with real data? | Page |

---

## 9. Common Mistakes and How to Fix Them

### Mistake 1: Atoms Composing Atoms

**Problem:** An `IconButton` in `atoms/` that imports `Icon` and `Button`.

**Fix:** Move `IconButton` to `molecules/` since it composes two atoms.

### Mistake 2: Molecules Fetching Data

**Problem:** A `UserCard` molecule using `useQuery` to fetch user data.

**Fix:** Make the molecule accept display-ready props (`name`, `avatarUrl`). Move data fetching to the parent organism or page.

### Mistake 3: Organisms Handling Layout

**Problem:** An organism that defines full-page grid structure with sidebars and headers.

**Fix:** Extract the layout structure into a template. The organism should be a section within the template.

### Mistake 4: Templates With Hardcoded Content

**Problem:** A `DashboardLayout` that renders `<h1>Dashboard</h1>` and specific metrics.

**Fix:** Replace hardcoded content with slots (`children`, `header`, `sidebar`). Pages fill the slots with real content.

### Mistake 5: Pages Reimplementing Layout

**Problem:** Every page manually builds `<div className="min-h-screen"><header>...</header><main>...</main></div>`.

**Fix:** Extract the repeated layout into a template and use it across pages.

### Mistake 6: Level In The Name

**Problem:** `AtomButton.tsx`, `MoleculeSearchForm.tsx`, `OrganismHeader.tsx`.

**Fix:** The directory already indicates the level. Name components by what they are: `Button.tsx`, `SearchForm.tsx`, `Header.tsx`.

### Mistake 7: Skipping Levels

**Problem:** A page directly composing atoms without templates or organisms.

**Fix:** While not strictly forbidden, consider whether the page would benefit from reusable organisms and a template. The hierarchy exists to promote reusability.

### Mistake 8: Too Many Props On Atoms

**Problem:** An atom with 15 props covering every possible variation.

**Fix:** Keep atoms minimal. If an atom needs many configuration options, consider whether it should be split into multiple atoms or if the variations should be handled by the consuming molecule.

---

## 10. Cross-Platform Considerations

### Shared vs. Platform-Specific

Some components exist across all platforms (Button, Input) but have different implementations. They share:
- The same atomic classification
- The same semantic purpose
- The same prop interface (where possible)

They differ in:
- The rendering primitives (`<button>` vs `<Pressable>`)
- Styling approaches (Tailwind CSS vs NativeWind)
- Platform-specific features (Server Components in Next.js, `accessibilityRole` in React Native)

### Server Components (Next.js)

In Next.js App Router:
- **Atoms, Molecules, Templates**: Can be Server Components (no `"use client"` needed) if they have no interactivity
- **Organisms**: May be Server Components if they fetch data server-side, or Client Components if they use hooks
- **Pages**: Are Server Components by default (`page.tsx` files)
- Add `"use client"` only when the component uses `useState`, `useEffect`, event handlers, or browser APIs

### Phlex Integration

In Rails with Phlex:
- Controllers prepare data and render Phlex views (pages)
- Views compose templates and organisms
- Data flows from controller -> view -> template -> organism -> molecule -> atom
- Use `render ComponentClass.new(...)` to compose components
- Use `yield` blocks for template slot injection
