from __future__ import annotations

import tempfile
from pathlib import Path

from app.kinematics.features import compute_features
from app.models import AnalysisResult, Handedness, Stroke, View
from app.overlay.render import render_overlay
from app.pose.estimator import MediaPipePoseEstimator, PoseEstimator, SyntheticPoseEstimator
from app.scoring.grading import assess_quality, grade_analysis
from app.scoring.rubric import load_rubric, score_phases
from app.segmentation.phases import segment_phases


class AnalysisPipeline:
    def __init__(self, estimator: PoseEstimator | None = None) -> None:
        self.estimator = estimator or MediaPipePoseEstimator()

    def analyze(
        self,
        video_path: Path,
        stroke: Stroke = Stroke.FOREHAND,
        handedness: Handedness = Handedness.RIGHT,
        view: View = View.SIDE,
        overlay_path: Path | None = None,
        use_synthetic_if_blank: bool = False,
    ) -> tuple[AnalysisResult, Path | None]:
        del view  # reserved for view-specific rubrics later
        poses = self.estimator.estimate(video_path)

        # Optional escape hatch for demos without a real person in frame.
        if use_synthetic_if_blank:
            mean_vis = 0.0
            if poses:
                vals = [lm.visibility for p in poses for lm in p.landmarks.values()]
                mean_vis = sum(vals) / len(vals) if vals else 0.0
            if mean_vis < 0.2:
                poses = SyntheticPoseEstimator(stroke=stroke, handedness=handedness).estimate()

        features = compute_features(poses, handedness=handedness)
        issues = assess_quality(features)
        if issues:
            result = grade_analysis(stroke, [], features, issues)
            return result, None

        windows = segment_phases(features)
        rubric = load_rubric(stroke)
        phase_scores = score_phases(features, windows, rubric)
        result = grade_analysis(stroke, phase_scores, features, [])

        out = overlay_path
        if out is None:
            tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
            out = Path(tmp.name)
            tmp.close()
        out = render_overlay(
            source_video=video_path if video_path.exists() else None,
            poses=poses,
            features=features,
            windows=windows,
            output_path=out,
            handedness=handedness,
        )
        return result, out
