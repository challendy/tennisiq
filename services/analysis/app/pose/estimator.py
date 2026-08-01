from __future__ import annotations

import math
from pathlib import Path
from typing import Protocol

import cv2
import numpy as np

from app.models import FramePose, Handedness, Landmark, Stroke


LANDMARK_NAMES = (
    "nose",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
)

# MediaPipe Pose landmark indices we care about.
_MP_INDEX = {
    "nose": 0,
    "left_shoulder": 11,
    "right_shoulder": 12,
    "left_elbow": 13,
    "right_elbow": 14,
    "left_wrist": 15,
    "right_wrist": 16,
    "left_hip": 23,
    "right_hip": 24,
    "left_knee": 25,
    "right_knee": 26,
    "left_ankle": 27,
    "right_ankle": 28,
}


class PoseEstimator(Protocol):
    def estimate(self, video_path: Path) -> list[FramePose]:
        """Return per-frame landmarks for a video."""


def _lm(x: float, y: float, z: float = 0.0, visibility: float = 1.0) -> Landmark:
    return Landmark(x=x, y=y, z=z, visibility=visibility)


class SyntheticPoseEstimator:
    """Deterministic pose generator for hermetic tests.

    Produces a right-handed side-view stroke whose hand-speed curve has
    clear phase boundaries. Degradation knobs let tests exercise scoring
    and confidence gating without real video.
    """

    def __init__(
        self,
        stroke: Stroke = Stroke.FOREHAND,
        handedness: Handedness = Handedness.RIGHT,
        frame_count: int = 60,
        fps: float = 30.0,
        visibility: float = 1.0,
        contact_height: float = 0.48,
        finish_over_shoulder: bool = True,
        short_backswing: bool = False,
    ) -> None:
        self.stroke = stroke
        self.handedness = handedness
        self.frame_count = frame_count
        self.fps = fps
        self.visibility = visibility
        self.contact_height = contact_height
        self.finish_over_shoulder = finish_over_shoulder
        self.short_backswing = short_backswing

    def estimate(self, video_path: Path | None = None) -> list[FramePose]:
        del video_path  # unused — synthetic
        frames: list[FramePose] = []
        n = self.frame_count
        dominant = "right" if self.handedness == Handedness.RIGHT else "left"
        off = "left" if dominant == "right" else "right"

        for i in range(n):
            t = i / max(n - 1, 1)
            wrist = self._wrist_path(t)
            shoulder_y = 0.38
            hip_y = 0.58
            # Unit turn: shoulders rotate (z separation grows) early.
            shoulder_sep = 0.05 + 0.08 * _smoothstep(t, 0.08, 0.28)
            hip_sep = 0.04 + 0.05 * _smoothstep(t, 0.05, 0.22)

            elbow = (
                wrist[0] * 0.55 + 0.32,
                wrist[1] * 0.55 + shoulder_y * 0.45,
            )

            landmarks = {
                "nose": _lm(0.50, 0.22, 0.0, self.visibility),
                f"{dominant}_shoulder": _lm(0.52 + shoulder_sep, shoulder_y, 0.02, self.visibility),
                f"{off}_shoulder": _lm(0.48 - shoulder_sep, shoulder_y, -0.02, self.visibility),
                f"{dominant}_elbow": _lm(elbow[0], elbow[1], 0.01, self.visibility),
                f"{off}_elbow": _lm(0.40, 0.45, -0.01, self.visibility),
                f"{dominant}_wrist": _lm(wrist[0], wrist[1], 0.0, self.visibility),
                f"{off}_wrist": _lm(0.38, 0.50, -0.02, self.visibility),
                f"{dominant}_hip": _lm(0.52 + hip_sep, hip_y, 0.01, self.visibility),
                f"{off}_hip": _lm(0.48 - hip_sep, hip_y, -0.01, self.visibility),
                f"{dominant}_knee": _lm(0.54, 0.75, 0.0, self.visibility),
                f"{off}_knee": _lm(0.46, 0.75, 0.0, self.visibility),
                f"{dominant}_ankle": _lm(0.55, 0.92, 0.0, self.visibility),
                f"{off}_ankle": _lm(0.45, 0.92, 0.0, self.visibility),
            }
            # Fill any missing side names for completeness.
            for name in LANDMARK_NAMES:
                landmarks.setdefault(name, _lm(0.5, 0.5, 0.0, self.visibility))

            frames.append(
                FramePose(
                    frame_index=i,
                    timestamp_ms=(i / self.fps) * 1000.0,
                    landmarks=landmarks,
                )
            )
        return frames

    def _wrist_path(self, t: float) -> tuple[float, float]:
        """Piecewise wrist trajectory for a side-view forehand."""
        # Phase anchors (normalized time):
        # ready 0-0.12, unit 0.12-0.22, takeback 0.22-0.38,
        # drop 0.38-0.48, accel 0.48-0.58, contact ~0.58,
        # extension 0.58-0.72, finish 0.72-1.0
        back_x = 0.28 if not self.short_backswing else 0.40
        ready = (0.55, 0.50)
        unit = (0.48, 0.48)
        takeback = (back_x, 0.42)
        drop = (back_x + 0.02, 0.55)
        contact = (0.62, self.contact_height)
        extension = (0.72, 0.40)
        finish = (0.58, 0.22) if self.finish_over_shoulder else (0.70, 0.55)

        keypoints = [
            (0.00, ready),
            (0.12, ready),
            (0.22, unit),
            (0.38, takeback),
            (0.48, drop),
            (0.58, contact),
            (0.72, extension),
            (1.00, finish),
        ]
        return _interp_path(t, keypoints)


def _smoothstep(t: float, edge0: float, edge1: float) -> float:
    if t <= edge0:
        return 0.0
    if t >= edge1:
        return 1.0
    x = (t - edge0) / (edge1 - edge0)
    return x * x * (3 - 2 * x)


def _interp_path(t: float, keypoints: list[tuple[float, tuple[float, float]]]) -> tuple[float, float]:
    t = max(0.0, min(1.0, t))
    for i in range(len(keypoints) - 1):
        t0, p0 = keypoints[i]
        t1, p1 = keypoints[i + 1]
        if t0 <= t <= t1:
            u = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
            # Ease in/out for more natural speed curve.
            u = u * u * (3 - 2 * u)
            return (p0[0] + (p1[0] - p0[0]) * u, p0[1] + (p1[1] - p0[1]) * u)
    return keypoints[-1][1]


class MediaPipePoseEstimator:
    """Runs MediaPipe Pose on every frame of a video file."""

    def __init__(self, model_complexity: int = 1) -> None:
        self.model_complexity = model_complexity

    def estimate(self, video_path: Path) -> list[FramePose]:
        import mediapipe as mp

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frames: list[FramePose] = []
        idx = 0

        with mp.solutions.pose.Pose(
            static_image_mode=False,
            model_complexity=self.model_complexity,
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        ) as pose:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = pose.process(rgb)
                landmarks: dict[str, Landmark] = {}
                if result.pose_landmarks:
                    for name, mp_i in _MP_INDEX.items():
                        lm = result.pose_landmarks.landmark[mp_i]
                        landmarks[name] = Landmark(
                            x=float(lm.x),
                            y=float(lm.y),
                            z=float(lm.z),
                            visibility=float(getattr(lm, "visibility", 1.0) or 0.0),
                        )
                else:
                    for name in LANDMARK_NAMES:
                        landmarks[name] = Landmark(x=0.0, y=0.0, z=0.0, visibility=0.0)

                frames.append(
                    FramePose(
                        frame_index=idx,
                        timestamp_ms=(idx / fps) * 1000.0,
                        landmarks=landmarks,
                    )
                )
                idx += 1

        cap.release()
        return frames


def write_blank_video(path: Path, frame_count: int = 30, fps: float = 30.0, size: tuple[int, int] = (640, 480)) -> None:
    """Utility for tests / demos — a solid-color clip the pipeline can open."""
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = None
    out_path = path
    for candidate, codec in (
        (path.with_suffix(".mp4"), "avc1"),
        (path.with_suffix(".mp4"), "mp4v"),
        (path.with_suffix(".avi"), "MJPG"),
    ):
        # macOS AVFoundation refuses to open a writer over an existing file.
        candidate.unlink(missing_ok=True)
        fourcc = cv2.VideoWriter_fourcc(*codec)
        w = cv2.VideoWriter(str(candidate), fourcc, fps, size)
        if w.isOpened():
            writer = w
            out_path = candidate
            break
        w.release()
    if writer is None:
        raise RuntimeError("No OpenCV VideoWriter backend available")
    for i in range(frame_count):
        img = np.zeros((size[1], size[0], 3), dtype=np.uint8)
        img[:] = (30, 90, 40)
        cv2.putText(img, f"frame {i}", (40, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        writer.write(img)
    writer.release()
    if out_path != path and out_path.exists():
        # Keep caller path stable when possible.
        if path.suffix == out_path.suffix:
            out_path.replace(path)
        else:
            path.write_bytes(out_path.read_bytes())
