"""Dump body-relative metrics for reference strokes.

Run this when authoring or retuning a rubric: it prints, per phase, the value
of every metric the rubric engine can reference, for an ideal synthetic stroke
and for each degradation the synthetic estimator can produce. Bands should sit
around the ideal column and clearly separate the degraded ones.

    python -m scripts.calibrate            # forehand
    python -m scripts.calibrate --stroke serve
"""

from __future__ import annotations

import argparse

from app.kinematics.features import compute_features
from app.models import Handedness, Stroke
from app.pose.estimator import SyntheticPoseEstimator
from app.scoring.rubric import _METRICS, _MetricContext, _feature_at
from app.segmentation.phases import segment_phases

VARIANTS: dict[str, dict] = {
    "ideal": {},
    "short_backswing": {"short_backswing": True},
    "low_contact": {"contact_height": 0.62},
    "high_contact": {"contact_height": 0.34},
    "low_finish": {"finish_over_shoulder": False},
}


def metrics_for(stroke: Stroke, **kwargs) -> dict[tuple[str, str], float]:
    poses = SyntheticPoseEstimator(stroke=stroke, frame_count=60, **kwargs).estimate()
    features = compute_features(poses, Handedness.RIGHT)
    windows = segment_phases(features)
    contact_frame = next((w.contact_frame for w in windows if w.contact_frame is not None), None)
    contact = _feature_at(features, contact_frame)

    out: dict[tuple[str, str], float] = {}
    for window in windows:
        slice_feats = [
            f for f in features if window.start_frame <= f.frame_index <= window.end_frame
        ] or features[:1]
        context = _MetricContext(window=slice_feats, clip=features, contact=contact)
        for name, fn in _METRICS.items():
            out[(window.name.value, name)] = fn(context)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stroke", default="forehand", choices=[s.value for s in Stroke])
    args = parser.parse_args()
    stroke = Stroke(args.stroke)

    tables = {name: metrics_for(stroke, **kwargs) for name, kwargs in VARIANTS.items()}
    keys = sorted(tables["ideal"].keys())

    header = f"{'phase':<14}{'metric':<28}" + "".join(f"{v:>18}" for v in VARIANTS)
    print(f"\n=== {stroke.value} ===")
    print(header)
    print("-" * len(header))

    last_phase = None
    for phase, metric in keys:
        if phase != last_phase:
            print()
            last_phase = phase
        row = f"{phase:<14}{metric:<28}"
        for variant in VARIANTS:
            row += f"{tables[variant][(phase, metric)]:>18.3f}"
        print(row)


if __name__ == "__main__":
    main()
