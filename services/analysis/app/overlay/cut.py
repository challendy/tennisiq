"""Export a time window from a source video without overlays."""

from __future__ import annotations

from pathlib import Path

import cv2

from app.overlay.render import _open_writer


def cut_video_window(
    source_video: Path,
    output_path: Path,
    start_ms: float,
    end_ms: float,
) -> Path:
    """Copy frames whose timestamps fall in [start_ms, end_ms]."""
    if not source_video.exists():
        raise FileNotFoundError(source_video)

    reader = cv2.VideoCapture(str(source_video))
    if not reader.isOpened():
        raise ValueError(f"Cannot open video: {source_video}")

    fps = reader.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(reader.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
    height = int(reader.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
    writer, output_path = _open_writer(output_path, fps, width, height)

    idx = 0
    written = 0
    while True:
        ok, frame = reader.read()
        if not ok:
            break
        t_ms = (idx / fps) * 1000.0
        if start_ms <= t_ms <= end_ms:
            writer.write(frame)
            written += 1
        elif t_ms > end_ms:
            break
        idx += 1

    writer.release()
    reader.release()
    if written == 0 or not output_path.exists() or output_path.stat().st_size < 500:
        raise RuntimeError(f"Cut produced empty file: {output_path}")
    return output_path
