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

    raw: list[FrameFeatures] = []
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
        # Balance: 1 when CoG sits over the base of support.
        balance = max(0.0, 1.0 - abs(cog_x - ankle_mid_x) * 4.0)

        vis = [lm.visibility for lm in pose.landmarks.values()]
        mean_vis = sum(vis) / len(vis) if vis else 0.0

        speed = 0.0
        if prev_hand is not None and prev_t is not None:
            dt = (pose.timestamp_ms - prev_t) / 1000.0
            if dt > 0:
                dist = math.hypot(wrist[0] - prev_hand[0], wrist[1] - prev_hand[1])
                speed = dist / dt

        raw.append(
            FrameFeatures(
                frame_index=pose.frame_index,
                timestamp_ms=pose.timestamp_ms,
                elbow_angle=elbow_angle,
                shoulder_angle=shoulder_angle,
                hip_shoulder_separation=hip_shoulder_sep,
                cog_x=cog_x,
                cog_y=cog_y,
                balance=balance,
                hand_x=wrist[0],
                hand_y=wrist[1],
                hand_speed=speed,
                mean_visibility=mean_vis,
            )
        )
        prev_hand = wrist
        prev_t = pose.timestamp_ms

    return raw


def hand_speed_series(features: list[FrameFeatures]) -> list[float]:
    return [f.hand_speed for f in features]
