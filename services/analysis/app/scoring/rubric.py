from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.kinematics.features import FrameFeatures
from app.models import PhaseName, PhaseScore, PhaseWindow, Stroke

_RUBRIC_DIR = Path(__file__).resolve().parents[2] / "rubrics"


def load_rubric(stroke: Stroke) -> dict[str, Any]:
    path = _RUBRIC_DIR / f"{stroke.value}.json"
    if not path.exists():
        path = _RUBRIC_DIR / "forehand.json"
    with path.open() as f:
        return json.load(f)


def score_phases(
    features: list[FrameFeatures],
    windows: list[PhaseWindow],
    rubric: dict[str, Any],
) -> list[PhaseScore]:
    phase_rules: dict[str, Any] = rubric.get("phases", {})
    scores: list[PhaseScore] = []

    for window in windows:
        rules = phase_rules.get(window.name.value, {})
        slice_feats = [f for f in features if window.start_frame <= f.frame_index <= window.end_frame]
        if not slice_feats:
            slice_feats = features[window.start_frame : window.end_frame + 1] or features[:1]

        score, observations, good = _score_window(window.name, slice_feats, features, rules)
        feedback = rules.get("feedback_good" if good else "feedback_bad", "Keep practicing this phase.")
        ideal = rules.get("ideal", "")
        scores.append(
            PhaseScore(
                name=window.name,
                score=round(score, 1),
                feedback=feedback,
                ideal_comparison=ideal,
                observations=observations,
            )
        )
    return scores


def _score_window(
    name: PhaseName,
    slice_feats: list[FrameFeatures],
    all_feats: list[FrameFeatures],
    rules: dict[str, Any],
) -> tuple[float, list[str], bool]:
    observations: list[str] = []
    checks: list[float] = []

    avg_balance = sum(f.balance for f in slice_feats) / len(slice_feats)
    avg_sep = sum(f.hip_shoulder_separation for f in slice_feats) / len(slice_feats)
    min_hand_x = min(f.hand_x for f in slice_feats)
    max_hand_y = max(f.hand_y for f in slice_feats)
    min_hand_y = min(f.hand_y for f in slice_feats)
    peak_speed = max(f.hand_speed for f in all_feats) if all_feats else 0.0
    contact_feat = slice_feats[len(slice_feats) // 2]

    if "balance_min" in rules:
        ok = avg_balance >= rules["balance_min"]
        checks.append(100.0 if ok else max(40.0, avg_balance / rules["balance_min"] * 100))
        observations.append(f"balance={avg_balance:.2f}")

    if "hip_shoulder_sep_min" in rules:
        ok = avg_sep >= rules["hip_shoulder_sep_min"]
        checks.append(100.0 if ok else max(35.0, avg_sep / rules["hip_shoulder_sep_min"] * 100))
        observations.append(f"hip_shoulder_sep={avg_sep:.2f}")

    if "hand_x_max" in rules:
        # Smaller hand_x = deeper takeback on a righty side view.
        ok = min_hand_x <= rules["hand_x_max"]
        if ok:
            checks.append(100.0)
        else:
            overshoot = min_hand_x - rules["hand_x_max"]
            checks.append(max(30.0, 100.0 - overshoot * 400))
        observations.append(f"min_hand_x={min_hand_x:.2f}")

    if "peak_speed_min" in rules:
        ok = peak_speed >= rules["peak_speed_min"]
        checks.append(100.0 if ok else max(35.0, peak_speed / rules["peak_speed_min"] * 100))
        observations.append(f"peak_speed={peak_speed:.2f}")

    if "hand_y_min" in rules or "hand_y_max" in rules:
        y = contact_feat.hand_y if name == PhaseName.CONTACT else (min_hand_y + max_hand_y) / 2
        lo = rules.get("hand_y_min", 0.0)
        hi = rules.get("hand_y_max", 1.0)
        if lo <= y <= hi:
            checks.append(100.0)
        else:
            dist = lo - y if y < lo else y - hi
            checks.append(max(30.0, 100.0 - dist * 300))
        observations.append(f"hand_y={y:.2f}")

    if name == PhaseName.FINISH and "hand_y_max" in rules:
        # Already handled above via hand_y_max; ensure finish uses min hand_y (highest point).
        pass

    if name == PhaseName.RACQUET_DROP:
        # Drop quality: hand should be lower than at takeback start.
        ok = max_hand_y >= 0.50
        checks.append(95.0 if ok else 55.0)
        observations.append(f"drop_hand_y={max_hand_y:.2f}")

    if name == PhaseName.EXTENSION:
        # Hand should move forward (increasing x) through extension.
        dx = slice_feats[-1].hand_x - slice_feats[0].hand_x
        ok = dx > 0.02
        checks.append(95.0 if ok else 50.0)
        observations.append(f"extension_dx={dx:.2f}")

    if not checks:
        checks.append(75.0)

    score = sum(checks) / len(checks)
    good = score >= 75.0
    return score, observations, good
