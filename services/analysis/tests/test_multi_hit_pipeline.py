from pathlib import Path

from app.kinematics.features import compute_features
from app.models import FramePose, Handedness, Landmark, Stroke
from app.pipeline import AnalysisPipeline
from app.pose.estimator import SyntheticPoseEstimator, write_blank_video
from app.segmentation.hits import detect_hits


class ConcatSyntheticEstimator:
    """Concatenate several synthetic strokes with idle gaps (pose-only, no video)."""

    def __init__(self, variants: list[dict], gap_frames: int = 45, fps: float = 30.0) -> None:
        self.variants = variants
        self.gap_frames = gap_frames
        self.fps = fps

    def estimate(self, video_path: Path | None = None) -> list[FramePose]:
        del video_path
        frames: list[FramePose] = []
        t_ms = 0.0
        dt = 1000.0 / self.fps
        for vi, kwargs in enumerate(self.variants):
            stroke_frames = SyntheticPoseEstimator(frame_count=60, fps=self.fps, **kwargs).estimate()
            for p in stroke_frames:
                frames.append(
                    FramePose(
                        frame_index=len(frames),
                        timestamp_ms=t_ms,
                        landmarks=p.landmarks,
                    )
                )
                t_ms += dt
            if vi < len(self.variants) - 1:
                last = frames[-1].landmarks
                for _ in range(self.gap_frames):
                    # Idle: hold the finish pose with near-zero motion.
                    frames.append(
                        FramePose(
                            frame_index=len(frames),
                            timestamp_ms=t_ms,
                            landmarks={
                                k: Landmark(x=lm.x, y=lm.y, z=lm.z, visibility=lm.visibility)
                                for k, lm in last.items()
                            },
                        )
                    )
                    t_ms += dt
        return frames


def test_pipeline_single_stroke_unchanged(tmp_path: Path):
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
    assert result.multi_hit is None
    assert clip is None
    assert out is not None and out.exists() and out.stat().st_size > 1000


def test_multi_hit_picks_best_of_three():
    # Middle stroke is short-backswing (worse); flanks are ideal.
    estimator = ConcatSyntheticEstimator(
        [
            {},
            {"short_backswing": True},
            {},
        ],
        gap_frames=45,
    )
    poses = estimator.estimate()
    feats = compute_features(poses, Handedness.RIGHT)
    hits = detect_hits(feats)
    assert len(hits) >= 2

    pipe = AnalysisPipeline(estimator=estimator)  # type: ignore[arg-type]
    # video path unused by ConcatSyntheticEstimator
    result, overlay, clip = pipe.analyze(
        video_path=Path("/nonexistent.mp4"),
        stroke=Stroke.FOREHAND,
        handedness=Handedness.RIGHT,
    )
    assert result.status == "ok"
    assert result.multi_hit is not None
    assert result.multi_hit.enabled
    assert result.multi_hit.detected >= 2
    assert result.multi_hit.kept_index is not None
    # Short backswing in the middle should not win.
    assert result.multi_hit.kept_index != 1
    assert overlay is not None and overlay.exists()
