from app.kinematics.features import compute_features
from app.models import PHASE_ORDER, Handedness
from app.pose.estimator import SyntheticPoseEstimator
from app.segmentation.phases import segment_phases


def test_synthetic_forehand_yields_all_eight_phases_in_order():
    poses = SyntheticPoseEstimator(frame_count=60).estimate()
    feats = compute_features(poses, Handedness.RIGHT)
    windows = segment_phases(feats)
    assert [w.name for w in windows] == PHASE_ORDER
    contact = next(w for w in windows if w.name.value == "contact")
    assert contact.contact_frame is not None
    # Contact near peak hand speed
    peak = max(range(len(feats)), key=lambda i: feats[i].hand_speed)
    assert abs(contact.contact_frame - peak) <= 3
