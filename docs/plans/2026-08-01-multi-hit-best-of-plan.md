# Multi-Hit Best-Of Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect multiple strokes in one upload, quality-gate each, keep the highest overall score, charge one quota, and show a light “Picked hit N of M” note.

**Architecture:** Peak detection and per-window scoring live in the Python analysis service (pose once, slice features, grade each window, overlay + cut clip for the winner). The ASP.NET worker downloads an optional kept clip and overwrites the stored video. The web analysis page reads `multiHit` from `resultJson` / API DTO and shows one disclosure line.

**Tech Stack:** FastAPI / MediaPipe / OpenCV, ASP.NET Core worker, Next.js analysis page.

**Spec:** `docs/specs/2026-08-01-multi-hit-best-of-design.md`

## Global Constraints

- Max source duration 45s; max 8 candidates; min peak gap 1.2s; window −0.6s / +0.8s.
- Quality-gate then highest `overall_score`; ties → earlier index.
- One quota unit per upload; no picker UI.
- Single-peak clips must behave identically to today.

---

### Task 1: Hit detection (`hits.py`)

**Files:**
- Create: `services/analysis/app/segmentation/hits.py`
- Test: `services/analysis/tests/test_hits.py`

**Interfaces:**
- Produces: `HitWindow(start_frame, end_frame, peak_frame, start_ms, end_ms)`, `detect_hits(features) -> list[HitWindow]`, `clip_too_long(features) -> bool`
- Constants: `MAX_DURATION_S=45`, `MAX_CANDIDATES=8`, `MIN_GAP_S=1.2`, `PRE_S=0.6`, `POST_S=0.8`, `PEAK_FRAC=0.45`

- [ ] **Step 1: Write failing tests** for local maxima, gap merge (keep taller), cap at 8 tallest, single peak returns one window, duration > 45s flagged.
- [ ] **Step 2: Implement `detect_hits` / `clip_too_long`.**
- [ ] **Step 3: `pytest tests/test_hits.py -q` → pass.**

---

### Task 2: Score windows + pick best

**Files:**
- Create: `services/analysis/app/segmentation/best_of.py`
- Modify: `services/analysis/app/models.py` (add `MultiHitInfo`, `MultiHitCandidate`; optional `multi_hit` on `AnalysisResult`)
- Test: `services/analysis/tests/test_best_of.py`

**Interfaces:**
- Produces: `score_hit_window(poses, features, stroke, handedness) -> AnalysisResult`, `pick_best(candidates) -> (index, result) | None`
- Candidate record: index, window, result

- [ ] **Step 1: Failing tests** — ok vs insufficient mix picks best ok; all rejected → None; tie → earlier.
- [ ] **Step 2: Implement** by slicing poses/features, reindexing frame indices and relative timestamps, then existing segment/score/grade path.
- [ ] **Step 3: Tests pass.**

---

### Task 3: Wire pipeline + clip export + HTTP tokens

**Files:**
- Modify: `services/analysis/app/pipeline.py`
- Modify: `services/analysis/app/main.py` (`/clip/{token}`, `clip_ready`/`clip_token`)
- Create: `services/analysis/app/overlay/cut.py` (export source window via OpenCV)
- Test: `services/analysis/tests/test_multi_hit_pipeline.py`

**Behaviour:**
1. Pose + features on full clip.
2. If `clip_too_long` → insufficient_quality with tip about shorter basket.
3. `hits = detect_hits(features)`.
4. If `len(hits) < 2` → existing single-stroke path (no `multi_hit`).
5. Else score each hit; if no ok survivors → insufficient_quality with multi-hit tip; else pick best, set `multi_hit` metadata, render overlay on kept slice, export cut clip.
6. Return `(result, overlay_path, clip_path | None)`.

- [ ] **Step 1: Integration test** with concatenated synthetic poses (2–3 strokes, middle one degraded) → `multi_hit.enabled`, kept index correct, single-peak still has no multi_hit.
- [ ] **Step 2: Implement pipeline + cut + main.py clip endpoint.**
- [ ] **Step 3: Full `pytest -q` passes.**

---

### Task 4: ASP.NET client + worker overwrite stored video

**Files:**
- Modify: `src/TennisIQ.Infrastructure/Cv/AnalysisServiceClient.cs`
- Modify: `src/TennisIQ.Api/Workers/AnalysisWorker.cs`
- Modify: `src/TennisIQ.Infrastructure/Storage/LocalVideoStorage.cs` if needed (`ReplaceAsync` or save-new + update key)
- Modify: API analysis DTO / controller so web can read `multiHit` (parse from `ResultJson` or expose field)

- [ ] **Step 1: Deserialize `MultiHit`, `ClipReady`, `ClipToken`; download clip bytes like overlay.**
- [ ] **Step 2: When clip bytes present, overwrite `job.Video.StorageKey` content (or save new key and update Video row).**
- [ ] **Step 3: `dotnet test` passes.**

---

### Task 5: Web disclosure line

**Files:**
- Modify: `web/src/lib/api.ts` (types)
- Modify: `web/src/app/analyses/[id]/page.tsx`
- Modify: API get-analysis response if `multiHit` is not already inside parsed JSON sent to client

- [ ] **Step 1: Show** `Picked hit {kept_index+1} of {detected} (score {kept_score})` when `multiHit?.enabled`.
- [ ] **Step 2: Manual check or ensure DTO wiring.**

---

### Task 6: Verify + commit

- [ ] Restart analysis service; run `pytest` + `dotnet test` + `scripts/smoke.sh`.
- [ ] Commit in logical chunks if not already; push only if asked.
