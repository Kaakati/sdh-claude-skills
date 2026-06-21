# Storytelling UI Framework

Structure an interface so the user moves through it like a narrative — a beginning,
middle, and end, with progression and emotional beats — instead of a flat collection of
screens and controls. Humans engage with and retain narrative far better than raw feature
lists, so the interface should guide the user along a deliberate arc.

> **Restraint first.** Storytelling serves the user's goal; it never overrides clarity,
> speed, or accessibility. Always keep skip paths, never withhold critical information for
> "drama," and honor `prefers-reduced-motion`. A story that slows the hero down is a bad story.

## The five dimensions

| Dimension | What it means | UI tools |
|-----------|---------------|----------|
| **1. Narrative arc** | A clear entry (hook/setup), a middle (core work / value), a resolution (payoff, success, CTA) | Onboarding flows, landing pages, feature tours, checkout |
| **2. Sequence & pacing** | Control the order and speed information is revealed — withhold and release to build understanding | Progressive disclosure, step flows, scroll-driven reveals, skeletons |
| **3. Protagonist** | The user is the hero; the product is the guide/mentor ("you're Luke, we're Yoda"). Copy is about the user's goal and obstacle, not the feature set | Microcopy, headlines, CTAs, onboarding voice |
| **4. Emotional beats** | Empty states, loading, errors, success, milestones carry tone and feeling, not just function | Microcopy, illustrations, transitions, success animations |
| **5. Continuity & motion** | Transitions keep a thread between states so it feels like one journey, not disconnected jumps | Shared-element transitions, scroll-linked animation, scrollytelling |

## StoryBrand (SB7) mapped to the interface

Donald Miller's framework: position the **user as hero, product as guide**. Map each beat to UI:

| SB7 beat | In the UI |
|----------|-----------|
| 1. A **Character** with a want | Hero section / onboarding speaks to the user's goal ("Ship faster", not "Our platform has…") |
| 2. Has a **Problem** (external, internal, philosophical) | Name the pain the user feels, not just the technical gap |
| 3. Meets a **Guide** (empathy + authority) | Product shows it understands ("We've been there") and is competent (proof, logos, results) |
| 4. Who gives a **Plan** | 3-step "how it works"; clear path; reduce perceived effort |
| 5. Calls to **Action** | One **direct** CTA (Start, Buy) + a **transitional** CTA (See how it works, Read the guide) |
| 6. Helps avoid **Failure** | Make stakes tangible (what they lose by not acting) — used sparingly |
| 7. Ends in **Success** | Show the transformed state — the after, the win, the success screen |

## Narrative arc mapped to common flows

- **Onboarding** — *Hook* (value prop, the promise) → *Rising action* (setup steps with visible progress) → *Climax* (the first "aha" / first real success) → *Resolution* ("You're ready" + next CTA). Drive to the aha moment fast; defer optional config.
- **Landing page** — *Hook* (headline names the want + problem) → *Guide* (product as solution, empathy + authority) → *Plan* (how it works) → *Proof* (testimonials, metrics) → *CTA* → *Success vision* (life after).
- **Empty state** — *Setup* (what this space is for) → *Invitation* (the hero's first concrete action) — never a dead end.
- **Checkout / multi-step** — steady **pacing** with a visible step indicator; each step a small win; the resolution is a celebratory, reassuring confirmation.
- **Search → results → detail** — query is the quest; results are the journey; the detail/decision is the payoff; the empty result is a redirect, not a failure.

## Storytelling per screen pattern

Extends the 8 core screen patterns with their narrative role:

| Pattern | Narrative role | Storytelling moves |
|---------|----------------|--------------------|
| Onboarding | Act I — the call to adventure | Promise the payoff up front; show progress; reach first value before asking for setup |
| Dashboard | Returning hero's "home base" | Lead with "where am I / what changed since last time"; surface the next best action, not every metric |
| List / Detail | The journey and the destination | List builds anticipation; detail delivers the payoff; preserve context on the trip back |
| Forms | The hero's effort/ordeal | Pace with sections + progressive disclosure; each section a beat; inline validation = a guide that catches you |
| Search | The quest | Empty/zero-results is a fork in the road with a suggested path, not a wall |
| Settings | Quiet interlude | Calm, low-drama, reversible; confirmation = reassurance |
| Profile | The hero's identity | Celebrate progress/achievements (streaks, milestones) as story so far |
| Empty states | The blank page / invitation | Setup + first action; tone carries the most emotional weight per pixel here |

## Emotional beats catalogue

Treat these as scripted moments with intended tone, not afterthoughts:

| Moment | Intended feeling | Technique |
|--------|------------------|-----------|
| First empty state | Invitation, possibility | Friendly illustration + one clear first action ("Create your first project") |
| First load / setup | Anticipation, momentum | Skeletons that hint at structure; progress with a sense of "almost there" |
| First success ("aha") | Pride, validation | Micro-celebration (subtle confetti/checkmark), name what they achieved |
| Milestone / streak | Recognition, belonging | Acknowledge progress ("3 days in a row") |
| Error | Calm, supported (never blamed) | Plain-language cause + the fix; "Let's try that again", not "Invalid input" |
| Loading a slow action | Trust, transparency | Tell the story of what's happening ("Crunching 4,200 rows…") |
| Completion / success state | Closure, reward | Clear resolution + the obvious next chapter (CTA) |
| Re-engagement (return) | Welcome back | "Here's what changed since you left" |

## Pacing & progressive-disclosure techniques

- **Progressive disclosure** — reveal complexity only when needed (accordions, "Advanced" sections, just-in-time fields).
- **Step flows** — chunk long tasks; a step indicator turns effort into measurable progress.
- **Scroll-driven reveals / scrollytelling** — content unfolds as the user scrolls; the most literal narrative pacing (data stories, product walkthroughs). Pair with `IntersectionObserver`.
- **Anticipation** — skeletons and optimistic UI hold tension during waits instead of dead spinners.
- **Withhold & release** — don't dump everything at once; release information as the user earns context.

## Continuity & motion

- **Shared-element / matched transitions** keep a spatial thread (list item → detail expands from its card), so states feel connected, not teleported.
- **Motion conveys causality** — direction and origin tell the user where they came from and where they're going.
- **Scroll-linked animation** ties progress to the user's own pace.
- Stack tools: **Framer Motion** (web — `layoutId`, `AnimatePresence`, `whileInView`), **Reanimated + Gesture Handler** (React Native), Tailwind transitions + View Transitions API where available.
- **Always** gate non-essential motion behind `prefers-reduced-motion` and keep durations short (150–300ms for UI, longer only for deliberate scrollytelling).

## Microcopy as narrative voice

Write around the user's **goal and obstacle**, in second person ("you"), with the product as guide.

| Flat / feature-led ❌ | Story-driven (user as hero) ✅ |
|----------------------|-------------------------------|
| "Our platform supports multi-region deployments." | "Ship to your users anywhere — we handle the regions." |
| "No items found." | "Nothing here yet — create your first invoice to get started." |
| "Error 422: validation failed." | "That email's already in use. Try signing in instead?" |
| "Upload complete." | "Done — your report's ready to share." |

## Storytelling review checklist (score each 0–2: 0 absent, 1 partial, 2 strong)

1. **Arc** — Is there a clear beginning (hook), middle (value), and end (payoff/CTA)? No dead ends.
2. **Hero framing** — Does copy center the user's goal/obstacle, with the product as guide?
3. **Pacing** — Is information released deliberately (progressive disclosure / steps), not dumped?
4. **First value** — Does the flow reach the "aha"/first success quickly?
5. **Emotional beats** — Do empty/loading/error/success states carry intentional tone?
6. **Continuity** — Do transitions maintain a thread between states?
7. **Resolution** — Is there a satisfying success state with an obvious next step?
8. **Restraint** — Does the narrative never block clarity, speed, accessibility, or skip paths?

Aggregate: **/16. ≥13 strong narrative; 8–12 functional but flat; <8 a disconnected collection of screens.**

## Anti-patterns

- **Feature dumping** — listing capabilities instead of the user's transformation.
- **No arc** — screens that start and stop with no setup or payoff.
- **Dead ends** — empty/error/success states with no next action.
- **Tone-deaf beats** — blaming error messages, celebration where reassurance was needed.
- **Hero confusion** — making the *product* the hero instead of the user.
- **Motion without meaning** — animation that decorates instead of conveying causality or continuity.
- **Drama over clarity** — withholding critical info, removing skip options, or ignoring reduced-motion for the sake of "story."
