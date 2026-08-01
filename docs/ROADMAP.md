# TennisIQ Long-Term Roadmap

**North star:** hours of meaningful practice improved by AI guidance per player each month.

The durable advantage is the **Player Knowledge Graph** — a continuously updated model of
each player built from videos, matches, practice, equipment, and (eventually) fitness and
recovery. Every phase below either feeds that graph or monetises what it already knows.

---

## Phase 0 — Foundation (this MVP)

**Ship:** the Record → Analyze → Understand → Practice → Track loop for individual
strokes. See `docs/specs/2026-08-01-tennisiq-mvp-design.md`.

**Exit criteria:**
- A 3.5 player can upload a forehand, get a graded analysis with overlay, hear the
  top fix, practice against a generated session, and see the score move on a second upload.
- Confidence gating rejects bad video with filming tips rather than fabricating grades.
- Free-tier quota is enforced.
- Product runs end-to-end with no third-party API key.

**Feeds the graph:** stroke analyses, phase scores, weaknesses, practice plans.

---

## Phase 1 — Productisation

Make it something people will pay for and use every week.

| Workstream | Deliverable |
|---|---|
| Billing | Stripe Checkout + Customer Portal for Premium. Soft-gate Free at 3/month. |
| Mobile | Flutter client against the same public API. Camera capture with on-court filming tips. Offline upload queue. |
| Auth | Magic-link / Google / Apple Sign-In. Password reset. |
| Reliability | Azure Blob storage adapter. Managed Postgres. Redis or Azure Service Bus for the job queue. CDN for overlays. |
| Observability | Structured logging, request tracing, analysis latency/success dashboards, Sentry. |
| Content | Expand the drill library; coach-authored drills tagged by weakness. |
| Quality | Browser E2E (Playwright). Golden-video regression suite for the CV pipeline. |

**Exit criteria:** paid conversions from free users; mobile retention above a baseline we
set after two weeks of analytics; p95 analysis latency under 90s for a 15s 1080p clip.

---

## Phase 2 — Match Intelligence

The second half of "why" — tactics, not just technique.

| Workstream | Deliverable |
|---|---|
| Ball tracking | TrackNet-class model; contact becomes measured, not estimated. |
| Court detection | Homography; every landing maps to court coordinates. |
| Point segmentation | Auto-cut a match video into points and rallies. |
| Match Review | Winners / forced / unforced, double faults, 1st-serve %, return %, rally length, shot selection, court positioning. |
| Shot recognition | Classify strokes *inside* a match, not just from a dedicated clip. |
| Tactical IQ | Score and trend on the dashboard. |

**Exit criteria:** a full set match produces a review a league player would actually act on
(e.g. "you lose 70% of points that last 7+ shots from the backhand corner").

**Feeds the graph:** match outcomes, shot selection patterns, court-position habits,
fatigue-correlated technique drop-off across long matches.

---

## Phase 3 — Retention & Depth

Keep players coming back and deepen the personalisation surface.

| Workstream | Deliverable |
|---|---|
| Equipment Advisor | Racquet / string / tension / grip recommendations from style, injuries, level, age. String-change schedules. |
| Gamification | Achievements, consistency streaks, milestone badges. |
| Professional comparison | Overlay measurable movement data against ATP/WTA reference models (not aesthetic side-by-sides). |
| Player Knowledge Graph v1 | Explicit graph store: player → sessions → strokes → phases → weaknesses → drills → outcomes. First "insights" queries ("your contact consistency improved 12% after the hybrid string change"). |
| AI conversation | Chat with the coach over the player's own history. Same rule: LLM never invents numbers. |

**Exit criteria:** at least one insight per active Premium user per week that they
couldn't have gotten by rewatching their own video.

---

## Phase 4 — Multiplayer of Coaching

Expand the customer from "a player" to "a coach and their roster".

| Workstream | Deliverable |
|---|---|
| Coach Mode | Teams, athlete invites, AI pre-analysis inbox, coach annotations on top of AI. |
| Club / Academy | Org accounts, role hierarchy, shared drill libraries, reporting. |
| Coach plan billing | Per-seat pricing. |
| White-label options | Academy branding on the athlete-facing views. |

**Exit criteria:** a teaching pro runs their week inside TennisIQ instead of in a
spreadsheet + iMessage.

---

## Phase 5 — Live & Ambient

Move from "review after" to "coach during".

| Workstream | Deliverable |
|---|---|
| Live audio coaching | Real-time cues through earbuds during a practice session (latency budget < 400ms for the cue path). |
| Wearables | Apple Watch / Garmin: heart rate, load, recovery. Correlate with technique breakdown. |
| Smart court | Position, speed, distance when the venue supports it. |
| AI Opponent Scout | Upload an opponent's match; get a scouting report and a game plan. |
| Ball machine integration | Lobster / Slinger / Hydrogen workout generation from the planner. |

**Exit criteria:** a player can take a lesson-quality practice session with no human
coach present and attribute measurable improvement to it.

---

## Platform principles that survive every phase

1. **Pixels and biomechanics in Python. History and money in .NET. Presentation in the
   client.** Cross that boundary only with typed contracts.
2. **The LLM writes prose; it never invents numbers.** Metrics come from sensors and
   models. The narrator is a guest in the room, not the referee.
3. **Confidence before confidence theatre.** Prefer an honest "we couldn't see that" to
   a precise-looking lie.
4. **Every new signal feeds the Player Knowledge Graph.** If a feature doesn't write to
   it or read from it, ask why it exists.
5. **Interfaces over infrastructure.** Storage, queue, narrator, pose estimator — all
   behind ports so Azure, Redis, a better pose model, or a different LLM are swaps.

---

## Suggested sequencing heuristic

When choosing what to build next, prefer the item that most improves the north-star
metric *and* writes a new edge into the Player Knowledge Graph. Features that only
decorate the UI without feeding the graph are usually Phase-later than they feel.
