# Multi-Hit Best-Of Design

**Date:** 2026-08-01  
**Status:** Approved for implementation  
**Parent:** `docs/specs/2026-08-01-tennisiq-mvp-design.md`  
**Decisions locked with Chris:** auto in upload flow; quality-gate then highest overall; counts as one quota; light UI disclosure (no picker).

---

## 1. Problem

The analysis pipeline assumes **one stroke per clip**. Contact is the peak of
`hand_speed_rel` in the middle of the video. On-court filming often captures a basket
of the same stroke in one take. Today that either fails the quality gate, or grades the
wrong peak and lies confidently.

Players should be able to film several hits without cutting in the camera roll. TennisIQ
should split the clip, score each hit, keep the best, and charge one analysis.

---

## 2. Non-goals

- User picker / override of which hit to keep (Phase-later; this design only discloses).
- Match / rally segmentation, ball tracking, or mixed stroke types in one clip.
- Client-side splitting (ffmpeg.wasm, etc.).
- Persisting every candidate as its own analysis row.
- Changing Free-tier limits beyond “one multi-hit upload = one quota unit.”

---

## 3. Product behaviour

1. User uploads as today (stroke, handedness, video).
2. If the clip contains **one** stroke candidate → identical to current single-stroke path.
3. If it contains **two or more** → multi-hit mode:
   - Score each candidate window with the existing pipeline.
   - Discard candidates that fail `assess_quality`.
   - Among survivors, keep the highest `overall_score` (tie → earlier hit).
4. Persist **only** the kept window as the canonical video + overlay + analysis (full
   basket is not what the player rewatches).
5. Analysis page shows a light note, e.g.  
   `Picked hit 3 of 7 (score 88.3)`.
6. Quota: **one** charge for the kept analysis.

### Failure modes

| Case | Behaviour |
|---|---|
| 0 candidates after peak detection | `insufficient_quality` — tip: film a clearer stroke / closer camera |
| ≥1 candidates, 0 pass quality gate | `insufficient_quality` — tip: none of the hits were filmable enough (not a fabricated grade) |
| Source longer than max duration (45 s) | Soft reject before scoring: ask for a shorter basket |
| More than 8 peaks after gap filtering | Keep the 8 tallest; do **not** reject the upload |
| Exactly 1 candidate | Single-stroke path; no multi-hit metadata required |

---

## 4. Architecture

Splitting and ranking live in the **Python analysis service**, next to pose and
kinematics. The ASP.NET API remains one job / one analysis. The web client only renders
the disclosure fields.

```
web upload
   → API (quota −1, enqueue job)
      → analysis POST /analyze  (unchanged external contract + new optional fields)
         1. pose + features on full clip
         2. detect stroke peaks
         3. if N < 2: existing single-stroke pipeline
         4. if N ≥ 2: window each peak → analyze each → quality filter → pick best
         5. return AnalysisResult for the kept hit + multi_hit metadata
      → worker stores kept overlay / result JSON as today
```

Approach rejected: rank by peak speed then grade once (fastest ≠ best technique).  
Approach rejected: client-side cut (duplicates CV logic, brittle on mobile).

---

## 5. Detection algorithm

Input: `list[FrameFeatures]` for the full clip (already body-relative).

1. Let `peak = max(hand_speed_rel)`.
2. Find local maxima where `hand_speed_rel[i] ≥ 0.45 * peak` and `i` is a strict local max
   in a ±3-frame neighbourhood.
3. Enforce a minimum gap of **1.2 seconds** between accepted peaks (keep the taller peak
   when two collide).
4. Cap at **8** candidates (keep the 8 tallest peaks if more).
5. For each peak at time `t`, cut a window  
   `[t − 0.6s, t + 0.8s]` clamped to the clip.  
   Re-index frames to start at 0 for the child analyze call.
6. Reject the source clip before step 5 if duration **> 45 seconds**.

Constants live in one module (`app/segmentation/hits.py`) so they can be tuned from
synthetic multi-hit fixtures without touching the rubric.

Pose is run **once** on the full clip; child analyzes reuse the sliced pose/feature
lists (no second MediaPipe pass per hit). Overlay is rendered only for the kept window,
re-reading that slice of the source video.

---

## 6. Scoring and selection

For each window (sliced pose + features from the single full-clip pass — **no** second
MediaPipe run):

1. Run `segment_phases` → `score_phases` → `grade_analysis` / `assess_quality` exactly as
   single-stroke does today (same stroke/handedness from the request).
2. If `status != "ok"`, mark candidate `insufficient_quality` with the quality issue codes;
   do not compete for “best.”
3. Among `ok` candidates, pick `max(overall_score)`; ties prefer lower index (earlier).

After a winner is chosen, render the overlay from the **kept window only**, and also
export a cut of the source video for that window (same codec path as overlay). The API
worker replaces the stored upload with that cut when `multi_hit.enabled`, so playback
and compare show one stroke — not the whole basket. Timestamps of the kept window are
included in `multi_hit` for debugging even if the cut bytes are what get persisted.

The kept `AnalysisResult` is what the API already persists. Additional payload:

```json
"multi_hit": {
  "enabled": true,
  "detected": 7,
  "kept_index": 2,
  "kept_score": 88.3,
  "kept_window_ms": [4120, 5520],
  "candidates": [
    {"index": 0, "score": 71.2, "status": "ok"},
    {"index": 1, "score": null, "status": "insufficient_quality"},
    {"index": 2, "score": 88.3, "status": "ok", "kept": true}
  ]
}
```

Sibling fields on the analyze response (same pattern as overlay today):

- `clip_ready` / `clip_token` — downloadable kept-window source MP4 (only when multi-hit
  kept a window; single-stroke path leaves these unset and the API keeps the original upload).

When multi-hit did not run: omit `multi_hit` or set `"enabled": false` so older clients
ignore it.

---

## 7. API / persistence / UI

| Layer | Change |
|---|---|
| Analysis `POST /analyze` | Same multipart inputs. Response gains optional `multi_hit`, and when multi-hit keeps a window also `clip_ready` / `clip_token`. Overlay token is always the kept stroke only. |
| `AnalysisServiceClient` | Deserialize `multi_hit`; if `clip_ready`, download the cut and overwrite the stored video key in the worker. |
| `Analysis.ResultJson` | Store full response including `multi_hit` (already opaque JSON). |
| Quota | Unchanged: one upload → one analysis row → one Free-tier unit. |
| Web analysis page | If `multi_hit.enabled`, show one line under the grade: “Picked hit {n} of {detected} (score {kept_score}).” Display index is 1-based in copy (`kept_index + 1`). No list UI in this slice. |

No new HTTP endpoint. No new DB table.

---

## 8. Limits and cost

| Limit | Value | Rationale |
|---|---|---|
| Max source duration | 45 s | Bounds MediaPipe cost and candidate count |
| Max candidates scored | 8 | Caps N× phase scoring / overlay decision |
| Min gap between peaks | 1.2 s | One swing ≠ three peaks |
| Window padding | −0.6 s / +0.8 s | Ready through finish without swallowing the next hit |

Pose once + feature slice keeps cost closer to “one long clip” than “N full analyzes.”
Overlay render remains the expensive second pass and runs only for the winner.

---

## 9. Testing

| Layer | Cases |
|---|---|
| Unit — detection | Synthetic multi-peak speed curve → expected indices; gap merging; cap at 8; single peak → multi-hit disabled |
| Unit — selection | Mix of ok / insufficient_quality → winner is best ok; all rejected → insufficient_quality result; tie → earlier index |
| Integration | Synthetic multi-hit pose sequence → overall equals analyzing the winning window alone; disclosure fields present |
| Regression | Existing single-stroke tests unchanged in behaviour when only one peak exists |
| Smoke | Optional: multi-peak blank/synthetic upload returns `multi_hit.enabled` |

Calibration helpers: extend `scripts/calibrate.py` or add `scripts/multi_hit_fixture.py`
that concatenates N synthetic strokes with idle gaps.

---

## 10. Rollout

1. Ship detection + selection behind the existing `/analyze` path (no feature flag required
   for local MVP; behaviour is additive).
2. API/web pick up `multi_hit` fields.
3. Restart analysis service so production-local picks up the module.
4. Document filming tip: “Basket of the same stroke is fine; we’ll keep the best.”

---

## 11. Open follow-ups (explicitly out of this slice)

- Picker UI to override the auto choice.
- Stroke classification per hit (mixed baskets).
- Adaptive window padding from phase lengths.
- Golden real-phone multi-hit regression set.
