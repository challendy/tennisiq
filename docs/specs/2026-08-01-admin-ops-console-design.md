# Admin Ops Console Design

**Date:** 2026-08-01  
**Status:** Draft — awaiting review  
**Parent:** `docs/specs/2026-08-01-tennisiq-mvp-design.md`  
**Decisions locked with Chris:** local/ops console (not full product admin); `User.IsAdmin` gate; v1 = users (plan + reset quota) + jobs (list, retry, cancel).

---

## 1. Problem

Quota and plan live only on `Subscriptions`. There is no UI to grant Premium, reset
`AnalysesUsed`, or unstick a failed analysis job. Today that means raw SQL. An ops
console removes that friction for local development and early support without waiting
for Stripe (Phase 1 roadmap).

---

## 2. Non-goals

- Stripe / Customer Portal / paid upgrades.
- Drills CRUD, analyses browser, impersonation, health dashboards.
- Admins promoting other users to admin in the UI (SQL / bootstrap only).
- Delete user / delete video / purge storage.
- Separate admin deployable or second auth system.
- Full audit log table in v1 (called out as follow-up).

---

## 3. Product behaviour

### Access

1. `User.IsAdmin` (bool, default `false`).
2. Bootstrap: if config `Admin:BootstrapEmail` (or env `TENNISIQ_BOOTSTRAP_ADMIN_EMAIL`)
   matches an existing user’s email at API startup (and on register if the new email
   matches), set `IsAdmin = true`. Idempotent.
3. JWT includes claim `is_admin` = `"true"` | `"false"`.
4. Web: `/admin/*` only for users whose token/me payload says admin; others redirect home.
5. API: all `/api/admin/*` require auth + `AdminOnly` policy → 403 otherwise.
6. Player chrome never shows an Admin link unless `isAdmin` is true.

### Users page (`/admin/users`)

- Search by email substring (`?q=`).
- Table columns: email, display name, plan, analyses used, limit (null → ∞ for Premium),
  period start, isAdmin (badge only).
- Actions per row:
  - **Set Free** / **Set Premium** — updates `Subscription.Plan`.
  - **Reset quota** — sets `AnalysesUsed = 0` (does not change `PeriodStart`).

### Jobs page (`/admin/jobs`)

- Filter by status (All / Pending / Running / Succeeded / Failed); default recent 50.
- Columns: job id (short), status, attempts, error (truncated), stroke, user email,
  video id, created/claimed timestamps.
- Actions:
  - **Retry** — only if `Failed`; set `Status = Pending`, clear `Error`, clear
    `ClaimedAt`, leave `Attempts` as-is (worker already increments on claim). If the
    queue requires `Attempts < max` for claim, admin retry also sets `Attempts = 0`
    so a permanently failed job can run again — **prefer reset Attempts to 0 on retry**
    so ops always works.
  - **Cancel** — if `Pending` or `Failed`: set `Status = Failed`,
    `Error = "Cancelled by admin"`, clear `ClaimedAt`, set `CompletedAt = utcNow`.
    If `Running`: same update (best-effort). **Race:** an in-flight worker may still
    finish and mark the job Succeeded afterward; v1 accepts that and does not add
    distributed cancellation. Succeeded jobs → 400.

---

## 4. Architecture

Admin lives in the **existing Next.js app** under an `(admin)` route group with its own
layout (no player marketing chrome). Backend is **ASP.NET** `/api/admin/*` using the
same JWT.

```
Browser /admin
   → JWT (is_admin=true)
      → GET/POST /api/admin/users|jobs
         → EF Core Users / Subscriptions / AnalysisJobs
```

Approach rejected: separate Blazor/Razor admin (second UI stack).  
Approach rejected: shared admin key only (worse UX once you’re already logged in).

---

## 5. Data model changes

```csharp
// User
public bool IsAdmin { get; set; } = false;
```

EF: project currently uses runtime schema ensure — add `IsAdmin` with default `false`
compatible with that path (and a note in README for existing DBs: `ALTER TABLE "Users"
ADD COLUMN IF NOT EXISTS "IsAdmin" boolean NOT NULL DEFAULT false;`). No new tables in v1.

Config:

```json
"Admin": {
  "BootstrapEmail": "chris@tennisiq.local"
}
```

---

## 6. API contract

All routes: `[Authorize(Policy = "AdminOnly")]`, prefix `/api/admin`.

| Method | Path | Body / query | Result |
|---|---|---|---|
| GET | `/users?q=&take=50` | optional email contains | `{ users: [{ id, email, displayName, plan, analysesUsed, analysesLimit, periodStart, isAdmin, createdAt }] }` |
| POST | `/users/{id}/plan` | `{ "plan": "Free" \| "Premium" }` | updated user summary |
| POST | `/users/{id}/reset-quota` | empty | updated user summary |
| GET | `/jobs?status=&take=50` | status optional | `{ jobs: [{ id, videoId, userId, userEmail, stroke, status, attempts, error, createdAt, claimedAt }] }` |
| POST | `/jobs/{id}/retry` | empty | updated job; 400 if not Failed |
| POST | `/jobs/{id}/cancel` | empty | updated job; 400 if already Succeeded |

Auth `/me` (and login/register response) gains `isAdmin: bool` so the client can gate nav
without decoding the JWT.

---

## 7. Web UI

| Route | Purpose |
|---|---|
| `/admin` | Redirect to `/admin/users` |
| `/admin/users` | Search + plan/quota actions |
| `/admin/jobs` | Filter + retry/cancel |

Layout: simple top nav “Users | Jobs | ← Back to app”. Confirm dialogs on plan change,
reset quota, retry, cancel. Toast or inline error on 403/400.

No design-system overhaul — reuse existing `btn-primary` / `card` tokens from the player app.

---

## 8. Security notes

- `IsAdmin` is not settable via any public API in v1.
- Bootstrap email must not default to a production wildcard; empty bootstrap = no auto-admin.
- Admin endpoints still require a valid JWT; stolen Free-user tokens cannot call them.
- Do not log passwords or full JWTs in admin responses.

Follow-up (not v1): `AdminActions` append-only log (actor, action, target, payload, utc).

---

## 9. Testing

| Layer | Cases |
|---|---|
| Unit / API | Non-admin → 403 on `/api/admin/users`; admin → 200 |
| Unit / API | Set Premium then quota allows analyze even when `AnalysesUsed >= 3` |
| Unit / API | Reset quota sets used to 0 |
| Unit / API | Retry Failed → Pending, Attempts 0; Cancel Succeeded → 400 |
| Bootstrap | Matching email sets IsAdmin on startup; non-matching untouched |
| Web | Smoke: admin sees nav link; non-admin does not |

---

## 10. Rollout (local)

1. Ship schema + JWT claim + admin API.
2. Set `Admin:BootstrapEmail` to your account; restart API (or SQL `UPDATE "Users" SET "IsAdmin" = true WHERE ...`).
3. Log out/in to refresh JWT.
4. Open `/admin`.

---

## 11. Open follow-ups

- Audit log table.
- Admin analyses browser / re-queue by analysis id.
- Promote/demote admin in UI with confirmation + second admin required.
- Stripe-aware plan display (read-only subscription id).
