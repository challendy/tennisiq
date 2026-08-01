"""Score reference strokes to check the rubric separates good from bad.

Prints the per-phase and overall score for each synthetic variant. A rubric
is doing its job when the ideal column is high, each degradation drops the
phase it targets, and the overall spread is wide enough to be meaningful.

    python -m scripts.score_variants --stroke forehand
"""

from __future__ import annotations

import argparse

from app.kinematics.features import compute_features
from app.models import PHASE_ORDER, Handedness, Stroke
from app.pose.estimator import SyntheticPoseEstimator
from app.scoring.grading import assess_quality, grade_analysis
from app.scoring.rubric import load_rubric, score_phases
from app.segmentation.phases import segment_phases
from scripts.calibrate import VARIANTS


def analyze(stroke: Stroke, **kwargs):
    poses = SyntheticPoseEstimator(stroke=stroke, frame_count=60, **kwargs).estimate()
    features = compute_features(poses, Handedness.RIGHT)
    windows = segment_phases(features)
    phases = score_phases(features, windows, load_rubric(stroke))
    return grade_analysis(stroke, phases, features, assess_quality(features))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stroke", default="forehand", choices=[s.value for s in Stroke])
    args = parser.parse_args()
    stroke = Stroke(args.stroke)

    results = {name: analyze(stroke, **kwargs) for name, kwargs in VARIANTS.items()}

    header = f"{'phase':<16}{'wt':>5}" + "".join(f"{v:>18}" for v in VARIANTS)
    print(f"\n=== {stroke.value} ===")
    print(header)
    print("-" * len(header))

    for phase in PHASE_ORDER:
        ideal_phase = next(p for p in results["ideal"].phases if p.name == phase)
        row = f"{phase.value:<16}{ideal_phase.weight:>5.2f}"
        for variant in VARIANTS:
            score = next(p.score for p in results[variant].phases if p.name == phase)
            row += f"{score:>18.1f}"
        print(row)

    print("-" * len(header))
    print(f"{'OVERALL':<16}{'':>5}" + "".join(f"{results[v].overall_score:>18.1f}" for v in VARIANTS))
    print(f"{'grade':<16}{'':>5}" + "".join(f"{results[v].grade:>18}" for v in VARIANTS))
    print()
    for variant in VARIANTS:
        print(f"{variant:>16}: {results[variant].top_fix}")


if __name__ == "__main__":
    main()
