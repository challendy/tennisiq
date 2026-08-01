# TennisIQ MVP Implementation Plan

> **For agentic workers:** This plan is executable top-to-bottom. Each task
> names exact files, commands, and a verification step. Prefer small commits.
> Work from `/Users/chrishallendy/Projects/tennisiq`.

**Goal:** Ship the Record → Analyze → Understand → Practice → Track loop for
individual strokes, runnable via `docker compose up`, with no third-party API
key required.

**Architecture:** Python CV service + ASP.NET Core API + Next.js web + Postgres.
See `docs/specs/2026-08-01-tennisiq-mvp-design.md`.

---

## Task 1: Repo skeleton & ignore rules

**Files:**
- Create: `.gitignore`, `README.md`, `docker-compose.yml` (stubs ok)
- Create: `services/analysis/requirements.txt`, `services/analysis/pyproject.toml`

**Verify:** `git status` shows a clean tree of new files only.

---

## Task 2: Analysis models & pose protocol (TDD)

**Files:**
- Create: `services/analysis/app/models.py` — `Landmark`, `FramePose`, `PhaseName`,
  `PhaseScore`, `AnalysisResult`, `QualityIssue`
- Create: `services/analysis/app/pose/estimator.py` — `PoseEstimator` protocol +
  `SyntheticPoseEstimator` that emits a deterministic forehand curve
- Create: `services/analysis/tests/test_synthetic_pose.py`

**Verify:** `cd services/analysis && .venv/bin/pytest tests/test_synthetic_pose.py -q`

---

## Task 3: Kinematics (TDD)

**Files:**
- Create: `services/analysis/app/kinematics/features.py`
- Create: `services/analysis/tests/test_kinematics.py`

Compute: elbow angle, shoulder angle, hip–shoulder separation, CoG, balance,
hand speed. Pure functions.

**Verify:** pytest green for kinematics.

---

## Task 4: Phase segmentation (TDD)

**Files:**
- Create: `services/analysis/app/segmentation/phases.py`
- Create: `services/analysis/tests/test_phases.py`

Eight phases: ready, unit_turn, takeback, racquet_drop, acceleration, contact,
extension, finish. Segment from hand-speed / hand-position curves of the
synthetic forehand.

**Verify:** synthetic forehand yields all 8 phases in order with contact near
peak hand speed.

---

## Task 5: Rubric scoring & grading (TDD)

**Files:**
- Create: `services/analysis/rubrics/forehand.json` (+ serve, backhand, volley, overhead)
- Create: `services/analysis/app/scoring/rubric.py`, `grading.py`
- Create: `services/analysis/tests/test_scoring.py`

**Verify:** ideal synthetic stroke grades A/B; deliberately degraded stroke
grades lower and surfaces the expected top fix; low-visibility input returns
`insufficient_quality`.

---

## Task 6: Overlay renderer + FastAPI entrypoint

**Files:**
- Create: `services/analysis/app/overlay/render.py`
- Create: `services/analysis/app/pipeline.py`, `app/main.py`
- Create: `services/analysis/tests/test_pipeline_integration.py`
- Create: `services/analysis/Dockerfile`

**Verify:** `POST /analyze` on a tiny generated mp4 returns JSON + overlay bytes;
pytest integration green.

---

## Task 7: ASP.NET solution skeleton

**Files:**
- Create: `src/TennisIQ.sln`, `src/TennisIQ.Api/`, `src/TennisIQ.Domain/`,
  `src/TennisIQ.Infrastructure/`, `src/TennisIQ.Api.Tests/`

**Verify:** `dotnet build src/TennisIQ.sln` succeeds.

---

## Task 8: Domain + EF Core + Postgres

**Files:** entities, `AppDbContext`, migrations, `LocalVideoStorage`,
`PostgresAnalysisJobQueue`.

**Verify:** `dotnet test` for storage/queue unit tests; migrate against compose Postgres.

---

## Task 9: Auth, quota, analysis endpoints, worker, narrator, planner

**Files:** auth controllers, JWT, `AnalysisWorker`, `RuleBasedCoachNarrator`,
`LlmCoachNarrator`, `PracticePlanner`, compare endpoint.

**Verify:** integration-style API tests covering signup → upload → job → result,
quota 402, compare, practice plan.

---

## Task 10: Next.js web client

**Files:** `web/` — auth, upload, analysis result (overlay + phases + voice),
dashboard, compare, practice.

**Verify:** `pnpm build` succeeds; manual smoke against local API.

---

## Task 11: Docker compose + README + end-to-end smoke

**Files:** finalize `docker-compose.yml`, root `README.md`, seed drills SQL/JSON.

**Verify:** `docker compose up --build` → signup → upload synthetic clip → graded
result with overlay → compare → practice plan → 4th upload 402.
