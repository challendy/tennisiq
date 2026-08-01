import math

from app.kinematics.features import _angle, compute_features
from app.models import Handedness
from app.pose.estimator import SyntheticPoseEstimator


def test_angle_right_angle():
    assert math.isclose(_angle((0, 1), (0, 0), (1, 0)), 90.0, abs_tol=1e-6)


def test_features_have_positive_peak_hand_speed():
    poses = SyntheticPoseEstimator(frame_count=60).estimate()
    feats = compute_features(poses, handedness=Handedness.RIGHT)
    assert len(feats) == 60
    assert max(f.hand_speed for f in feats) > 0.5
    assert all(0.0 <= f.balance <= 1.0 for f in feats)
    assert all(0.0 <= f.mean_visibility <= 1.0 for f in feats)
