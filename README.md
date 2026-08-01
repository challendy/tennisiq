# TennisIQ

AI-powered tennis improvement from ordinary phone video.

**Vision:** explain *why* a stroke looked the way it did, and name the highest-impact fix.

This repo contains the **v0.1 MVP** — the Record → Analyze → Understand → Practice → Track loop for individual strokes — plus the product roadmap for everything after.

| Doc | Purpose |
|---|---|
| [`docs/PRODUCT_REQUIREMENTS_v1.md`](docs/PRODUCT_REQUIREMENTS_v1.md) | Original product requirements |
| [`docs/specs/2026-08-01-tennisiq-mvp-design.md`](docs/specs/2026-08-01-tennisiq-mvp-design.md) | MVP design (scope, architecture, data model) |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Long-term roadmap (Phases 0–5) |
| [`docs/plans/2026-08-01-tennisiq-mvp-plan.md`](docs/plans/2026-08-01-tennisiq-mvp-plan.md) | Implementation plan |

---

## Architecture

```
web (Next.js)  →  api (ASP.NET Core)  →  analysis (Python / MediaPipe)
                         ↓
                     PostgreSQL
                         ↓
                   local storage (videos + overlays)
```

- **Python** owns pixels and biomechanics.
- **.NET** owns history, auth, quota, jobs, coaching narration, practice plans.
- **Web** owns presentation (mobile-first). Flutter comes in Phase 1 against the same API.

---

## Quick start (local, no Docker)

Prerequisites: Python 3.12, .NET 10 SDK, Node 22+, PostgreSQL 16, pnpm.

```bash
# 1) Database (Homebrew example)
brew services start postgresql@16
createdb tennisiq   # once

# 2) Analysis service
cd services/analysis
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8090

# 3) API (new terminal)
cd src
dotnet run --project TennisIQ.Api --urls http://localhost:5129

# 4) Web (new terminal)
cd web
pnpm install
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000). Register, upload a stroke video (side view), wait for the analysis.

> Tips: film from the side; a basket of the same stroke in one take is fine — TennisIQ splits the hits, quality-gates them, and keeps the best (counts as one analysis). If MediaPipe can't see a person, the API can fall back to a synthetic pose so blank/test clips still demo the loop.

### Admin ops console

Set `Admin:BootstrapEmail` in `src/TennisIQ.Api/appsettings.json` (default `chris@tennisiq.local`), restart the API, then log in as that user. An **Admin** link appears in the nav → `/admin/users` (plan / quota) and `/admin/jobs` (retry / cancel).

Existing local DBs need the column (API also runs this on startup):

```sql
ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS "IsAdmin" boolean NOT NULL DEFAULT false;
UPDATE "Users" SET "IsAdmin" = true WHERE "Email" = 'chris@tennisiq.local';
```

Log out and back in so the JWT picks up `is_admin`.

### Tests

```bash
cd services/analysis && .venv/bin/pytest -q
cd src && dotnet test
```

### Docker Compose

Requires Docker Desktop running:

```bash
docker compose up --build
```

---

## MVP feature map

| Feature | Status |
|---|---|
| AI stroke analysis (5 strokes) | ✅ |
| Frame-by-frame phase scores | ✅ |
| Visual overlay MP4 | ✅ |
| AI voice coach (Web Speech API) | ✅ |
| Shot comparison | ✅ |
| Practice planner | ✅ |
| Progress dashboard | ✅ |
| Free-tier quota (3/month) | ✅ |
| Match review / ball tracking | Phase 2 |
| Equipment advisor / gamification | Phase 3 |
| Coach / Club mode | Phase 4 |
| Flutter mobile client | Phase 1 |
| Stripe billing | Phase 1 |

---

## North star

> Hours of meaningful practice improved by AI guidance per player each month.

The long-term moat is the **Player Knowledge Graph** — see the roadmap.
