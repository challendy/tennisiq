"""Contracts the rubric layer must hold regardless of how bands are tuned."""

from __future__ import annotations

import copy
import json

import pytest

from app.kinematics.features import compute_features
from app.models import PHASE_ORDER, Handedness, Stroke
from app.pose.estimator import SyntheticPoseEstimator
from app.scoring.rubric import (
    _RUBRIC_DIR,
    RubricError,
    load_rubric,
    score_phases,
    validate_rubric,
)
from app.segmentation.phases import segment_phases


def _phase_scores(stroke: Stroke, **kwargs) -> dict[str, float]:
    poses = SyntheticPoseEstimator(frame_count=60, **kwargs).estimate()
    features = compute_features(poses, Handedness.RIGHT)
    windows = segment_phases(features)
    scores = score_phases(features, windows, load_rubric(stroke))
    return {p.name.value: p.score for p in scores}


@pytest.mark.parametrize("stroke", list(Stroke))
def test_every_shipped_rubric_is_valid(stroke: Stroke):
    load_rubric(stroke)


@pytest.mark.parametrize("stroke", list(Stroke))
def test_every_phase_is_backed_by_a_measurement(stroke: Stroke):
    """The failure this guards: a phase with no checks used to score a
    constant 75 while the UI presented it as analysis."""
    rubric = load_rubric(stroke)
    for phase in PHASE_ORDER:
        checks = rubric["phases"][phase.value]["checks"]
        assert checks, f"{stroke.value}/{phase.value} has no checks"


def test_rubric_with_an_unmeasured_phase_is_rejected():
    rubric = json.loads((_RUBRIC_DIR / "forehand.json").read_text())
    rubric["phases"]["contact"]["checks"] = []
    with pytest.raises(RubricError, match="no checks"):
        validate_rubric(rubric)


def test_rubric_referencing_an_unknown_metric_is_rejected():
    rubric = json.loads((_RUBRIC_DIR / "forehand.json").read_text())
    rubric["phases"]["contact"]["checks"][0]["metric"] = "vibes"
    with pytest.raises(RubricError, match="unknown metric"):
        validate_rubric(rubric)


def test_rubric_missing_a_target_band_is_rejected():
    rubric = json.loads((_RUBRIC_DIR / "forehand.json").read_text())
    check = rubric["phases"]["takeback"]["checks"][0]
    check.pop("ideal_min", None)
    check.pop("ideal_max", None)
    with pytest.raises(RubricError, match="ideal_min"):
        validate_rubric(rubric)


def test_volley_and_forehand_disagree_about_the_racquet_drop():
    """A volley wants the racquet head up; a forehand wants it dropped.

    Scoring both with one hardcoded rule was the original bug: a correct
    volley was penalised and a dropped head rewarded.
    """
    forehand = load_rubric(Stroke.FOREHAND)["phases"]["racquet_drop"]["checks"][0]
    volley = load_rubric(Stroke.VOLLEY)["phases"]["racquet_drop"]["checks"][0]
    assert forehand["metric"] == volley["metric"] == "min_hand_y_rel"
    # Forehand caps how high the hand may stay; volley floors how low it may drop.
    assert "ideal_max" in forehand and "ideal_min" not in forehand
    assert "ideal_min" in volley and "ideal_max" not in volley


def test_forehand_motion_scores_badly_against_the_volley_rubric():
    """Stroke rubrics must actually differ, not just carry different prose."""
    as_forehand = _phase_scores(Stroke.FOREHAND)
    as_volley = _phase_scores(Stroke.VOLLEY)
    assert as_forehand["takeback"] > as_volley["takeback"] + 30
    assert as_forehand["finish"] > as_volley["finish"] + 30


def test_phase_weights_are_positive():
    for stroke in Stroke:
        rubric = load_rubric(stroke)
        for phase in PHASE_ORDER:
            assert rubric["phases"][phase.value].get("weight", 1.0) > 0


def test_validation_rejects_a_non_positive_tolerance():
    rubric = copy.deepcopy(load_rubric(Stroke.FOREHAND))
    rubric["phases"]["finish"]["checks"][0]["tolerance"] = 0
    with pytest.raises(RubricError, match="tolerance"):
        validate_rubric(rubric)
