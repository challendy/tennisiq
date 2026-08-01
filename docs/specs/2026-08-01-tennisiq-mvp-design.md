# TennisIQ MVP Design (v0.1)

**Date:** 2026-08-01
**Source spec:** `docs/PRODUCT_REQUIREMENTS_v1.md`
**Status:** Approved for implementation

---

## 1. What this document decides

The product requirements specification describes a platform: ten MVP features, four
subscription tiers, coach mode, gamification, a Flutter app, a web app, and a six-model
computer-vision pipeline. That is a multi-year product, not an MVP.

This document narrows it to one **vertical slice that a real player can use end to end**,
names what is deliberately deferred, and fixes the architecture so the deferred work can
be added without rewrites. `docs/ROADMAP.md` sequences everything that is cut here.

---

## 2. The one loop the MVP must nail

```
Record → Upload → Analyze → Understand → Practice → Track
```

If a 3.5 player can film a forehand on a phone, get back a graded, phase-by-phase
explanation of *why* it looked like that, hear the single highest-impact correction,
practice against a generated session, and then see the score move two weeks later — the
product thesis is proven. Everything else is expansion.

### In scope (maps to the numbered MVP features in the source spec)

| # | Feature | MVP scope |
|---|---|---|
| 1 | AI Stroke Analysis | Serve, forehand, backhand, volley, overhead. Grade, confidence, strengths, weaknesses, single highest-priority fix. |
| 2 | Frame-by-frame breakdown | All 8 phases, each with score, coaching note, and comparison to an ideal range. |
| 3 | Visual overlay | Rendered MP4: skeleton, swing path trail, contact marker, shoulder/hip angles, hip–shoulder separation, centre of gravity, balance bar. |
| 4 | AI Voice Coach | Generated coaching script, spoken in-browser via the Web Speech API. No paid TTS vendor yet. |
| 5 | Shot comparison | Compare any two analyses of the same stroke; per-metric deltas with direction of travel. |
| 6 | Practice planner | Rules-based session generated from the player's live weaknesses, drawn from a seeded drill library. |
| 10 | Progress dashboard | Per-stroke score history, overall TennisIQ score, analysis volume. |

### Deferred, with the reason

| # | Feature | Why not now |
|---|---|---|
| 7 | Match Review | Needs ball tracking, court homography, and point/rally segmentation — an entire second CV subsystem with its own accuracy bar. Phase 2. |
| 8 | Ball machine integration | Already marked future in the source spec; depends on vendor APIs. |
| 9 | Equipment Advisor | Genuinely easy (rules over a racquet/string table) but it sits outside the core loop and would dilute the first release. Phase 3. |
| — | Gamification | Achievements are a retention lever, not a proof of value. Phase 3. |
| — | Coach / Club mode | Multi-tenant teams and athlete rosters change the authorization model. Phase 4, once single-player value is proven. |
| — | Billing | Quota **enforcement** ships now because it shapes the data model. Stripe/App Store payment does not. Phase 1. |

---

## 3. Deviations from the specified technology stack

Three deliberate departures. Each is a sequencing decision, not a rejection.

**Flutter → mobile-first web app first.** The source spec names Flutter for mobile. The MVP
ships a mobile-first, installable web app instead. During discovery, the UI will be rewritten
several times; paying that cost twice (native + web) before the analysis output is validated is
waste. The web client talks to the same public API a Flutter client will, so Phase 1 adds the
Flutter shell against a proven contract. Practically: video capture and playback work fine in a
mobile browser, and Flutter could not be exercised on this machine anyway.

**Redis → Postgres-backed job queue.** Redis buys distributed caching and a fast queue at
the cost of a second stateful dependency. At MVP volume, `SELECT ... FOR UPDATE SKIP LOCKED`
against Postgres is a correct, durable, observable queue in ~40 lines. `IAnalysisJobQueue`
is an interface, so Redis/Azure Service Bus is a swap, not a migration.

**Azure Blob Storage → `IVideoStorage` with a local adapter.** The MVP writes to disk. The
Azure adapter is a second implementation of the same two-method interface, added when we
deploy.

**Kept from the spec:** ASP.NET Core, PostgreSQL, Python inference service, OpenCV,
MediaPipe pose estimation, an LLM for coaching language.

---

## 4. Architecture

```
                 ┌─────────────────────────┐
   phone/laptop  │  web  (Next.js, TS)     │   mobile-first UI, records or picks a
   browser  ───► │  mobile-first PWA       │   video, polls the job, plays overlay
                 └───────────┬─────────────┘
                             │ REST + JWT
                 ┌───────────▼─────────────┐
                 │  api  (ASP.NET Core 10) │   system of record + orchestration
                 │                         │   auth, quota, jobs, persistence,
                 │  ┌───────────────────┐  │   coaching narration, planner
                 │  │ AnalysisWorker    │  │
                 │  │ (hosted service)  │  │
                 │  └─────────┬─────────┘  │
                 └──────┬─────┼────────────┘
              EF Core   │     │  HTTP (multipart)
                 ┌──────▼──┐  │   ┌──────────────────────────┐
                 │Postgres │  └──►│ analysis (Python 3.12)   │  the CV brain:
                 │ + jobs  │      │ FastAPI + MediaPipe      │  pose → kinematics →
                 └─────────┘      │ + OpenCV                 │  phases → scores →
                                  └──────────────────────────┘  overlay MP4
                 ┌─────────┐
                 │ storage │  IVideoStorage: local dir now, Azure Blob later
                 └─────────┘
```

Three processes, one `docker compose up`. The split is along the axis that actually
matters: **Python owns pixels and biomechanics, .NET owns the player's history and
money, the browser owns presentation.** Each can be replaced or scaled alone.

### 4.1 `services/analysis` — the CV brain

Stateless. Takes a video, returns judgement. Knows nothing about users, plans, or quotas,
which is what makes it independently testable.

`POST /analyze` (multipart: `video`, `stroke`, `handedness`, `view`) → `AnalysisResult`

Pipeline, one module per stage:

| Module | Responsibility |
|---|---|
| `pose/estimator.py` | `PoseEstimator` protocol → `list[FramePose]`. `MediaPipePoseEstimator` is the real one; `SyntheticPoseEstimator` generates deterministic strokes so every downstream stage is testable without a model or a video. |
| `kinematics/features.py` | Per-frame derived signals: joint angles, hip–shoulder separation, centre of gravity, balance, hand speed. Pure functions over landmarks. |
| `segmentation/phases.py` | Cuts the rally-free clip into the 8 named phases from the hand-speed and hand-position curves. |
| `scoring/rubric.py` | Declarative per-stroke ideal ranges → per-phase score + observations. Coaching knowledge lives in data, not code. |
| `grading.py` | Aggregates phases into overall grade, strengths, weaknesses, the single top fix, and a **confidence** score. |
| `overlay/render.py` | Draws the annotated MP4 with OpenCV. |

**Contact detection is an estimate, and the product says so.** With no ball tracking in
the MVP, contact is the peak-hand-speed frame within the acceleration window. This is
right for most clean strokes and wrong for mishits, so contact-dependent metrics carry
their own confidence and the UI labels them estimated. Ball tracking in Phase 2 replaces
the estimator behind the same interface.

**Confidence gating is a first-class output, not an afterthought.** Bad input is the
default failure mode of consumer video: filmed head-on, player half out of frame, 15 fps,
dusk. When landmark visibility, frame count, or phase separation fall below threshold, the
service returns `insufficient_quality` with specific, actionable filming guidance rather
than a confident, wrong grade. Fabricated precision is the fastest way to lose a coach's
trust.

### 4.2 `src/TennisIQ.Api` — system of record

- **Auth:** email + password, ASP.NET `PasswordHasher`, JWT bearer.
- **Persistence:** EF Core + Npgsql. Analysis results land in `jsonb`; the handful of
  metrics that drive trends are also projected into typed columns so dashboard queries
  stay indexable.
- **Jobs:** `analysis_jobs` table, `SKIP LOCKED` claim, `AnalysisWorker` hosted service
  calls the Python service and persists the result. Upload returns immediately; the client
  polls. Retries with attempt counting; terminal failures carry a user-facing reason.
- **Quota:** free = 3 analyses/month, premium = unlimited. Enforced at job creation,
  counted per calendar month.
- **Coaching language:** `ICoachNarrator` has two implementations —
  `LlmCoachNarrator` (OpenAI-compatible chat completions, model configurable) and
  `RuleBasedCoachNarrator` (templated from the rubric findings). **The rule-based one is
  the default when no API key is configured, so the whole product runs offline.** The LLM
  writes *prose*; it never invents *numbers*. Metrics come from the CV service, are passed
  in as facts, and the prompt forbids new measurements. This keeps hallucination out of
  the one place it would be most damaging.

### 4.3 `web` — mobile-first client

Next.js App Router, TypeScript, Tailwind. Screens: auth, capture/upload, analysis result
(overlay video with a scrubbable phase timeline, grade, strengths/weaknesses, top fix,
spoken coaching), history + progress dashboard, compare, practice plan.

---

## 5. Data model

```
users ─┬─ subscriptions (plan, current_period_start, analyses_used)
       ├─ videos (storage_key, duration, fps, resolution, stroke, handedness)
       ├─ analyses (video_id, stroke, overall_score, grade, confidence,
       │            result jsonb, overlay_key, created_at)
       │     └─ phase_scores (phase, score, feedback)   -- projected for trends
       ├─ analysis_jobs (video_id, status, attempts, error, claimed_at)
       └─ practice_plans (goal, generated_from_analysis_id, items jsonb)
drills (library, seeded: name, focus, stroke, equipment, reps, instructions)
```

`analyses.result` holds the full CV payload so the schema does not need to chase every
pipeline change; `overall_score`, `confidence`, and `phase_scores` are extracted because
the dashboard and comparison queries need them relationally.

---

## 6. Error handling

Failures are expected, not exceptional, so each one has a named user-visible outcome:

| Failure | Behaviour |
|---|---|
| Unsupported/corrupt video | Rejected at upload with format guidance. Never enqueued. |
| Pose quality too low | Job succeeds with `insufficient_quality`; UI shows filming tips. Not billed against quota. |
| Analysis service down / times out | Job retries with backoff, up to 3 attempts, then fails with a retry action. |
| LLM unavailable or no key | Silent fallback to `RuleBasedCoachNarrator`. Analysis still ships. |
| Quota exhausted | 402 with the current plan and reset date. |

---

## 7. Testing strategy

Test where the logic is, not uniformly.

- **Python (pytest)** — the real substance. Kinematics maths against hand-computed
  vectors; phase segmentation against synthetic stroke curves with known boundaries;
  rubric scoring at and outside ideal ranges; confidence gating on degraded input;
  overlay renders a playable file. `SyntheticPoseEstimator` makes all of this hermetic —
  no model download, no video fixtures, no flakiness.
- **.NET (xUnit)** — quota arithmetic across month boundaries, job lifecycle and retry,
  practice-plan generation from weaknesses, rule-based narration, comparison deltas.
- **Web (vitest)** — pure presentation logic only: chart shaping, phase-timeline maths,
  formatting.

The deliberate gap: no full browser E2E in the MVP. It is on the roadmap, and the API
contract tests plus Python integration tests cover the risk that matters more.

---

## 8. Definition of done for v0.1

1. `docker compose up` brings up Postgres, analysis, api, web.
2. A new user signs up, uploads a forehand clip, and receives a graded analysis with an
   overlay video, 8 phase scores, and a spoken top-priority correction.
3. A second upload of the same stroke produces a comparison with per-metric deltas.
4. The dashboard shows score history; the planner produces a session targeting the
   weakest phase.
5. A free user is blocked on the 4th analysis of the month.
6. Test suites pass for Python and .NET.
7. Everything runs with **no third-party API key configured**.
