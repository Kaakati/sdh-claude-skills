---
title: "Pages Are Template Instances"
id: page-template-instance
impact: MEDIUM
tags: [atomic-design, pages]
platforms: [phlex, reactjs, nextjs, react-native]
---

# Pages Are Template Instances

Pages are specific instances of templates populated with real data. They are the entry points where data fetching, routing, and business logic connect to the UI. Pages compose templates with organisms and pass real data down through the component tree.

## Platform Entry Points

| Platform | Page Location | Naming |
|----------|--------------|--------|
| Phlex (Rails) | `backend/app/views/` | `Views::Articles::Index` |
| ReactJS (Vite SPA) | `web/src/pages/` | `DashboardPage.tsx` |
| Next.js (App Router) | `next/app/` | `page.tsx` (convention) |
| React Native | `mobile/src/screens/` | `DashboardScreen.tsx` |

## Incorrect

A page that builds layout from scratch instead of using a template.

```tsx
// WRONG: Page reimplements layout instead of using a template
export function DashboardPage() {
  const { data } = useQuery({ queryKey: ["metrics"], queryFn: fetchMetrics });

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="sticky top-0 z-40 border-b bg-white">
        <div className="mx-auto flex h-16 max-w-7xl items-center px-4">
          {/* Manually building header layout... */}
        </div>
      </header>
      <div className="mx-auto max-w-7xl px-4 py-6">
        <div className="flex gap-8">
          <aside className="w-64">
            {/* Manually building sidebar layout... */}
          </aside>
          <main className="flex-1">
            {/* Content... */}
          </main>
        </div>
      </div>
    </div>
  );
}
```

## Correct

Pages use templates for layout and populate them with real data via organisms.

### Phlex (Rails)

```ruby
# backend/app/views/base.rb
class Views::Base < Phlex::HTML
  include Phlex::Rails::Helpers::Routes
end

# backend/app/views/articles/index.rb
class Views::Articles::Index < Views::Base
  def initialize(articles:, current_user:, filters:)
    @articles = articles
    @current_user = current_user
    @filters = filters
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
          nav_items: sidebar_nav_items,
          active_item: :articles,
        )
        render Components::Organisms::FilterPanel.new(
          filters: @filters,
          applied: params[:filters],
        )
      end

      layout.content do
        render Components::Atoms::Heading.new(text: "Articles", level: 1)
        render Components::Organisms::ArticleList.new(articles: @articles)
        render Components::Molecules::Pagination.new(
          collection: @articles,
          path: articles_path,
        )
      end
    end
  end

  private

  def sidebar_nav_items
    [
      { label: "Dashboard", href: dashboard_path, icon: :home },
      { label: "Articles", href: articles_path, icon: :document },
      { label: "Users", href: users_path, icon: :users },
    ]
  end
end

# backend/app/views/articles/show.rb
class Views::Articles::Show < Views::Base
  def initialize(article:, current_user:, related_articles:)
    @article = article
    @current_user = current_user
    @related_articles = related_articles
  end

  def view_template
    render Components::Templates::DetailLayout.new do |layout|
      layout.header do
        render Components::Organisms::Header.new(current_user: @current_user)
      end

      layout.breadcrumb do
        render Components::Molecules::Breadcrumb.new(
          items: [
            { label: "Articles", href: articles_path },
            { label: @article.title },
          ],
        )
      end

      layout.content do
        render Components::Organisms::ArticleDetail.new(article: @article)
        render Components::Organisms::CommentThread.new(
          comments: @article.comments,
          current_user: @current_user,
        )
      end

      layout.related do
        render Components::Organisms::RelatedArticles.new(articles: @related_articles)
      end
    end
  end
end
```

### ReactJS (Vite SPA)

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
import { fetchDashboardMetrics, fetchRecentActivity } from "@/api/dashboard";
import { useAuthStore } from "@/stores/authStore";

export function DashboardPage() {
  const currentUser = useAuthStore((state) => state.user);

  const { data: metrics, isLoading: isMetricsLoading } = useQuery({
    queryKey: ["dashboard", "metrics"],
    queryFn: fetchDashboardMetrics,
  });

  const { data: activities, isLoading: isActivitiesLoading } = useQuery({
    queryKey: ["dashboard", "activities"],
    queryFn: fetchRecentActivity,
  });

  return (
    <DashboardLayout
      header={
        <Header
          currentUser={currentUser}
          onSearch={(q) => console.log("Search:", q)}
        />
      }
      sidebar={
        <Sidebar
          navItems={[
            { label: "Dashboard", href: "/dashboard", icon: "home" },
            { label: "Articles", href: "/articles", icon: "document" },
            { label: "Users", href: "/users", icon: "users" },
          ]}
          activeItem="dashboard"
        />
      }
    >
      <Heading level={1}>Dashboard</Heading>

      {isMetricsLoading ? (
        <Spinner />
      ) : (
        <MetricsGrid metrics={metrics!} />
      )}

      {isActivitiesLoading ? (
        <Spinner />
      ) : (
        <ActivityFeed activities={activities!} />
      )}
    </DashboardLayout>
  );
}
```

### Next.js (App Router)

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
import { getDashboardMetrics, getRecentActivity } from "@/lib/api/dashboard";

export const metadata = {
  title: "Dashboard",
  description: "Overview of key metrics and recent activity",
};

export default async function DashboardPage() {
  const currentUser = await getCurrentUser();
  const [metrics, activities] = await Promise.all([
    getDashboardMetrics(),
    getRecentActivity(),
  ]);

  return (
    <DashboardLayout
      header={<Header currentUser={currentUser} />}
      sidebar={
        <Sidebar
          navItems={[
            { label: "Dashboard", href: "/dashboard", icon: "home" },
            { label: "Articles", href: "/articles", icon: "document" },
            { label: "Users", href: "/users", icon: "users" },
          ]}
          activeItem="dashboard"
        />
      }
    >
      <Heading level={1}>Dashboard</Heading>

      <Suspense fallback={<Spinner />}>
        <MetricsGrid metrics={metrics} />
      </Suspense>

      <Suspense fallback={<Spinner />}>
        <ActivityFeed activities={activities} />
      </Suspense>
    </DashboardLayout>
  );
}
```

### React Native

```tsx
// mobile/src/screens/DashboardScreen.tsx
import { useQuery } from "@tanstack/react-query";
import { DashboardLayout } from "@/components/templates/DashboardLayout";
import { Header } from "@/components/organisms/Header";
import { MetricsGrid } from "@/components/organisms/MetricsGrid";
import { ActivityFeed } from "@/components/organisms/ActivityFeed";
import { Heading } from "@/components/atoms/Heading";
import { Spinner } from "@/components/atoms/Spinner";
import { fetchDashboardMetrics, fetchRecentActivity } from "@/api/dashboard";
import { useAuthStore } from "@/stores/authStore";
import { useNavigation } from "@react-navigation/native";

export function DashboardScreen() {
  const navigation = useNavigation();
  const currentUser = useAuthStore((state) => state.user);

  const { data: metrics, isLoading: isMetricsLoading } = useQuery({
    queryKey: ["dashboard", "metrics"],
    queryFn: fetchDashboardMetrics,
  });

  const { data: activities, isLoading: isActivitiesLoading } = useQuery({
    queryKey: ["dashboard", "activities"],
    queryFn: fetchRecentActivity,
  });

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

      {isMetricsLoading ? <Spinner /> : <MetricsGrid metrics={metrics!} />}

      {isActivitiesLoading ? <Spinner /> : <ActivityFeed activities={activities!} />}
    </DashboardLayout>
  );
}
```

## Additional Context

**Page responsibilities:**
1. **Data fetching**: Pages initiate all data loading (TanStack Query, server-side fetch, controller assigns)
2. **Template selection**: Pages choose which template layout to use
3. **Organism composition**: Pages arrange organisms within template slots
4. **Routing**: Pages are route entry points (React Router, Next.js routes, Rails controller actions)
5. **SEO/Metadata**: Pages set page titles, meta tags, Open Graph data

**Pages are NOT reusable:**
- Each page is unique to a specific route/URL
- If you find yourself reusing a "page," it should be a template or organism

**Data flow pattern:**
```
Page (fetches data)
  -> Template (defines layout)
    -> Organism (receives data via props, may fetch its own sub-data)
      -> Molecule (receives display-ready props)
        -> Atom (receives primitive props)
```

**Rails controller integration:**
The Rails controller prepares data and renders the Phlex view:
```ruby
# backend/app/controllers/articles_controller.rb
class ArticlesController < ApplicationController
  def index
    articles = Article.published.order(created_at: :desc).page(params[:page])
    render Views::Articles::Index.new(
      articles: articles,
      current_user: current_user,
      filters: Article::FILTER_OPTIONS,
    )
  end
end
```
