from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from app.kinematics.features import FrameFeatures
from app.models import PHASE_ORDER, PhaseScore, PhaseWindow, Stroke

_RUBRIC_DIR = Path(__file__).resolve().parents[2] / "rubrics"

_DEFAULT_FLOOR = 30.0


@dataclass(frozen=True)
class _MetricContext:
    window: list[FrameFeatures]
    clip: list[FrameFeatures]
    contact: FrameFeatures


def _mean(values: Iterable[float]) -> float:
    items = list(values)
    return sum(items) / len(items) if items else 0.0


# Every quantity a rubric may reference. Values are body-relative wherever a
# distance or speed is involved: `_rel` metrics are expressed in torso lengths
# (or torso lengths per second), measured from the hip midpoint, with positive
# x pointing the way the player swings. That makes a threshold mean the same
# thing regardless of camera distance, lens, player height, or handedness.
_METRICS: dict[str, Callable[[_MetricContext], float]] = {
    "mean_balance": lambda c: _mean(f.balance for f in c.window),
    "min_balance": lambda c: min(f.balance for f in c.window),
    "mean_hip_shoulder_sep": lambda c: _mean(f.hip_shoulder_separation for f in c.window),
    "max_hip_shoulder_sep": lambda c: max(f.hip_shoulder_separation for f in c.window),
    "min_hand_x_rel": lambda c: min(f.hand_x_rel for f in c.window),
    "max_hand_x_rel": lambda c: max(f.hand_x_rel for f in c.window),
    "hand_x_rel_delta": lambda c: c.window[-1].hand_x_rel - c.window[0].hand_x_rel,
    "min_hand_y_rel": lambda c: min(f.hand_y_rel for f in c.window),
    "max_hand_y_rel": lambda c: max(f.hand_y_rel for f in c.window),
    "mean_hand_y_rel": lambda c: _mean(f.hand_y_rel for f in c.window),
    "hand_y_rel_delta": lambda c: c.window[-1].hand_y_rel - c.window[0].hand_y_rel,
    "contact_hand_x_rel": lambda c: c.contact.hand_x_rel,
    "contact_hand_y_rel": lambda c: c.contact.hand_y_rel,
    "peak_hand_speed_rel": lambda c: max(f.hand_speed_rel for f in c.clip),
    "window_peak_hand_speed_rel": lambda c: max(f.hand_speed_rel for f in c.window),
    "mean_elbow_angle": lambda c: _mean(f.elbow_angle for f in c.window),
    "min_elbow_angle": lambda c: min(f.elbow_angle for f in c.window),
    "max_elbow_angle": lambda c: max(f.elbow_angle for f in c.window),
}


class RubricError(ValueError):
    """A rubric file is malformed. Raised at load so typos fail loudly."""


def load_rubric(stroke: Stroke) -> dict[str, Any]:
    path = _RUBRIC_DIR / f"{stroke.value}.json"
    if not path.exists():
        path = _RUBRIC_DIR / "forehand.json"
    with path.open() as f:
        rubric = json.load(f)
    validate_rubric(rubric, source=path.name)
    return rubric


def validate_rubric(rubric: dict[str, Any], source: str = "<rubric>") -> None:
    """Reject a rubric that would silently produce meaningless scores.

    The failure this guards against is a phase with no measurable check:
    it looks like analysis in the UI while the number never moves.
    """
    phases = rubric.get("phases")
    if not isinstance(phases, dict):
        raise RubricError(f"{source}: missing 'phases' object")

    for phase in PHASE_ORDER:
        rules = phases.get(phase.value)
        if rules is None:
            raise RubricError(f"{source}: no rules for phase '{phase.value}'")

        checks = rules.get("checks")
        if not isinstance(checks, list) or not checks:
            raise RubricError(
                f"{source}: phase '{phase.value}' has no checks — every phase "
                "must be backed by at least one measurement"
            )

        for i, check in enumerate(checks):
            where = f"{source}: phase '{phase.value}' check {i}"
            metric = check.get("metric")
            if metric not in _METRICS:
                raise RubricError(f"{where}: unknown metric {metric!r}")
            if "ideal_min" not in check and "ideal_max" not in check:
                raise RubricError(f"{where}: needs 'ideal_min' and/or 'ideal_max'")
            tolerance = check.get("tolerance")
            if not isinstance(tolerance, (int, float)) or tolerance <= 0:
                raise RubricError(f"{where}: 'tolerance' must be a positive number")


def score_phases(
    features: list[FrameFeatures],
    windows: list[PhaseWindow],
    rubric: dict[str, Any],
) -> list[PhaseScore]:
    phase_rules: dict[str, Any] = rubric.get("phases", {})
    contact_frame = next((w.contact_frame for w in windows if w.contact_frame is not None), None)
    contact_feat = _feature_at(features, contact_frame)
    scores: list[PhaseScore] = []

    for window in windows:
        rules = phase_rules.get(window.name.value, {})
        slice_feats = [f for f in features if window.start_frame <= f.frame_index <= window.end_frame]
        if not slice_feats:
            slice_feats = features[window.start_frame : window.end_frame + 1] or features[:1]

        context = _MetricContext(window=slice_feats, clip=features, contact=contact_feat)
        score, observations = _score_window(context, rules.get("checks", []))
        good = score >= float(rules.get("good_at", 75.0))
        scores.append(
            PhaseScore(
                name=window.name,
                score=round(score, 1),
                weight=float(rules.get("weight", 1.0)),
                feedback=rules.get("feedback_good" if good else "feedback_bad", ""),
                ideal_comparison=rules.get("ideal", ""),
                observations=observations,
            )
        )
    return scores


def _score_window(
    context: _MetricContext,
    checks: list[dict[str, Any]],
) -> tuple[float, list[str]]:
    observations: list[str] = []
    total = 0.0
    total_weight = 0.0

    for check in checks:
        value = _METRICS[check["metric"]](context)
        score = _score_check(value, check)
        weight = float(check.get("weight", 1.0))
        total += score * weight
        total_weight += weight
        observations.append(_describe(check, value))

    if total_weight <= 0:
        return 0.0, observations
    return total / total_weight, observations


def _score_check(value: float, check: dict[str, Any]) -> float:
    """Full marks inside the target band, easing to a floor outside it.

    The bands describe good technique rather than merely acceptable
    technique, which is what leaves the scale room to separate a solid
    stroke from an excellent one.
    """
    low = check.get("ideal_min")
    high = check.get("ideal_max")

    if low is not None and value < low:
        distance = low - value
    elif high is not None and value > high:
        distance = value - high
    else:
        return 100.0

    floor = float(check.get("floor", _DEFAULT_FLOOR))
    tolerance = float(check["tolerance"])
    shortfall = min(1.0, distance / tolerance)
    return floor + (100.0 - floor) * (1.0 - shortfall)


def _describe(check: dict[str, Any], value: float) -> str:
    label = check.get("label", check["metric"])
    low = check.get("ideal_min")
    high = check.get("ideal_max")
    if low is not None and high is not None:
        target = f"target {low:g}–{high:g}"
    elif low is not None:
        target = f"target ≥{low:g}"
    else:
        target = f"target ≤{high:g}"
    return f"{label}={value:.2f} ({target})"


def _feature_at(features: list[FrameFeatures], frame_index: int | None) -> FrameFeatures:
    if frame_index is not None:
        for f in features:
            if f.frame_index == frame_index:
                return f
    return features[len(features) // 2]
