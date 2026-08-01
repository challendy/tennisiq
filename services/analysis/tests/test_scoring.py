from app.kinematics.features import compute_features
from app.models import Handedness, Stroke
from app.pose.estimator import SyntheticPoseEstimator
from app.scoring.grading import assess_quality, grade_analysis
from app.scoring.rubric import load_rubric, score_phases
from app.segmentation.phases import segment_phases


def _analyze(estimator: SyntheticPoseEstimator):
    poses = estimator.estimate()
    feats = compute_features(poses, Handedness.RIGHT)
    windows = segment_phases(feats)
    rubric = load_rubric(Stroke.FOREHAND)
    phases = score_phases(feats, windows, rubric)
    return grade_analysis(Stroke.FOREHAND, phases, feats, assess_quality(feats))


def test_good_synthetic_forehand_grades_well():
    result = _analyze(SyntheticPoseEstimator(frame_count=60))
    assert result.status == "ok"
    assert result.overall_score >= 70
    assert result.grade in {"A", "B", "C"}
    assert len(result.phases) == 8
    assert result.top_fix


def test_short_backswing_lowers_takeback_and_surfaces_fix():
    good = _analyze(SyntheticPoseEstimator(short_backswing=False))
    bad = _analyze(SyntheticPoseEstimator(short_backswing=True))
    good_tb = next(p.score for p in good.phases if p.name.value == "takeback")
    bad_tb = next(p.score for p in bad.phases if p.name.value == "takeback")
    assert bad_tb < good_tb
    blob = (bad.top_fix + " " + " ".join(bad.weaknesses)).lower()
    assert any(word in blob for word in ("takeback", "backswing", "take the racquet", "unit turn"))


def test_low_visibility_returns_insufficient_quality():
    result = _analyze(SyntheticPoseEstimator(visibility=0.1, frame_count=60))
    assert result.status == "insufficient_quality"
    assert result.quality_issues
    assert any(i.code == "low_visibility" for i in result.quality_issues)
