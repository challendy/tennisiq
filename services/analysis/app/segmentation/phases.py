from __future__ import annotations

from app.kinematics.features import FrameFeatures
from app.models import PHASE_ORDER, PhaseName, PhaseWindow


def segment_phases(features: list[FrameFeatures]) -> list[PhaseWindow]:
    """Segment a stroke into the eight coaching phases.

    Strategy (side-view, single-stroke clip):
    - Contact ≈ frame of peak hand speed in the second half of the clip
      (acceleration window), which is an *estimate* without ball tracking.
    - Remaining phases are laid out relative to contact using the hand-x
      curve (backswing extremum) and fixed proportional windows.
    """
    n = len(features)
    if n < 8:
        # Degenerate: equal slices so callers always get 8 phases.
        return _equal_slices(n)

    # Body-relative signals: direction-normalised, so a lefty or a clip shot
    # from the opposite sideline segments the same way.
    speeds = [f.hand_speed_rel for f in features]
    hand_x = [f.hand_x_rel for f in features]

    # Peak speed in the middle 60% of the clip — avoids startup noise.
    lo = max(1, int(n * 0.2))
    hi = min(n - 1, int(n * 0.85))
    contact_idx = lo + max(range(hi - lo), key=lambda i: speeds[lo + i])

    # Backswing extremum: minimum hand_x before contact.
    search_end = max(1, contact_idx - 1)
    takeback_idx = min(range(search_end), key=lambda i: hand_x[i])

    # Drop is between takeback and contact, where the hand sits lowest.
    if contact_idx - takeback_idx >= 2:
        drop_idx = takeback_idx + min(
            range(contact_idx - takeback_idx),
            key=lambda i: features[takeback_idx + i].hand_y_rel,
        )
    else:
        drop_idx = takeback_idx

    # Unit turn starts when shoulders begin rotating — approximate as 30% of
    # the way from start to takeback.
    unit_idx = max(1, int(takeback_idx * 0.45))
    ready_end = max(1, int(unit_idx * 0.6))

    accel_start = drop_idx
    extension_end = min(n - 1, contact_idx + max(2, int((n - contact_idx) * 0.45)))

    bounds = {
        PhaseName.READY: (0, ready_end),
        PhaseName.UNIT_TURN: (ready_end, unit_idx),
        PhaseName.TAKEBACK: (unit_idx, takeback_idx),
        PhaseName.RACQUET_DROP: (takeback_idx, drop_idx),
        PhaseName.ACCELERATION: (accel_start, contact_idx),
        PhaseName.CONTACT: (contact_idx, min(n - 1, contact_idx + 1)),
        PhaseName.EXTENSION: (min(n - 1, contact_idx + 1), extension_end),
        PhaseName.FINISH: (extension_end, n - 1),
    }

    # Repair any inverted / empty windows by stretching forward.
    repaired: list[PhaseWindow] = []
    cursor = 0
    for name in PHASE_ORDER:
        start, end = bounds[name]
        start = max(cursor, start)
        end = max(start, end)
        end = min(end, n - 1)
        repaired.append(
            PhaseWindow(
                name=name,
                start_frame=start,
                end_frame=end,
                contact_frame=contact_idx if name == PhaseName.CONTACT else None,
            )
        )
        cursor = end

    # Ensure last phase reaches the end.
    last = repaired[-1]
    repaired[-1] = PhaseWindow(
        name=last.name,
        start_frame=last.start_frame,
        end_frame=n - 1,
        contact_frame=last.contact_frame,
    )
    return repaired


def _equal_slices(n: int) -> list[PhaseWindow]:
    if n <= 0:
        return [
            PhaseWindow(name=name, start_frame=0, end_frame=0)
            for name in PHASE_ORDER
        ]
    windows: list[PhaseWindow] = []
    for i, name in enumerate(PHASE_ORDER):
        start = int(i * (n - 1) / 8)
        end = int((i + 1) * (n - 1) / 8)
        windows.append(PhaseWindow(name=name, start_frame=start, end_frame=max(start, end)))
    return windows
