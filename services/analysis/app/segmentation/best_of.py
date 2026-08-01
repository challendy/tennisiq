"""Score individual hit windows and pick the best survivor."""

from __future__ import annotations

from dataclasses import dataclass

from app.kinematics.features import FrameFeatures
from app.models import AnalysisResult, FramePose, Handedness, Stroke
from app.scoring.grading import assess_quality, grade_analysis
from app.scoring.rubric import load_rubric, score_phases
from app.segmentation.hits import HitWindow
from app.segmentation.phases import segment_phases


@dataclass
class ScoredHit:
    index: int
    window: HitWindow
    result: AnalysisResult


def slice_poses(poses: list[FramePose], window: HitWindow) -> list[FramePose]:
    chunk = poses[window.start_frame : window.end_frame + 1]
    if not chunk:
        return []
    t0 = chunk[0].timestamp_ms
    return [
        FramePose(
            frame_index=i,
            timestamp_ms=p.timestamp_ms - t0,
            landmarks=p.landmarks,
        )
        for i, p in enumerate(chunk)
    ]


def slice_features(features: list[FrameFeatures], window: HitWindow) -> list[FrameFeatures]:
    chunk = features[window.start_frame : window.end_frame + 1]
    if not chunk:
        return []
    t0 = chunk[0].timestamp_ms
    return [
        FrameFeatures(
            frame_index=i,
            timestamp_ms=f.timestamp_ms - t0,
            elbow_angle=f.elbow_angle,
            shoulder_angle=f.shoulder_angle,
            hip_shoulder_separation=f.hip_shoulder_separation,
            cog_x=f.cog_x,
            cog_y=f.cog_y,
            balance=f.balance,
            hand_x=f.hand_x,
            hand_y=f.hand_y,
            hand_speed=f.hand_speed,
            mean_visibility=f.mean_visibility,
            torso_length=f.torso_length,
            hand_x_rel=f.hand_x_rel,
            hand_y_rel=f.hand_y_rel,
            hand_speed_rel=f.hand_speed_rel,
        )
        for i, f in enumerate(chunk)
    ]


def score_hit_window(
    poses: list[FramePose],
    features: list[FrameFeatures],
    window: HitWindow,
    stroke: Stroke,
    handedness: Handedness = Handedness.RIGHT,
) -> AnalysisResult:
    del handedness  # features are already handedness-aware
    sliced_feats = slice_features(features, window)
    issues = assess_quality(sliced_feats)
    if issues:
        return grade_analysis(stroke, [], sliced_feats, issues)

    windows = segment_phases(sliced_feats)
    phase_scores = score_phases(sliced_feats, windows, load_rubric(stroke))
    return grade_analysis(stroke, phase_scores, sliced_feats, [])


def pick_best(scored: list[ScoredHit]) -> ScoredHit | None:
    """Highest overall among ok results; ties prefer earlier index."""
    ok = [s for s in scored if s.result.status == "ok"]
    if not ok:
        return None
    return min(ok, key=lambda s: (-s.result.overall_score, s.index))
