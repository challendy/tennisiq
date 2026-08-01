"""Detect individual stroke peaks in a multi-hit clip."""

from __future__ import annotations

from dataclasses import dataclass

from app.kinematics.features import FrameFeatures

MAX_DURATION_S = 45.0
MAX_CANDIDATES = 8
MIN_GAP_S = 1.2
PRE_S = 0.6
POST_S = 0.8
PEAK_FRAC = 0.45
_LOCAL_RADIUS = 3


@dataclass(frozen=True)
class HitWindow:
    start_frame: int
    end_frame: int
    peak_frame: int
    start_ms: float
    end_ms: float


def clip_too_long(features: list[FrameFeatures]) -> bool:
    if len(features) < 2:
        return False
    duration_s = (features[-1].timestamp_ms - features[0].timestamp_ms) / 1000.0
    return duration_s > MAX_DURATION_S


def detect_hits(features: list[FrameFeatures]) -> list[HitWindow]:
    """Return stroke windows around hand-speed peaks.

    Empty when there is no usable motion. A single-stroke clip yields one window.
    """
    if len(features) < 5:
        return []

    speeds = [f.hand_speed_rel for f in features]
    peak = max(speeds)
    if peak <= 0:
        return []

    threshold = PEAK_FRAC * peak
    raw: list[int] = []
    n = len(features)
    for i in range(_LOCAL_RADIUS, n - _LOCAL_RADIUS):
        if speeds[i] < threshold:
            continue
        window = speeds[i - _LOCAL_RADIUS : i + _LOCAL_RADIUS + 1]
        if speeds[i] == max(window) and window.count(speeds[i]) == 1:
            raw.append(i)

    if not raw:
        # Fall back to the global peak so a quiet single stroke still grades.
        raw = [max(range(n), key=lambda i: speeds[i])]

    merged = _merge_by_gap(features, speeds, raw)
    if len(merged) > MAX_CANDIDATES:
        merged = sorted(merged, key=lambda i: speeds[i], reverse=True)[:MAX_CANDIDATES]
        merged.sort()

    return [_window_for_peak(features, i) for i in merged]


def _merge_by_gap(
    features: list[FrameFeatures],
    speeds: list[float],
    peaks: list[int],
) -> list[int]:
    if not peaks:
        return []
    kept: list[int] = [peaks[0]]
    for idx in peaks[1:]:
        prev = kept[-1]
        gap_s = (features[idx].timestamp_ms - features[prev].timestamp_ms) / 1000.0
        if gap_s < MIN_GAP_S:
            if speeds[idx] > speeds[prev]:
                kept[-1] = idx
        else:
            kept.append(idx)
    return kept


def _window_for_peak(features: list[FrameFeatures], peak_i: int) -> HitWindow:
    peak_ms = features[peak_i].timestamp_ms
    start_ms = peak_ms - PRE_S * 1000.0
    end_ms = peak_ms + POST_S * 1000.0
    start_i = 0
    end_i = len(features) - 1
    for i, f in enumerate(features):
        if f.timestamp_ms >= start_ms:
            start_i = i
            break
    for i in range(len(features) - 1, -1, -1):
        if features[i].timestamp_ms <= end_ms:
            end_i = i
            break
    if end_i < start_i:
        end_i = start_i
    return HitWindow(
        start_frame=start_i,
        end_frame=end_i,
        peak_frame=peak_i,
        start_ms=features[start_i].timestamp_ms,
        end_ms=features[end_i].timestamp_ms,
    )
