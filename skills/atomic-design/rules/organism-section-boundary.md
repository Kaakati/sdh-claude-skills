---
title: "Organisms Define Section Boundaries"
id: organism-section-boundary
impact: MEDIUM
tags: [atomic-design, organisms]
platforms: [phlex, reactjs, nextjs, react-native]
---

# Organisms Define Section Boundaries

Organisms represent distinct, self-contained sections of an interface. They compose molecules and atoms into meaningful UI regions that serve a specific purpose within the page. An organism typically maps to a recognizable section a user can identify -- a header, a sidebar, a product grid, a comment thread.

## Incorrect

An organism that is too granular -- just wrapping a single molecule without adding meaningful composition.

```tsx
// WRONG: This is just a molecule wrapper, not a distinct section
export function SearchSection() {
  return (
    <div>
      <SearchForm onSubmit={handleSearch} />
    </div>
  );
}
```

An organism that tries to be the entire page -- too much responsibility.

```tsx
// WRONG: This is a page, not an organism
export function Dashboard() {
  const { data: metrics } = useQuery({ queryKey: ["metrics"], queryFn: fetchMetrics });
  const { data: activities } = useQuery({ queryKey: ["activities"], queryFn: fetchActivities });
  const { data: users } = useQuery({ queryKey: ["users"], queryFn: fetchUsers });

  return (
    <div>
      <nav>...</nav>
      <header>...</header>
      <main>
        <MetricsGrid data={metrics} />
        <ActivityFeed data={activities} />
        <UserList data={users} />
      </main>
      <footer>...</footer>
    </div>
  );
}
```

## Correct

Organisms compose multiple molecules and atoms into a distinct, recognizable interface section.

### Phlex (Rails)

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
        render_logo
        render_navigation
        render_actions
      end
    end
  end

  private

  def render_logo
    render Components::Atoms::Logo.new(size: :md)
  end

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

```ruby
# backend/app/components/organisms/product_grid.rb
class Components::Organisms::ProductGrid < Components::Base
  def initialize(products:, columns: 3)
    @products = products
    @columns = columns
  end

  def view_template
    section(class: "py-8", aria_label: "Product listing") do
      div(class: "flex items-center justify-between mb-6") do
        render Components::Atoms::Heading.new(text: "Products", level: 2)
        render Components::Molecules::SortSelector.new(
          fields: [
            { value: "name", label: "Name" },
            { value: "price", label: "Price" },
            { value: "rating", label: "Rating" },
          ],
        )
      end
      div(class: grid_classes) do
        @products.each do |product|
          render Components::Molecules::ProductCard.new(product: product)
        end
      end
    end
  end

  private

  def grid_classes
    "grid gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-#{@columns}"
  end
end
```

### ReactJS (Vite SPA)

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

export function Header({
  currentUser,
  notificationsCount = 0,
  onSearch,
}: HeaderProps) {
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

### Next.js (App Router)

```tsx
// next/src/components/organisms/Header/Header.tsx
import { Logo } from "@/components/atoms/Logo";
import { IconButton } from "@/components/atoms/IconButton";
import { NavLink } from "@/components/molecules/NavLink";
import { SearchForm } from "@/components/molecules/SearchForm";
import { UserMenu } from "@/components/molecules/UserMenu";

interface HeaderProps {
  currentUser: User;
  notificationsCount?: number;
}

export function Header({ currentUser, notificationsCount = 0 }: HeaderProps) {
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
          <SearchForm placeholder="Search..." />
          <IconButton icon="bell" badgeCount={notificationsCount} aria-label="Notifications" />
          <UserMenu user={currentUser} />
        </div>
      </div>
    </header>
  );
}
```

### React Native

```tsx
// mobile/src/components/organisms/Header/Header.tsx
import { View, SafeAreaView } from "react-native";
import { Logo } from "@/components/atoms/Logo";
import { IconButton } from "@/components/atoms/IconButton";
import { SearchForm } from "@/components/molecules/SearchForm";
import { UserAvatar } from "@/components/molecules/UserAvatar";

interface HeaderProps {
  currentUser: User;
  notificationsCount?: number;
  onSearch: (query: string) => void;
  onNotificationsPress: () => void;
  onProfilePress: () => void;
}

export function Header({
  currentUser,
  notificationsCount = 0,
  onSearch,
  onNotificationsPress,
  onProfilePress,
}: HeaderProps) {
  return (
    <SafeAreaView className="bg-white border-b border-gray-200">
      <View className="flex-row items-center justify-between px-4 h-14">
        <Logo size="sm" />

        <View className="flex-1 mx-4">
          <SearchForm placeholder="Search..." onSubmit={onSearch} />
        </View>

        <View className="flex-row items-center gap-3">
          <IconButton
            icon="bell"
            badgeCount={notificationsCount}
            onPress={onNotificationsPress}
            accessibilityLabel="Notifications"
          />
          <UserAvatar user={currentUser} onPress={onProfilePress} />
        </View>
      </View>
    </SafeAreaView>
  );
}
```

## Additional Context

**How to identify an organism boundary:**
- Can a user point to it on the screen and name it? ("the header", "the sidebar", "the product grid")
- Does it compose at least two molecules or a mix of molecules and atoms?
- Does it represent a distinct functional area with its own purpose?

**Common organisms and what they compose:**

| Organism | Composed Of | Purpose |
|----------|------------|---------|
| `Header` | Logo (atom) + NavLinks (molecule) + SearchForm (molecule) + UserMenu (molecule) | Site-wide navigation |
| `Sidebar` | NavLinks (molecule) + FilterGroups (molecule) | Secondary navigation or filtering |
| `ProductGrid` | Heading (atom) + SortSelector (molecule) + ProductCards (molecule) | Product listing section |
| `CommentThread` | UserAvatar (molecule) + CommentBody (molecule) + ReplyForm (molecule) | Discussion section |
| `Footer` | Logo (atom) + NavLinks (molecule) + SocialLinks (molecule) | Site footer |
| `HeroSection` | Heading (atom) + Text (atom) + Button (atom) + Image (atom) | Landing page hero |

**Organism vs. page:**
- An organism is a reusable section. A page is a unique composition of organisms.
- If the component fetches ALL the data for the entire view, it is a page, not an organism.
- Organisms can accept data via props or fetch data for their specific section.
