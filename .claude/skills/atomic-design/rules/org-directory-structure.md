---
title: "Directory Structure"
id: org-directory-structure
impact: MEDIUM
tags: [atomic-design, organization]
platforms: [phlex, reactjs, nextjs, react-native]
---

# Directory Structure

Follow standard directory trees for all 4 platforms. Each atomic level has a dedicated directory. Components live under their atomic level, and pages/views live in their platform-specific location.

## Phlex (Rails)

```
backend/app/components/
├── base.rb                          # Base component class
├── atoms/
│   ├── avatar.rb                    # Components::Atoms::Avatar
│   ├── badge.rb                     # Components::Atoms::Badge
│   ├── button.rb                    # Components::Atoms::Button
│   ├── divider.rb                   # Components::Atoms::Divider
│   ├── heading.rb                   # Components::Atoms::Heading
│   ├── help_text.rb                 # Components::Atoms::HelpText
│   ├── icon.rb                      # Components::Atoms::Icon
│   ├── icon_button.rb               # Components::Atoms::IconButton
│   ├── input.rb                     # Components::Atoms::Input
│   ├── label.rb                     # Components::Atoms::Label
│   ├── link.rb                      # Components::Atoms::Link
│   ├── logo.rb                      # Components::Atoms::Logo
│   ├── select.rb                    # Components::Atoms::Select
│   ├── spinner.rb                   # Components::Atoms::Spinner
│   └── text.rb                      # Components::Atoms::Text
├── molecules/
│   ├── breadcrumb.rb                # Components::Molecules::Breadcrumb
│   ├── filter_group.rb              # Components::Molecules::FilterGroup
│   ├── form_field.rb                # Components::Molecules::FormField
│   ├── nav_link.rb                  # Components::Molecules::NavLink
│   ├── pagination.rb                # Components::Molecules::Pagination
│   ├── search_form.rb               # Components::Molecules::SearchForm
│   ├── sort_selector.rb             # Components::Molecules::SortSelector
│   ├── stat_card.rb                 # Components::Molecules::StatCard
│   └── user_menu.rb                 # Components::Molecules::UserMenu
├── organisms/
│   ├── article_detail.rb            # Components::Organisms::ArticleDetail
│   ├── article_list.rb              # Components::Organisms::ArticleList
│   ├── comment_thread.rb            # Components::Organisms::CommentThread
│   ├── filter_panel.rb              # Components::Organisms::FilterPanel
│   ├── footer.rb                    # Components::Organisms::Footer
│   ├── header.rb                    # Components::Organisms::Header
│   ├── metrics_grid.rb              # Components::Organisms::MetricsGrid
│   ├── product_grid.rb              # Components::Organisms::ProductGrid
│   └── sidebar.rb                   # Components::Organisms::Sidebar
└── templates/
    ├── auth_layout.rb               # Components::Templates::AuthLayout
    ├── dashboard_layout.rb          # Components::Templates::DashboardLayout
    ├── detail_layout.rb             # Components::Templates::DetailLayout
    └── marketing_layout.rb          # Components::Templates::MarketingLayout

backend/app/views/
├── base.rb                          # Views::Base
├── articles/
│   ├── index.rb                     # Views::Articles::Index (page)
│   ├── show.rb                      # Views::Articles::Show (page)
│   ├── new.rb                       # Views::Articles::New (page)
│   └── edit.rb                      # Views::Articles::Edit (page)
├── dashboard/
│   └── show.rb                      # Views::Dashboard::Show (page)
└── auth/
    ├── login.rb                     # Views::Auth::Login (page)
    └── register.rb                  # Views::Auth::Register (page)
```

## ReactJS (Vite SPA)

```
web/src/components/
├── atoms/
│   ├── Avatar/
│   │   ├── Avatar.tsx
│   │   └── index.ts                 # export { Avatar } from './Avatar'
│   ├── Badge/
│   │   ├── Badge.tsx
│   │   └── index.ts
│   ├── Button/
│   │   ├── Button.tsx
│   │   └── index.ts
│   ├── Heading/
│   │   ├── Heading.tsx
│   │   └── index.ts
│   ├── HelpText/
│   │   ├── HelpText.tsx
│   │   └── index.ts
│   ├── Icon/
│   │   ├── Icon.tsx
│   │   └── index.ts
│   ├── Input/
│   │   ├── Input.tsx
│   │   └── index.ts
│   ├── Label/
│   │   ├── Label.tsx
│   │   └── index.ts
│   ├── Select/
│   │   ├── Select.tsx
│   │   └── index.ts
│   ├── Spinner/
│   │   ├── Spinner.tsx
│   │   └── index.ts
│   └── Text/
│       ├── Text.tsx
│       └── index.ts
├── molecules/
│   ├── Breadcrumb/
│   │   ├── Breadcrumb.tsx
│   │   └── index.ts
│   ├── FilterGroup/
│   │   ├── FilterGroup.tsx
│   │   └── index.ts
│   ├── FormField/
│   │   ├── FormField.tsx
│   │   └── index.ts
│   ├── NavLink/
│   │   ├── NavLink.tsx
│   │   └── index.ts
│   ├── Pagination/
│   │   ├── Pagination.tsx
│   │   └── index.ts
│   ├── SearchForm/
│   │   ├── SearchForm.tsx
│   │   └── index.ts
│   ├── SortSelector/
│   │   ├── SortSelector.tsx
│   │   └── index.ts
│   └── UserMenu/
│       ├── UserMenu.tsx
│       └── index.ts
├── organisms/
│   ├── ActivityFeed/
│   │   ├── ActivityFeed.tsx
│   │   └── index.ts
│   ├── Header/
│   │   ├── Header.tsx
│   │   └── index.ts
│   ├── MetricsGrid/
│   │   ├── MetricsGrid.tsx
│   │   └── index.ts
│   ├── ProductGrid/
│   │   ├── ProductGrid.tsx
│   │   └── index.ts
│   └── Sidebar/
│       ├── Sidebar.tsx
│       └── index.ts
└── templates/
    ├── AuthLayout/
    │   ├── AuthLayout.tsx
    │   └── index.ts
    ├── DashboardLayout/
    │   ├── DashboardLayout.tsx
    │   └── index.ts
    └── DetailLayout/
        ├── DetailLayout.tsx
        └── index.ts

web/src/pages/
├── DashboardPage.tsx
├── ArticlesPage.tsx
├── ArticleDetailPage.tsx
├── LoginPage.tsx
└── RegisterPage.tsx
```

## Next.js (App Router)

```
next/src/components/
├── atoms/
│   ├── Avatar/
│   │   ├── Avatar.tsx
│   │   └── index.ts
│   ├── Badge/
│   │   ├── Badge.tsx
│   │   └── index.ts
│   ├── Button/
│   │   ├── Button.tsx
│   │   └── index.ts
│   ├── Heading/
│   │   ├── Heading.tsx
│   │   └── index.ts
│   ├── Icon/
│   │   ├── Icon.tsx
│   │   └── index.ts
│   ├── Input/
│   │   ├── Input.tsx
│   │   └── index.ts
│   ├── Label/
│   │   ├── Label.tsx
│   │   └── index.ts
│   ├── Select/
│   │   ├── Select.tsx
│   │   └── index.ts
│   ├── Spinner/
│   │   ├── Spinner.tsx
│   │   └── index.ts
│   └── Text/
│       ├── Text.tsx
│       └── index.ts
├── molecules/
│   ├── Breadcrumb/
│   │   ├── Breadcrumb.tsx
│   │   └── index.ts
│   ├── FilterGroup/
│   │   ├── FilterGroup.tsx
│   │   └── index.ts
│   ├── FormField/
│   │   ├── FormField.tsx
│   │   └── index.ts
│   ├── NavLink/
│   │   ├── NavLink.tsx
│   │   └── index.ts
│   ├── SearchForm/
│   │   ├── SearchForm.tsx
│   │   └── index.ts
│   └── UserMenu/
│       ├── UserMenu.tsx
│       └── index.ts
├── organisms/
│   ├── ActivityFeed/
│   │   ├── ActivityFeed.tsx
│   │   └── index.ts
│   ├── Header/
│   │   ├── Header.tsx
│   │   └── index.ts
│   ├── MetricsGrid/
│   │   ├── MetricsGrid.tsx
│   │   └── index.ts
│   └── Sidebar/
│       ├── Sidebar.tsx
│       └── index.ts
└── templates/
    ├── AuthLayout/
    │   ├── AuthLayout.tsx
    │   └── index.ts
    ├── DashboardLayout/
    │   ├── DashboardLayout.tsx
    │   └── index.ts
    └── DetailLayout/
        ├── DetailLayout.tsx
        └── index.ts

next/app/
├── layout.tsx                       # Root layout (persistent shell)
├── page.tsx                         # Home page
├── dashboard/
│   ├── layout.tsx                   # Dashboard layout (optional)
│   └── page.tsx                     # Dashboard page
├── articles/
│   ├── page.tsx                     # Articles list page
│   └── [slug]/
│       └── page.tsx                 # Article detail page
└── auth/
    ├── login/
    │   └── page.tsx                 # Login page
    └── register/
        └── page.tsx                 # Register page
```

## React Native

```
mobile/src/components/
├── atoms/
│   ├── Avatar/
│   │   ├── Avatar.tsx
│   │   └── index.ts
│   ├── Badge/
│   │   ├── Badge.tsx
│   │   └── index.ts
│   ├── Button/
│   │   ├── Button.tsx
│   │   └── index.ts
│   ├── Heading/
│   │   ├── Heading.tsx
│   │   └── index.ts
│   ├── Icon/
│   │   ├── Icon.tsx
│   │   └── index.ts
│   ├── Input/
│   │   ├── Input.tsx
│   │   └── index.ts
│   ├── Spinner/
│   │   ├── Spinner.tsx
│   │   └── index.ts
│   └── Text/
│       ├── Text.tsx
│       └── index.ts
├── molecules/
│   ├── FormField/
│   │   ├── FormField.tsx
│   │   └── index.ts
│   ├── SearchForm/
│   │   ├── SearchForm.tsx
│   │   └── index.ts
│   ├── FilterGroup/
│   │   ├── FilterGroup.tsx
│   │   └── index.ts
│   └── UserAvatar/
│       ├── UserAvatar.tsx
│       └── index.ts
├── organisms/
│   ├── ActivityFeed/
│   │   ├── ActivityFeed.tsx
│   │   └── index.ts
│   ├── Header/
│   │   ├── Header.tsx
│   │   └── index.ts
│   ├── MetricsGrid/
│   │   ├── MetricsGrid.tsx
│   │   └── index.ts
│   └── ProductList/
│       ├── ProductList.tsx
│       └── index.ts
└── templates/
    ├── AuthLayout/
    │   ├── AuthLayout.tsx
    │   └── index.ts
    ├── DashboardLayout/
    │   ├── DashboardLayout.tsx
    │   └── index.ts
    └── DetailLayout/
        ├── DetailLayout.tsx
        └── index.ts

mobile/src/screens/
├── DashboardScreen.tsx
├── ArticlesScreen.tsx
├── ArticleDetailScreen.tsx
├── LoginScreen.tsx
└── RegisterScreen.tsx
```

## Additional Context

**Key principles:**
- Each atomic level has its own directory -- never mix levels in the same folder
- React/Next.js/React Native use `PascalCase` directories with `index.ts` barrel exports
- Phlex uses `snake_case` files with namespaced classes
- Pages/views/screens live outside the components directory in platform-specific locations

**Barrel exports (React platforms):**
```tsx
// web/src/components/atoms/Button/index.ts
export { Button } from "./Button";
export type { ButtonProps } from "./Button";
```

**Base component (Phlex):**
```ruby
# backend/app/components/base.rb
class Components::Base < Phlex::HTML
  include Phlex::Rails::Helpers::Routes

  if Rails.env.development?
    def before_template
      comment { "#{self.class.name}" }
      super
    end
  end
end
```

**Co-located files:**
When a component grows, add co-located files within its directory:
```
Button/
├── Button.tsx          # Component implementation
├── Button.test.tsx     # Tests
├── Button.stories.tsx  # Storybook stories (optional)
├── useButton.ts        # Component-specific hook (if needed)
└── index.ts            # Barrel export
```
