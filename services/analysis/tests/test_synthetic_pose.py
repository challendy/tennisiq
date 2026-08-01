from app.models import Handedness, Stroke
from app.pose.estimator import SyntheticPoseEstimator


def test_synthetic_pose_emits_expected_frame_count():
    poses = SyntheticPoseEstimator(frame_count=60).estimate()
    assert len(poses) == 60
    assert all("right_wrist" in p.landmarks for p in poses)


def test_synthetic_forehand_has_deep_takeback_and_high_finish():
    poses = SyntheticPoseEstimator(
        stroke=Stroke.FOREHAND,
        handedness=Handedness.RIGHT,
        frame_count=60,
    ).estimate()
    xs = [p.landmarks["right_wrist"].x for p in poses]
    ys = [p.landmarks["right_wrist"].y for p in poses]
    assert min(xs) <= 0.35  # deep takeback
    assert min(ys) <= 0.30  # high finish (small y)


def test_short_backswing_degradation():
    good = SyntheticPoseEstimator(short_backswing=False).estimate()
    bad = SyntheticPoseEstimator(short_backswing=True).estimate()
    assert min(p.landmarks["right_wrist"].x for p in good) < min(
        p.landmarks["right_wrist"].x for p in bad
    )
