---
title: "Organism Data Awareness Boundary"
id: organism-data-awareness
impact: MEDIUM
tags: [atomic-design, organisms, data-fetching]
platforms: [phlex, reactjs, nextjs, react-native]
---

# Organism Data Awareness Boundary

Organisms are the LOWEST level in the atomic hierarchy that can be data-aware. They may accept domain-specific data via props, use data-fetching hooks (TanStack Query), or subscribe to real-time channels. Atoms and molecules must remain purely presentational -- they accept display-ready props and know nothing about API endpoints, query keys, or data shapes.

## Incorrect

An atom or molecule using data-fetching hooks or accepting domain-specific objects.

```tsx
// web/src/components/atoms/UserBadge/UserBadge.tsx
// WRONG: Atom fetching its own data
import { useQuery } from "@tanstack/react-query";
import { fetchUser } from "@/api/users";

export function UserBadge({ userId }: { userId: string }) {
  const { data: user } = useQuery({
    queryKey: ["user", userId],
    queryFn: () => fetchUser(userId),
  });

  return <span className="badge">{user?.name}</span>;
}
```

```tsx
// web/src/components/molecules/ProductCard/ProductCard.tsx
// WRONG: Molecule with data-fetching logic
import { useQuery } from "@tanstack/react-query";
import { fetchProductReviews } from "@/api/products";

interface ProductCardProps {
  productId: string;
}

export function ProductCard({ productId }: ProductCardProps) {
  const { data: reviews } = useQuery({
    queryKey: ["reviews", productId],
    queryFn: () => fetchProductReviews(productId),
  });

  return (
    <div>
      <Heading>Product</Heading>
      <Text>{reviews?.length} reviews</Text>
    </div>
  );
}
```

```ruby
# backend/app/components/molecules/user_card.rb
# WRONG: Molecule querying the database
class Components::Molecules::UserCard < Components::Base
  def initialize(user_id:)
    @user = User.find(user_id)  # Database query in a molecule
  end

  def view_template
    div(class: "flex items-center gap-3") do
      render Components::Atoms::Avatar.new(src: @user.avatar_url, alt: @user.name)
      render Components::Atoms::Text.new(content: @user.name)
    end
  end
end
```

## Correct

Atoms and molecules accept display-ready props. Organisms handle data awareness.

### Phlex (Rails)

```ruby
# backend/app/components/atoms/avatar.rb
# CORRECT: Atom accepts display-ready props only
class Components::Atoms::Avatar < Components::Base
  def initialize(src:, alt:, size: :md)
    @src = src
    @alt = alt
    @size = size
  end

  def view_template
    img(src: @src, alt: @alt, class: avatar_classes)
  end

  private

  def avatar_classes
    base = "rounded-full object-cover"
    size = case @size
           when :sm then "h-8 w-8"
           when :md then "h-10 w-10"
           when :lg then "h-12 w-12"
           end
    "#{base} #{size}"
  end
end

# backend/app/components/molecules/user_card.rb
# CORRECT: Molecule accepts pre-fetched display props
class Components::Molecules::UserCard < Components::Base
  def initialize(name:, avatar_url:, role:)
    @name = name
    @avatar_url = avatar_url
    @role = role
  end

  def view_template
    div(class: "flex items-center gap-3") do
      render Components::Atoms::Avatar.new(src: @avatar_url, alt: @name)
      div do
        render Components::Atoms::Text.new(content: @name, weight: :semibold)
        render Components::Atoms::Text.new(content: @role, size: :sm, color: :muted)
      end
    end
  end
end

# backend/app/components/organisms/team_roster.rb
# CORRECT: Organism receives data and distributes to molecules
class Components::Organisms::TeamRoster < Components::Base
  def initialize(team_members:)
    @team_members = team_members
  end

  def view_template
    section(class: "py-6", aria_label: "Team members") do
      render Components::Atoms::Heading.new(text: "Team", level: 2)
      div(class: "mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3") do
        @team_members.each do |member|
          render Components::Molecules::UserCard.new(
            name: member.name,
            avatar_url: member.avatar_url,
            role: member.role,
          )
        end
      end
    end
  end
end
```

### ReactJS (Vite SPA)

```tsx
// web/src/components/atoms/Avatar/Avatar.tsx
// CORRECT: Purely presentational atom
interface AvatarProps {
  src: string;
  alt: string;
  size?: "sm" | "md" | "lg";
}

export function Avatar({ src, alt, size = "md" }: AvatarProps) {
  const sizeClasses = { sm: "h-8 w-8", md: "h-10 w-10", lg: "h-12 w-12" };

  return (
    <img
      src={src}
      alt={alt}
      className={`rounded-full object-cover ${sizeClasses[size]}`}
    />
  );
}

// web/src/components/molecules/UserCard/UserCard.tsx
// CORRECT: Molecule with display-ready props
import { Avatar } from "@/components/atoms/Avatar";
import { Text } from "@/components/atoms/Text";

interface UserCardProps {
  name: string;
  avatarUrl: string;
  role: string;
}

export function UserCard({ name, avatarUrl, role }: UserCardProps) {
  return (
    <div className="flex items-center gap-3">
      <Avatar src={avatarUrl} alt={name} />
      <div>
        <Text weight="semibold">{name}</Text>
        <Text size="sm" color="muted">{role}</Text>
      </div>
    </div>
  );
}

// web/src/components/organisms/TeamRoster/TeamRoster.tsx
// CORRECT: Organism with data-fetching
import { useQuery } from "@tanstack/react-query";
import { Heading } from "@/components/atoms/Heading";
import { Spinner } from "@/components/atoms/Spinner";
import { UserCard } from "@/components/molecules/UserCard";
import { fetchTeamMembers } from "@/api/teams";

interface TeamRosterProps {
  teamId: string;
}

export function TeamRoster({ teamId }: TeamRosterProps) {
  const { data: members, isLoading, error } = useQuery({
    queryKey: ["team-members", teamId],
    queryFn: () => fetchTeamMembers(teamId),
  });

  if (isLoading) return <Spinner />;
  if (error) return <Text color="error">Failed to load team members</Text>;

  return (
    <section className="py-6" aria-label="Team members">
      <Heading level={2}>Team</Heading>
      <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {members?.map((member) => (
          <UserCard
            key={member.id}
            name={member.name}
            avatarUrl={member.avatarUrl}
            role={member.role}
          />
        ))}
      </div>
    </section>
  );
}
```

### Next.js (App Router)

```tsx
// next/src/components/organisms/TeamRoster/TeamRoster.tsx
// CORRECT: Server Component organism with data fetching
import { Heading } from "@/components/atoms/Heading";
import { UserCard } from "@/components/molecules/UserCard";
import { getTeamMembers } from "@/lib/api/teams";

interface TeamRosterProps {
  teamId: string;
}

export async function TeamRoster({ teamId }: TeamRosterProps) {
  const members = await getTeamMembers(teamId);

  return (
    <section className="py-6" aria-label="Team members">
      <Heading level={2}>Team</Heading>
      <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {members.map((member) => (
          <UserCard
            key={member.id}
            name={member.name}
            avatarUrl={member.avatarUrl}
            role={member.role}
          />
        ))}
      </div>
    </section>
  );
}
```

### React Native

```tsx
// mobile/src/components/organisms/TeamRoster/TeamRoster.tsx
// CORRECT: Organism with TanStack Query
import { View, FlatList } from "react-native";
import { useQuery } from "@tanstack/react-query";
import { Heading } from "@/components/atoms/Heading";
import { Spinner } from "@/components/atoms/Spinner";
import { Text } from "@/components/atoms/Text";
import { UserCard } from "@/components/molecules/UserCard";
import { fetchTeamMembers } from "@/api/teams";

interface TeamRosterProps {
  teamId: string;
}

export function TeamRoster({ teamId }: TeamRosterProps) {
  const { data: members, isLoading, error } = useQuery({
    queryKey: ["team-members", teamId],
    queryFn: () => fetchTeamMembers(teamId),
  });

  if (isLoading) return <Spinner />;
  if (error) return <Text color="error">Failed to load team members</Text>;

  return (
    <View className="py-6">
      <Heading level={2}>Team</Heading>
      <FlatList
        data={members}
        keyExtractor={(item) => item.id}
        numColumns={2}
        contentContainerStyle={{ gap: 16, marginTop: 16 }}
        columnWrapperStyle={{ gap: 16 }}
        renderItem={({ item }) => (
          <UserCard
            name={item.name}
            avatarUrl={item.avatarUrl}
            role={item.role}
          />
        )}
      />
    </View>
  );
}
```

## Additional Context

**Data awareness boundary summary:**

| Level | Data Fetching | Global State | Domain Objects | Event Handlers |
|-------|--------------|-------------|----------------|---------------|
| Atoms | Never | Never | Never | DOM events only (onClick, onFocus) |
| Molecules | Never | Never | Never | Form events (onSubmit, onChange) |
| Organisms | Allowed | Allowed | Allowed | Business events (onAddToCart) |
| Templates | Never (layout only) | Never | Never | Never |
| Pages | Required | Allowed | Required | Routing events |

**What "data-aware" means:**
- Using `useQuery`, `useMutation`, or `useSuspenseQuery` from TanStack Query
- Using Zustand stores for client-side state
- Subscribing to Centrifugo real-time channels
- Accepting domain-specific typed objects (e.g., `User`, `Product`, `Order`)
- Making API calls or database queries (in server components)

**What atoms and molecules CAN accept:**
- Primitive values: `string`, `number`, `boolean`
- Display-ready props: `label`, `placeholder`, `src`, `alt`, `variant`, `size`
- Callback props: `onClick`, `onSubmit`, `onChange` (without business logic)
- Children for composition

**Alternative pattern -- prop-drilling data through organisms:**
An organism can also accept data via props instead of fetching it. This is useful when the parent page has already fetched the data. The key rule is that atoms and molecules must never be the ones fetching data.
