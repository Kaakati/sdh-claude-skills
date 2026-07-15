# Real-time (Centrifugo) — one socket, one cache, no second source of truth

Load-bearing rules restated (hold even if you read nothing else):

1. **One `Centrifuge` client for the app, created once.** Not per screen, not per hook.
2. **`newSubscription()` throws if the channel already has a subscription** — and a remounting
   screen calls it twice. Use `getSubscription() ?? newSubscription()`.
3. **A real-time event updates the Query cache. It never becomes a second copy of the data.**
4. **The connection token comes from your backend and expires** — wire `getToken` or the socket
   dies silently after an hour.

---

## Why real-time breaks the state model

Every other data path in this stack has one owner: TanStack Query owns server state, Zustand
owns client state. A socket quietly offers a third — *events arriving with data in them* — and
the tempting move is to drop them into a `useState` or a store. Now the same order exists in two
places with different values, and which one the user sees depends on which screen they opened
first. Nothing crashes. The app is just wrong sometimes.

**The event is a cache update, not a data source.** That single rule keeps the model intact.

## Decision: what do I do with an incoming event?

| The event… | Do | Why |
|---|---|---|
| Carries the full updated entity | `setQueryData(key, entity)` | Free update, no refetch |
| Carries only an id / "something changed" | `invalidateQueries({ queryKey })` | Let Query refetch the truth |
| Is high-frequency (typing, cursors, presence) | Zustand or local state | Ephemeral; never server state |
| Might be out of order or partial | `invalidateQueries` | Refetch beats reconstructing |

**When in doubt, invalidate.** `setQueryData` with a partial payload is how caches drift: you
merge a field, miss another, and the screen shows a half-updated record that no refetch ever
corrects because Query thinks it is fresh.

## The client — created once, at module scope

```ts
// src/lib/centrifugo.ts  ✅
import { Centrifuge } from 'centrifuge';
import { api } from '@/api/client';

export const centrifuge = new Centrifuge(process.env.EXPO_PUBLIC_CENTRIFUGO_URL!, {
  // getToken is called on connect AND whenever the token expires. Passing a static `token`
  // instead works until it expires, then the socket disconnects and never comes back — the
  // classic "real-time stopped working after an hour and nobody noticed" bug.
  getToken: async () => {
    const { data } = await api.post('/centrifugo/token');
    return data.token;   // minted by Rails; never build a Centrifugo token on the client
  },
});

centrifuge.connect();
```

The token is generated **by the backend**. A client that can mint its own connection token can
subscribe to any channel it likes.

## Bad — a subscription per mount, and a second copy of the data

```tsx
// src/screens/ChatRoom.tsx  ❌
export function ChatRoom({ roomId }: { roomId: string }) {
  const [messages, setMessages] = useState<Message[]>([]);   // ❌ second source of truth
  const { data } = useQuery({ queryKey: ['messages', roomId], queryFn: () => api.getMessages(roomId) });

  useEffect(() => {
    // ❌ throws "Subscription to a channel already exists" the second time this screen
    // mounts — navigate away and back, and the screen crashes.
    const sub = centrifuge.newSubscription(`chat:${roomId}`);
    sub.on('publication', (ctx) => setMessages((m) => [...m, ctx.data]));
    sub.subscribe();
    // ❌ unsubscribe does NOT remove the subscription from the client registry, so the
    // next newSubscription() for this channel still throws.
    return () => sub.unsubscribe();
  }, [roomId]);

  // ❌ which list is real? `data` from the server, or `messages` from the socket?
  return <FlatList data={messages} renderItem={renderMessage} />;
}
```

Three bugs, and the first one is the only one that announces itself. The `useState` copy loses
every message that arrived before this screen mounted, and `data` is never updated by the socket
at all.

## Good — one subscription per channel, cache is the only truth

```ts
// src/hooks/useChannel.ts  ✅
import { useEffect } from 'react';
import { centrifuge } from '@/lib/centrifugo';

type Handler = (data: unknown) => void;

export function useChannel(channel: string | null, onPublication: Handler) {
  useEffect(() => {
    if (!channel) return;

    // getSubscription first: newSubscription THROWS if one already exists in the client's
    // internal registry, and a remount or a second screen on the same channel does exactly
    // that. This one line is the difference between working and crashing on navigation.
    const sub = centrifuge.getSubscription(channel) ?? centrifuge.newSubscription(channel);

    const handler = (ctx: { data: unknown }) => onPublication(ctx.data);
    sub.on('publication', handler);
    if (sub.state !== 'subscribed') sub.subscribe();

    return () => {
      // "Unsubscribing from subscription does not remove event handlers you already set" —
      // remove OUR handler, or every remount stacks another one and the cache update runs
      // N times per message.
      sub.removeListener('publication', handler);
      // Leave the subscription itself alive: another screen may share this channel. Reap it
      // only when nothing is listening.
      if (sub.listeners('publication').length === 0) {
        sub.unsubscribe();
        centrifuge.removeSubscription(sub);   // frees the channel in the registry
      }
    };
  }, [channel, onPublication]);
}
```

```tsx
// src/screens/ChatRoom.tsx  ✅ the cache is the only list
import { useCallback } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useChannel } from '@/hooks/useChannel';

export function ChatRoom({ roomId }: { roomId: string }) {
  const queryClient = useQueryClient();
  const key = ['messages', roomId];
  const { data: messages = [] } = useQuery({ queryKey: key, queryFn: () => api.getMessages(roomId) });

  // useCallback: an unstable handler re-runs the effect on every render, which
  // re-subscribes on every render.
  const onMessage = useCallback(
    (data: unknown) => {
      const message = data as Message;
      // Full entity on the wire -> write it straight into the cache. One list, one owner.
      queryClient.setQueryData<Message[]>(key, (old = []) =>
        old.some((m) => m.id === message.id) ? old : [...old, message],
      );
    },
    [queryClient, roomId],
  );

  useChannel(`chat:${roomId}`, onMessage);

  return <FlatList data={messages} renderItem={renderMessage} keyExtractor={(m) => m.id} />;
}
```

The dedupe by `id` is not defensive padding: Centrifugo delivers at-least-once, and a
reconnect can replay recent publications.

## Reconnection is a cache problem, not just a banner

While the socket was down, events were missed. The socket coming back does **not** backfill
them — so a screen that only listens is now quietly stale.

```ts
// src/lib/centrifugo.ts  ✅
import { queryClient } from './query-client';

centrifuge.on('connected', () => {
  // Refetch what the socket could not tell us about while it was down. Without this, a
  // subway ride ends with a chat that looks fine and is missing ten messages.
  queryClient.invalidateQueries({ queryKey: ['messages'] });
});
```

Surface the state — a real-time UI that is silently disconnected is worse than one that admits
it:

```tsx
const [connected, setConnected] = useState(false);
useEffect(() => {
  const on = () => setConnected(true);
  const off = () => setConnected(false);
  centrifuge.on('connected', on);
  centrifuge.on('disconnected', off);
  return () => { centrifuge.removeListener('connected', on); centrifuge.removeListener('disconnected', off); };
}, []);
```

## Presence — ephemeral, so it does not belong in Query

Presence changes many times a second and has no server-of-record worth caching. It is client
state: keep it in Zustand or local state, and let it die with the screen.

```ts
const sub = centrifuge.getSubscription(channel) ?? centrifuge.newSubscription(channel);
sub.on('join', (ctx) => usePresenceStore.getState().add(ctx.info.user));
sub.on('leave', (ctx) => usePresenceStore.getState().remove(ctx.info.user));
```

This is the one case where the socket legitimately owns the data — because nothing else does.
