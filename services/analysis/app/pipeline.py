from __future__ import annotations

import tempfile
from pathlib import Path

from app.kinematics.features import compute_features
from app.models import (
    AnalysisResult,
    Handedness,
    MultiHitCandidate,
    MultiHitInfo,
    QualityIssue,
    Stroke,
    View,
)
from app.overlay.cut import cut_video_window
from app.overlay.render import render_overlay
from app.pose.estimator import MediaPipePoseEstimator, PoseEstimator, SyntheticPoseEstimator
from app.scoring.grading import assess_quality, grade_analysis
from app.scoring.rubric import load_rubric, score_phases
from app.segmentation.best_of import (
    ScoredHit,
    pick_best,
    score_hit_window,
    slice_features,
    slice_poses,
)
from app.segmentation.hits import clip_too_long, detect_hits
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
        clip_path: Path | None = None,
        use_synthetic_if_blank: bool = False,
    ) -> tuple[AnalysisResult, Path | None, Path | None]:
        """Return (result, overlay_path, kept_clip_path).

        kept_clip_path is set only when multi-hit mode keeps a window from a real file.
        """
        del view  # reserved for view-specific rubrics later
        poses = self.estimator.estimate(video_path)

        if use_synthetic_if_blank:
            mean_vis = 0.0
            if poses:
                vals = [lm.visibility for p in poses for lm in p.landmarks.values()]
                mean_vis = sum(vals) / len(vals) if vals else 0.0
            if mean_vis < 0.2:
                poses = SyntheticPoseEstimator(stroke=stroke, handedness=handedness).estimate()

        features = compute_features(poses, handedness=handedness)

        if clip_too_long(features):
            issues = [
                QualityIssue(
                    code="clip_too_long",
                    message="This clip is longer than 45 seconds.",
                    tip="Upload a shorter basket (under 45s) with a few clear hits of the same stroke.",
                )
            ]
            return grade_analysis(stroke, [], features, issues), None, None

        hits = detect_hits(features)
        if len(hits) < 2:
            result, overlay = self._analyze_single(
                video_path=video_path,
                poses=poses,
                features=features,
                stroke=stroke,
                handedness=handedness,
                overlay_path=overlay_path,
            )
            return result, overlay, None

        scored: list[ScoredHit] = [
            ScoredHit(index=i, window=hit, result=score_hit_window(poses, features, hit, stroke, handedness))
            for i, hit in enumerate(hits)
        ]
        best = pick_best(scored)
        candidates = [
            MultiHitCandidate(
                index=s.index,
                score=s.result.overall_score if s.result.status == "ok" else None,
                status=s.result.status,  # type: ignore[arg-type]
                kept=best is not None and s.index == best.index,
            )
            for s in scored
        ]

        if best is None:
            issues = [
                QualityIssue(
                    code="no_usable_hits",
                    message=f"Detected {len(hits)} hits but none were filmable enough to grade.",
                    tip="Film from the side in good light; keep the full body in frame for each swing.",
                )
            ]
            result = grade_analysis(stroke, [], features, issues)
            result.multi_hit = MultiHitInfo(
                enabled=True,
                detected=len(hits),
                candidates=candidates,
            )
            return result, None, None

        kept = best.result
        kept.multi_hit = MultiHitInfo(
            enabled=True,
            detected=len(hits),
            kept_index=best.index,
            kept_score=kept.overall_score,
            kept_window_ms=[best.window.start_ms, best.window.end_ms],
            candidates=candidates,
        )

        sliced_poses = slice_poses(poses, best.window)
        sliced_feats = slice_features(features, best.window)
        phase_windows = segment_phases(sliced_feats)

        out = overlay_path or _temp_mp4()
        source_for_overlay: Path | None = None
        kept_clip: Path | None = None

        if video_path.exists():
            try:
                kept_clip = clip_path or _temp_mp4()
                kept_clip = cut_video_window(
                    video_path, kept_clip, best.window.start_ms, best.window.end_ms
                )
                source_for_overlay = kept_clip
            except Exception:
                kept_clip = None
                source_for_overlay = None

        out = render_overlay(
            source_video=source_for_overlay,
            poses=sliced_poses,
            features=sliced_feats,
            windows=phase_windows,
            output_path=out,
            handedness=handedness,
        )
        return kept, out, kept_clip

    def _analyze_single(
        self,
        video_path: Path,
        poses,
        features,
        stroke: Stroke,
        handedness: Handedness,
        overlay_path: Path | None,
    ) -> tuple[AnalysisResult, Path | None]:
        issues = assess_quality(features)
        if issues:
            return grade_analysis(stroke, [], features, issues), None

        windows = segment_phases(features)
        phase_scores = score_phases(features, windows, load_rubric(stroke))
        result = grade_analysis(stroke, phase_scores, features, [])

        out = overlay_path or _temp_mp4()
        out = render_overlay(
            source_video=video_path if video_path.exists() else None,
            poses=poses,
            features=features,
            windows=windows,
            output_path=out,
            handedness=handedness,
        )
        return result, out


def _temp_mp4() -> Path:
    tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    path = Path(tmp.name)
    tmp.close()
    return path
