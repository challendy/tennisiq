from pathlib import Path

from app.models import Handedness, Stroke
from app.pipeline import AnalysisPipeline
from app.pose.estimator import SyntheticPoseEstimator, write_blank_video


def test_pipeline_produces_overlay(tmp_path: Path):
    video = tmp_path / "blank.mp4"
    write_blank_video(video, frame_count=30)
    overlay = tmp_path / "overlay.mp4"
    pipe = AnalysisPipeline(estimator=SyntheticPoseEstimator(stroke=Stroke.FOREHAND))
    result, out, clip = pipe.analyze(
        video_path=video,
        stroke=Stroke.FOREHAND,
        handedness=Handedness.RIGHT,
        overlay_path=overlay,
    )
    assert result.status == "ok"
    assert clip is None
    assert out is not None and out.exists()
    assert out.stat().st_size > 1000
