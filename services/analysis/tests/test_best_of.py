from app.models import AnalysisResult, QualityIssue, Stroke
from app.pose.estimator import SyntheticPoseEstimator
from app.kinematics.features import compute_features
from app.models import Handedness
from app.segmentation.best_of import ScoredHit, pick_best, score_hit_window
from app.segmentation.hits import HitWindow, detect_hits


def test_pick_best_skips_insufficient_and_takes_highest_ok():
    scored = [
        ScoredHit(
            0,
            HitWindow(0, 10, 5, 0, 100),
            AnalysisResult(
                stroke=Stroke.FOREHAND,
                status="insufficient_quality",
                overall_score=0,
                grade="—",
                confidence=0,
                quality_issues=[QualityIssue(code="x", message="m", tip="t")],
            ),
        ),
        ScoredHit(
            1,
            HitWindow(20, 30, 25, 200, 300),
            AnalysisResult(
                stroke=Stroke.FOREHAND,
                status="ok",
                overall_score=80,
                grade="B",
                confidence=0.8,
            ),
        ),
        ScoredHit(
            2,
            HitWindow(40, 50, 45, 400, 500),
            AnalysisResult(
                stroke=Stroke.FOREHAND,
                status="ok",
                overall_score=92,
                grade="A",
                confidence=0.9,
            ),
        ),
    ]
    best = pick_best(scored)
    assert best is not None
    assert best.index == 2


def test_pick_best_tie_prefers_earlier():
    scored = [
        ScoredHit(
            0,
            HitWindow(0, 10, 5, 0, 100),
            AnalysisResult(stroke=Stroke.FOREHAND, status="ok", overall_score=88, grade="B", confidence=0.8),
        ),
        ScoredHit(
            1,
            HitWindow(20, 30, 25, 200, 300),
            AnalysisResult(stroke=Stroke.FOREHAND, status="ok", overall_score=88, grade="B", confidence=0.8),
        ),
    ]
    assert pick_best(scored).index == 0


def test_pick_best_all_rejected_returns_none():
    scored = [
        ScoredHit(
            0,
            HitWindow(0, 10, 5, 0, 100),
            AnalysisResult(
                stroke=Stroke.FOREHAND,
                status="insufficient_quality",
                overall_score=0,
                grade="—",
                confidence=0,
            ),
        )
    ]
    assert pick_best(scored) is None


def test_score_hit_window_grades_synthetic_slice():
    poses = SyntheticPoseEstimator(frame_count=60).estimate()
    feats = compute_features(poses, Handedness.RIGHT)
    hits = detect_hits(feats)
    assert len(hits) == 1
    result = score_hit_window(poses, feats, hits[0], Stroke.FOREHAND)
    assert result.status == "ok"
    assert result.overall_score >= 70
