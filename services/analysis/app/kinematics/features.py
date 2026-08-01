from __future__ import annotations

import math
from dataclasses import dataclass

from app.models import FramePose, Handedness


@dataclass(frozen=True)
class FrameFeatures:
    frame_index: int
    timestamp_ms: float
    elbow_angle: float
    shoulder_angle: float
    hip_shoulder_separation: float
    cog_x: float
    cog_y: float
    balance: float
    hand_x: float
    hand_y: float
    hand_speed: float
    mean_visibility: float
    # Body-relative measures. These divide out camera distance, lens, and
    # player size, so rubric thresholds transfer between clips. Frame-relative
    # fields above stay for rendering, which works in image space.
    torso_length: float = 0.0
    hand_x_rel: float = 0.0
    hand_y_rel: float = 0.0
    hand_speed_rel: float = 0.0


# A person framed head-to-toe has a torso spanning roughly 0.20 of frame
# height. Anything below this means the pose collapsed, and dividing by it
# would turn noise into enormous relative values.
_MIN_TORSO = 0.05


def _angle(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    """Interior angle ABC in degrees."""
    ba = (a[0] - b[0], a[1] - b[1])
    bc = (c[0] - b[0], c[1] - b[1])
    dot = ba[0] * bc[0] + ba[1] * bc[1]
    norm_ba = math.hypot(*ba)
    norm_bc = math.hypot(*bc)
    if norm_ba < 1e-9 or norm_bc < 1e-9:
        return 0.0
    cos = max(-1.0, min(1.0, dot / (norm_ba * norm_bc)))
    return math.degrees(math.acos(cos))


def _xy(pose: FramePose, name: str) -> tuple[float, float]:
    lm = pose.landmarks[name]
    return (lm.x, lm.y)


def compute_features(poses: list[FramePose], handedness: Handedness = Handedness.RIGHT) -> list[FrameFeatures]:
    if not poses:
        return []

    dominant = "right" if handedness == Handedness.RIGHT else "left"
    off = "left" if dominant == "right" else "right"

    partial: list[dict] = []
    prev_hand: tuple[float, float] | None = None
    prev_t: float | None = None

    for pose in poses:
        shoulder = _xy(pose, f"{dominant}_shoulder")
        elbow = _xy(pose, f"{dominant}_elbow")
        wrist = _xy(pose, f"{dominant}_wrist")
        hip = _xy(pose, f"{dominant}_hip")
        off_shoulder = _xy(pose, f"{off}_shoulder")
        off_hip = _xy(pose, f"{off}_hip")

        elbow_angle = _angle(shoulder, elbow, wrist)
        shoulder_angle = _angle(hip, shoulder, elbow)

        # Approximate transverse-plane separation using horizontal offsets.
        shoulder_mid_x = (shoulder[0] + off_shoulder[0]) / 2
        hip_mid_x = (hip[0] + off_hip[0]) / 2
        shoulder_width = abs(shoulder[0] - off_shoulder[0]) + 1e-6
        hip_shoulder_sep = abs((shoulder[0] - off_shoulder[0]) - (hip[0] - off_hip[0])) / shoulder_width

        # CoG ~ average of hips + shoulders.
        cog_x = (shoulder[0] + off_shoulder[0] + hip[0] + off_hip[0]) / 4
        cog_y = (shoulder[1] + off_shoulder[1] + hip[1] + off_hip[1]) / 4
        ankle_mid_x = (
            pose.landmarks[f"{dominant}_ankle"].x + pose.landmarks[f"{off}_ankle"].x
        ) / 2
        shoulder_mid = ((shoulder[0] + off_shoulder[0]) / 2, (shoulder[1] + off_shoulder[1]) / 2)
        hip_mid = ((hip[0] + off_hip[0]) / 2, (hip[1] + off_hip[1]) / 2)
        torso = max(
            _MIN_TORSO,
            math.hypot(shoulder_mid[0] - hip_mid[0], shoulder_mid[1] - hip_mid[1]),
        )
        # Balance: 1 when CoG sits over the base of support, falling to 0 once
        # it drifts about 1.25 torso lengths off. Measured in torso lengths so
        # it does not change with how much of the frame the player fills.
        balance = max(0.0, 1.0 - (abs(cog_x - ankle_mid_x) / torso) * 0.8)

        vis = [lm.visibility for lm in pose.landmarks.values()]
        mean_vis = sum(vis) / len(vis) if vis else 0.0

        speed = 0.0
        if prev_hand is not None and prev_t is not None:
            dt = (pose.timestamp_ms - prev_t) / 1000.0
            if dt > 0:
                dist = math.hypot(wrist[0] - prev_hand[0], wrist[1] - prev_hand[1])
                speed = dist / dt

        partial.append(
            {
                "frame_index": pose.frame_index,
                "timestamp_ms": pose.timestamp_ms,
                "elbow_angle": elbow_angle,
                "shoulder_angle": shoulder_angle,
                "hip_shoulder_separation": hip_shoulder_sep,
                "cog_x": cog_x,
                "cog_y": cog_y,
                "balance": balance,
                "hand_x": wrist[0],
                "hand_y": wrist[1],
                "hand_speed": speed,
                "mean_visibility": mean_vis,
                "torso_length": torso,
                "hip_mid_x": hip_mid[0],
                "hip_mid_y": hip_mid[1],
            }
        )
        prev_hand = wrist
        prev_t = pose.timestamp_ms

    sign = _swing_direction(
        [p["hand_x"] for p in partial],
        [p["hand_speed"] for p in partial],
    )

    return [
        FrameFeatures(
            frame_index=p["frame_index"],
            timestamp_ms=p["timestamp_ms"],
            elbow_angle=p["elbow_angle"],
            shoulder_angle=p["shoulder_angle"],
            hip_shoulder_separation=p["hip_shoulder_separation"],
            cog_x=p["cog_x"],
            cog_y=p["cog_y"],
            balance=p["balance"],
            hand_x=p["hand_x"],
            hand_y=p["hand_y"],
            hand_speed=p["hand_speed"],
            mean_visibility=p["mean_visibility"],
            torso_length=p["torso_length"],
            hand_x_rel=sign * (p["hand_x"] - p["hip_mid_x"]) / p["torso_length"],
            hand_y_rel=(p["hip_mid_y"] - p["hand_y"]) / p["torso_length"],
            hand_speed_rel=p["hand_speed"] / p["torso_length"],
        )
        for p in partial
    ]


def _swing_direction(hand_xs: list[float], speeds: list[float]) -> float:
    """Which way across the frame the player swings, as +1 or -1.

    Derived from where the hand travels during the fastest frames, so a
    left-hander or a clip shot from the opposite sideline is normalised
    instead of being scored against inverted expectations.
    """
    if len(hand_xs) < 3:
        return 1.0
    indices = sorted(range(1, len(hand_xs)), key=lambda i: speeds[i], reverse=True)
    fastest = indices[: max(1, len(indices) // 5)]
    displacement = sum(hand_xs[i] - hand_xs[i - 1] for i in fastest)
    return -1.0 if displacement < 0 else 1.0


def hand_speed_series(features: list[FrameFeatures]) -> list[float]:
    return [f.hand_speed for f in features]
