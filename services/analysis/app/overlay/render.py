from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from app.kinematics.features import FrameFeatures
from app.models import FramePose, Handedness, PhaseWindow

_SKELETON = [
    ("left_shoulder", "right_shoulder"),
    ("left_shoulder", "left_elbow"),
    ("left_elbow", "left_wrist"),
    ("right_shoulder", "right_elbow"),
    ("right_elbow", "right_wrist"),
    ("left_shoulder", "left_hip"),
    ("right_shoulder", "right_hip"),
    ("left_hip", "right_hip"),
    ("left_hip", "left_knee"),
    ("left_knee", "left_ankle"),
    ("right_hip", "right_knee"),
    ("right_knee", "right_ankle"),
]


def render_overlay(
    source_video: Path | None,
    poses: list[FramePose],
    features: list[FrameFeatures],
    windows: list[PhaseWindow],
    output_path: Path,
    handedness: Handedness = Handedness.RIGHT,
    size: tuple[int, int] = (640, 480),
    fps: float = 30.0,
) -> Path:
    """Draw skeleton, swing path, contact marker, angles, CoG, balance bar."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    width, height = size
    reader = None
    if source_video is not None and source_video.exists():
        reader = cv2.VideoCapture(str(source_video))
        if reader.isOpened():
            width = int(reader.get(cv2.CAP_PROP_FRAME_WIDTH)) or width
            height = int(reader.get(cv2.CAP_PROP_FRAME_HEIGHT)) or height
            fps = reader.get(cv2.CAP_PROP_FPS) or fps
        else:
            reader = None

    writer, output_path = _open_writer(output_path, fps, width, height)

    contact_frame = next((w.contact_frame for w in windows if w.contact_frame is not None), None)
    dominant = "right" if handedness == Handedness.RIGHT else "left"
    trail: list[tuple[int, int]] = []

    n = max(len(poses), 1)
    for i in range(n):
        if reader is not None:
            ok, frame = reader.read()
            if not ok:
                frame = np.zeros((height, width, 3), dtype=np.uint8)
                frame[:] = (25, 70, 35)
        else:
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            frame[:] = (25, 70, 35)

        pose = poses[i] if i < len(poses) else poses[-1]
        feat = features[i] if i < len(features) else features[-1]
        phase = _phase_at(windows, i)

        _draw_skeleton(frame, pose)
        wrist = pose.landmarks.get(f"{dominant}_wrist")
        if wrist and wrist.visibility > 0.2:
            pt = (int(wrist.x * width), int(wrist.y * height))
            trail.append(pt)
            if len(trail) > 1:
                for a, b in zip(trail[:-1], trail[1:]):
                    cv2.line(frame, a, b, (0, 220, 255), 2)
            cv2.circle(frame, pt, 5, (0, 220, 255), -1)

        if contact_frame is not None and i == contact_frame and wrist:
            cv2.circle(frame, (int(wrist.x * width), int(wrist.y * height)), 14, (0, 0, 255), 2)
            cv2.putText(frame, "CONTACT (est.)", (20, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        # CoG + balance bar
        cog = (int(feat.cog_x * width), int(feat.cog_y * height))
        cv2.drawMarker(frame, cog, (255, 200, 0), markerType=cv2.MARKER_CROSS, markerSize=12, thickness=2)
        bar_w = int(120 * feat.balance)
        cv2.rectangle(frame, (20, 20), (140, 36), (60, 60, 60), -1)
        cv2.rectangle(frame, (20, 20), (20 + bar_w, 36), (80, 220, 80), -1)
        cv2.putText(frame, "balance", (150, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (230, 230, 230), 1)

        # Shoulder / hip lines for separation cue
        ls = pose.landmarks.get("left_shoulder")
        rs = pose.landmarks.get("right_shoulder")
        lh = pose.landmarks.get("left_hip")
        rh = pose.landmarks.get("right_hip")
        if ls and rs:
            cv2.line(
                frame,
                (int(ls.x * width), int(ls.y * height)),
                (int(rs.x * width), int(rs.y * height)),
                (255, 120, 80),
                2,
            )
        if lh and rh:
            cv2.line(
                frame,
                (int(lh.x * width), int(lh.y * height)),
                (int(rh.x * width), int(rh.y * height)),
                (80, 180, 255),
                2,
            )

        label = f"{phase}  elbow={feat.elbow_angle:.0f}  sep={feat.hip_shoulder_separation:.2f}"
        cv2.putText(frame, label, (20, height - 48), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
        writer.write(frame)

    writer.release()
    if reader is not None:
        reader.release()
    if not output_path.exists() or output_path.stat().st_size < 500:
        raise RuntimeError(f"Overlay render produced empty file: {output_path}")
    return output_path


def _open_writer(path: Path, fps: float, width: int, height: int):
    """Try codecs until one actually opens. Prefer browser-friendly mp4."""
    candidates = [
        (path.with_suffix(".mp4"), "avc1"),
        (path.with_suffix(".mp4"), "mp4v"),
        (path.with_suffix(".avi"), "MJPG"),
    ]
    for candidate, codec in candidates:
        # macOS AVFoundation refuses to open a writer when the destination already
        # exists, so callers passing a pre-created temp file would silently fall
        # through to the non-browser-friendly AVI codec.
        candidate.unlink(missing_ok=True)
        fourcc = cv2.VideoWriter_fourcc(*codec)
        writer = cv2.VideoWriter(str(candidate), fourcc, fps, (width, height))
        if writer.isOpened():
            return writer, candidate
        writer.release()
    raise RuntimeError("No OpenCV VideoWriter backend available")


def _draw_skeleton(frame, pose: FramePose) -> None:
    h, w = frame.shape[:2]
    pts = {}
    for name, lm in pose.landmarks.items():
        if lm.visibility < 0.2:
            continue
        pts[name] = (int(lm.x * w), int(lm.y * h))
        cv2.circle(frame, pts[name], 3, (240, 240, 240), -1)
    for a, b in _SKELETON:
        if a in pts and b in pts:
            cv2.line(frame, pts[a], pts[b], (200, 200, 200), 2)


def _phase_at(windows: list[PhaseWindow], frame_index: int) -> str:
    for w in windows:
        if w.start_frame <= frame_index <= w.end_frame:
            return w.name.value
    return ""
