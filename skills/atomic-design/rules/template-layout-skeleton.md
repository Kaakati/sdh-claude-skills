---
title: "Templates Are Layout Skeletons"
id: template-layout-skeleton
impact: MEDIUM
tags: [atomic-design, templates]
platforms: [phlex, reactjs, nextjs, react-native]
---

# Templates Are Layout Skeletons

Templates define page-level layout structure by arranging organisms, molecules, and atoms into a spatial composition. They determine WHERE content goes but not WHAT the content is. Templates use placeholder or slot-based patterns and never fetch data or contain business logic.

## Incorrect

A template that fetches data or contains business logic -- this is a page, not a template.

```tsx
// WRONG: Template fetching data
export function DashboardLayout() {
  const { data: user } = useQuery({ queryKey: ["user"], queryFn: fetchUser });
  const { data: stats } = useQuery({ queryKey: ["stats"], queryFn: fetchStats });

  return (
    <div className="min-h-screen">
      <Header user={user} />
      <Sidebar />
      <main>
        <StatsGrid stats={stats} />
      </main>
    </div>
  );
}
```

A template with hardcoded content instead of slots.

```tsx
// WRONG: Template with hardcoded content
export function DashboardLayout() {
  return (
    <div className="min-h-screen">
      <header>
        <h1>Dashboard</h1>
        <p>Welcome back, John!</p>
      </header>
      <main>
        <div>Revenue: $42,000</div>
        <div>Users: 1,234</div>
      </main>
    </div>
  );
}
```

## Correct

Templates define the layout skeleton with content slots that pages fill with real data.

### Phlex (Rails)

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
        div(class: layout_classes) do
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

      footer(class: "border-t border-gray-200 bg-white") do
        yield(:footer) if block
      end
    end
  end

  private

  def layout_classes
    base = "flex gap-8"
    @show_sidebar ? base : "#{base} justify-center"
  end
end
```

```ruby
# backend/app/components/templates/auth_layout.rb
class Components::Templates::AuthLayout < Components::Base
  def view_template(&block)
    div(class: "flex min-h-screen items-center justify-center bg-gray-50 px-4") do
      div(class: "w-full max-w-md") do
        div(class: "mb-8 text-center") do
          yield(:branding) if block
        end

        div(class: "rounded-xl bg-white p-8 shadow-sm") do
          yield(:form) if block
        end

        div(class: "mt-4 text-center text-sm text-gray-500") do
          yield(:footer) if block
        end
      end
    end
  end
end
```

### ReactJS (Vite SPA)

```tsx
// web/src/components/templates/DashboardLayout/DashboardLayout.tsx
import { type ReactNode } from "react";

interface DashboardLayoutProps {
  header: ReactNode;
  sidebar?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
}

export function DashboardLayout({
  header,
  sidebar,
  children,
  footer,
}: DashboardLayoutProps) {
  return (
    <div className="min-h-screen bg-gray-50">
      {header}

      <div className="mx-auto max-w-7xl px-4 py-6">
        <div className="flex gap-8">
          {sidebar && (
            <aside className="w-64 shrink-0" aria-label="Sidebar">
              {sidebar}
            </aside>
          )}

          <main className="flex-1 min-w-0" role="main">
            {children}
          </main>
        </div>
      </div>

      {footer && (
        <footer className="border-t border-gray-200 bg-white">
          {footer}
        </footer>
      )}
    </div>
  );
}
```

```tsx
// web/src/components/templates/AuthLayout/AuthLayout.tsx
import { type ReactNode } from "react";

interface AuthLayoutProps {
  branding: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
}

export function AuthLayout({ branding, children, footer }: AuthLayoutProps) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">{branding}</div>

        <div className="rounded-xl bg-white p-8 shadow-sm">{children}</div>

        {footer && (
          <div className="mt-4 text-center text-sm text-gray-500">{footer}</div>
        )}
      </div>
    </div>
  );
}
```

### Next.js (App Router)

```tsx
// next/src/components/templates/DashboardLayout/DashboardLayout.tsx
import { type ReactNode } from "react";

interface DashboardLayoutProps {
  header: ReactNode;
  sidebar?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
}

export function DashboardLayout({
  header,
  sidebar,
  children,
  footer,
}: DashboardLayoutProps) {
  return (
    <div className="min-h-screen bg-gray-50">
      {header}

      <div className="mx-auto max-w-7xl px-4 py-6">
        <div className="flex gap-8">
          {sidebar && (
            <aside className="w-64 shrink-0" aria-label="Sidebar">
              {sidebar}
            </aside>
          )}

          <main className="flex-1 min-w-0" role="main">
            {children}
          </main>
        </div>
      </div>

      {footer && (
        <footer className="border-t border-gray-200 bg-white">
          {footer}
        </footer>
      )}
    </div>
  );
}
```

### React Native

```tsx
// mobile/src/components/templates/DashboardLayout/DashboardLayout.tsx
import { type ReactNode } from "react";
import { View, ScrollView, SafeAreaView } from "react-native";

interface DashboardLayoutProps {
  header: ReactNode;
  children: ReactNode;
  bottomNav?: ReactNode;
}

export function DashboardLayout({
  header,
  children,
  bottomNav,
}: DashboardLayoutProps) {
  return (
    <SafeAreaView className="flex-1 bg-gray-50">
      {header}

      <ScrollView
        className="flex-1"
        contentContainerStyle={{ paddingHorizontal: 16, paddingVertical: 24 }}
      >
        {children}
      </ScrollView>

      {bottomNav && (
        <View className="border-t border-gray-200 bg-white">
          {bottomNav}
        </View>
      )}
    </SafeAreaView>
  );
}
```

```tsx
// mobile/src/components/templates/AuthLayout/AuthLayout.tsx
import { type ReactNode } from "react";
import { View, ScrollView, KeyboardAvoidingView, Platform } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

interface AuthLayoutProps {
  branding: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
}

export function AuthLayout({ branding, children, footer }: AuthLayoutProps) {
  return (
    <SafeAreaView className="flex-1 bg-gray-50">
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        className="flex-1"
      >
        <ScrollView
          contentContainerStyle={{ flexGrow: 1, justifyContent: "center", padding: 16 }}
          keyboardShouldPersistTaps="handled"
        >
          <View className="mb-8 items-center">{branding}</View>

          <View className="rounded-2xl bg-white p-6 shadow-sm">
            {children}
          </View>

          {footer && (
            <View className="mt-4 items-center">{footer}</View>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
```

## Additional Context

**Template characteristics:**
- Define spatial arrangement (grid, flexbox, positioning)
- Use slots/children/yield for content injection
- Apply layout-specific styles (max-width, padding, gaps)
- Handle responsive breakpoints for layout shifts
- Never fetch data or contain business logic
- Never hardcode text content or dynamic values

**Common templates:**

| Template | Slots | Use Case |
|----------|-------|----------|
| `DashboardLayout` | header, sidebar, content, footer | Admin dashboards |
| `AuthLayout` | branding, form, footer | Login, signup, reset password |
| `MarketingLayout` | hero, features, cta, footer | Landing pages |
| `DetailLayout` | breadcrumb, content, related | Detail/show pages |
| `ListLayout` | filters, content, pagination | Index/list pages |

**Template vs. organism:**
- An organism is a self-contained section (Header, Sidebar)
- A template arranges multiple organisms into a full-page skeleton
- Templates have NO visual identity of their own -- they are purely structural

**Next.js layout.tsx vs. templates:**
- Next.js `layout.tsx` files in the `app/` directory serve as persistent layouts across route segments
- Atomic Design templates are reusable layout components used within pages
- They can work together: a `layout.tsx` may use an Atomic Design template internally
