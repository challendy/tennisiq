from app.kinematics.features import FrameFeatures
from app.segmentation.hits import (
    MAX_CANDIDATES,
    MAX_DURATION_S,
    MIN_GAP_S,
    clip_too_long,
    detect_hits,
)


def _feats(speeds: list[float], fps: float = 30.0) -> list[FrameFeatures]:
    out: list[FrameFeatures] = []
    for i, speed in enumerate(speeds):
        out.append(
            FrameFeatures(
                frame_index=i,
                timestamp_ms=(i / fps) * 1000.0,
                elbow_angle=90.0,
                shoulder_angle=90.0,
                hip_shoulder_separation=0.2,
                cog_x=0.5,
                cog_y=0.5,
                balance=1.0,
                hand_x=0.5,
                hand_y=0.5,
                hand_speed=speed,
                mean_visibility=1.0,
                torso_length=0.2,
                hand_x_rel=0.0,
                hand_y_rel=0.0,
                hand_speed_rel=speed,
            )
        )
    return out


def _pulse(center: int, height: float, width: int = 5) -> dict[int, float]:
    return {center + d: height * (1.0 - abs(d) / (width + 1)) for d in range(-width, width + 1)}


def test_detects_three_well_spaced_peaks():
    fps = 30.0
    n = int(10 * fps)
    speeds = [0.1] * n
    for center, height in ((45, 10.0), (120, 12.0), (200, 9.0)):
        for i, v in _pulse(center, height).items():
            if 0 <= i < n:
                speeds[i] = max(speeds[i], v)
    hits = detect_hits(_feats(speeds, fps))
    assert len(hits) == 3
    assert [h.peak_frame for h in hits] == [45, 120, 200]


def test_gap_merge_keeps_taller_peak():
    fps = 30.0
    n = int(4 * fps)
    speeds = [0.1] * n
    # Two peaks 0.5s apart — under MIN_GAP_S.
    assert 0.5 < MIN_GAP_S
    for i, v in _pulse(30, 8.0).items():
        speeds[i] = max(speeds[i], v)
    for i, v in _pulse(45, 11.0).items():
        speeds[i] = max(speeds[i], v)
    hits = detect_hits(_feats(speeds, fps))
    assert len(hits) == 1
    assert hits[0].peak_frame == 45


def test_caps_at_max_candidates_keeping_tallest():
    fps = 30.0
    # 10 peaks spaced 1.5s apart with increasing height.
    gap = int(1.5 * fps)
    n = gap * 12
    speeds = [0.05] * n
    centers = []
    for k in range(10):
        c = gap * (k + 1)
        centers.append(c)
        for i, v in _pulse(c, 5.0 + k).items():
            if 0 <= i < n:
                speeds[i] = max(speeds[i], v)
    hits = detect_hits(_feats(speeds, fps))
    assert len(hits) == MAX_CANDIDATES
    # Tallest 8 are the last 8 centers.
    assert [h.peak_frame for h in hits] == centers[-MAX_CANDIDATES:]


def test_single_peak_returns_one_window():
    fps = 30.0
    n = 60
    speeds = [0.1] * n
    for i, v in _pulse(30, 10.0).items():
        speeds[i] = max(speeds[i], v)
    hits = detect_hits(_feats(speeds, fps))
    assert len(hits) == 1
    assert hits[0].start_frame < hits[0].peak_frame < hits[0].end_frame


def test_clip_too_long():
    fps = 30.0
    n = int((MAX_DURATION_S + 5) * fps)
    feats = _feats([0.2] * n, fps)
    assert clip_too_long(feats)
    assert not clip_too_long(_feats([0.2] * 60, fps))
