"""The point of body-relative metrics: the same stroke scores the same
regardless of how it was filmed.

These are the properties that let a rubric threshold mean something. If they
break, thresholds have quietly gone back to encoding camera setup.
"""

from __future__ import annotations

from app.kinematics.features import compute_features
from app.models import FramePose, Handedness, Landmark, Stroke
from app.pose.estimator import SyntheticPoseEstimator
from app.scoring.grading import assess_quality, grade_analysis
from app.scoring.rubric import load_rubric, score_phases
from app.segmentation.phases import segment_phases


def _transform(poses: list[FramePose], scale: float = 1.0, mirror: bool = False) -> list[FramePose]:
    """Re-frame a clip: `scale` stands in for camera distance, `mirror` for
    filming from the opposite sideline (or a left-hander)."""
    out: list[FramePose] = []
    for pose in poses:
        landmarks = {}
        for name, lm in pose.landmarks.items():
            x = 0.5 + (lm.x - 0.5) * scale
            y = 0.5 + (lm.y - 0.5) * scale
            if mirror:
                x = 1.0 - x
            landmarks[name] = Landmark(x=x, y=y, z=lm.z, visibility=lm.visibility)
        out.append(
            FramePose(
                frame_index=pose.frame_index,
                timestamp_ms=pose.timestamp_ms,
                landmarks=landmarks,
            )
        )
    return out


def _grade(poses: list[FramePose]):
    features = compute_features(poses, Handedness.RIGHT)
    windows = segment_phases(features)
    phases = score_phases(features, windows, load_rubric(Stroke.FOREHAND))
    return grade_analysis(Stroke.FOREHAND, phases, features, assess_quality(features))


def test_camera_distance_does_not_change_the_grade():
    poses = SyntheticPoseEstimator(frame_count=60).estimate()
    close = _grade(poses)
    far = _grade(_transform(poses, scale=0.55))
    assert abs(close.overall_score - far.overall_score) < 1.0
    for a, b in zip(close.phases, far.phases):
        assert abs(a.score - b.score) < 1.0, f"{a.name} moved with camera distance"


def test_filming_from_the_other_side_does_not_change_the_grade():
    poses = SyntheticPoseEstimator(frame_count=60).estimate()
    normal = _grade(poses)
    mirrored = _grade(_transform(poses, mirror=True))
    assert abs(normal.overall_score - mirrored.overall_score) < 1.0
    for a, b in zip(normal.phases, mirrored.phases):
        assert abs(a.score - b.score) < 1.0, f"{a.name} moved when mirrored"


def test_a_short_backswing_still_reads_as_short_when_filmed_from_further_away():
    good = _grade(_transform(SyntheticPoseEstimator(frame_count=60).estimate(), scale=0.55))
    bad = _grade(
        _transform(
            SyntheticPoseEstimator(frame_count=60, short_backswing=True).estimate(),
            scale=0.55,
        )
    )
    good_takeback = next(p.score for p in good.phases if p.name.value == "takeback")
    bad_takeback = next(p.score for p in bad.phases if p.name.value == "takeback")
    assert bad_takeback < good_takeback - 20
