from __future__ import annotations

from app.kinematics.features import FrameFeatures
from app.models import AnalysisResult, PhaseScore, QualityIssue, Stroke


def score_to_grade(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def assess_quality(features: list[FrameFeatures], min_frames: int = 24) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    if len(features) < min_frames:
        issues.append(
            QualityIssue(
                code="too_few_frames",
                message=f"Only {len(features)} frames detected (need ~{min_frames}+).",
                tip="Film at 30fps or higher and capture the full stroke from ready to finish.",
            )
        )
    if features:
        mean_vis = sum(f.mean_visibility for f in features) / len(features)
        if mean_vis < 0.45:
            issues.append(
                QualityIssue(
                    code="low_visibility",
                    message="Pose landmarks are unreliable across the clip.",
                    tip="Film from the side in good light; keep the full body in frame.",
                )
            )
        speeds = [f.hand_speed for f in features]
        if max(speeds) < 0.3:
            issues.append(
                QualityIssue(
                    code="no_stroke_motion",
                    message="No clear stroke motion detected.",
                    tip="Film a single full stroke; avoid walking to the ball or cutting mid-swing.",
                )
            )
    return issues


def grade_analysis(
    stroke: Stroke,
    phase_scores: list[PhaseScore],
    features: list[FrameFeatures],
    quality_issues: list[QualityIssue],
) -> AnalysisResult:
    if quality_issues:
        return AnalysisResult(
            stroke=stroke,
            status="insufficient_quality",
            overall_score=0.0,
            grade="—",
            confidence=0.0,
            top_fix="Re-film with the tips below, then try again.",
            phases=[],
            quality_issues=quality_issues,
            frame_count=len(features),
            fps=_infer_fps(features),
        )

    overall = sum(p.score for p in phase_scores) / len(phase_scores)
    mean_vis = sum(f.mean_visibility for f in features) / len(features)
    confidence = max(0.35, min(0.98, 0.55 * mean_vis + 0.45 * (1.0 if len(features) >= 40 else len(features) / 40)))

    ranked = sorted(phase_scores, key=lambda p: p.score)
    strengths = [p.feedback for p in ranked[-2:][::-1] if p.score >= 75]
    weaknesses = [p.feedback for p in ranked[:2] if p.score < 80]
    top = ranked[0]
    top_fix = f"Focus on {top.name.value.replace('_', ' ')}: {top.feedback}"

    peak_speed = max(f.hand_speed for f in features) if features else 0.0
    contact = next((p for p in phase_scores if p.name.value == "contact"), None)
    metrics = {
        "peak_hand_speed": round(peak_speed, 3),
        "mean_balance": round(sum(f.balance for f in features) / len(features), 3),
        "mean_visibility": round(mean_vis, 3),
        "contact_score": contact.score if contact else 0.0,
        "weakest_phase_score": ranked[0].score,
    }

    return AnalysisResult(
        stroke=stroke,
        status="ok",
        overall_score=round(overall, 1),
        grade=score_to_grade(overall),
        confidence=round(confidence, 3),
        strengths=strengths or ["Solid fundamentals to build on."],
        weaknesses=weaknesses or ["Keep reinforcing consistency across phases."],
        top_fix=top_fix,
        phases=phase_scores,
        metrics=metrics,
        quality_issues=[],
        contact_estimated=True,
        frame_count=len(features),
        fps=_infer_fps(features),
    )


def _infer_fps(features: list[FrameFeatures]) -> float:
    if len(features) < 2:
        return 0.0
    dt = (features[-1].timestamp_ms - features[0].timestamp_ms) / 1000.0
    if dt <= 0:
        return 0.0
    return round((len(features) - 1) / dt, 2)
