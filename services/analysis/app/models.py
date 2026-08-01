from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Stroke(str, Enum):
    SERVE = "serve"
    FOREHAND = "forehand"
    BACKHAND = "backhand"
    VOLLEY = "volley"
    OVERHEAD = "overhead"


class Handedness(str, Enum):
    RIGHT = "right"
    LEFT = "left"


class View(str, Enum):
    SIDE = "side"
    REAR = "rear"
    FRONT = "front"
    UNKNOWN = "unknown"


class PhaseName(str, Enum):
    READY = "ready"
    UNIT_TURN = "unit_turn"
    TAKEBACK = "takeback"
    RACQUET_DROP = "racquet_drop"
    ACCELERATION = "acceleration"
    CONTACT = "contact"
    EXTENSION = "extension"
    FINISH = "finish"


PHASE_ORDER: list[PhaseName] = [
    PhaseName.READY,
    PhaseName.UNIT_TURN,
    PhaseName.TAKEBACK,
    PhaseName.RACQUET_DROP,
    PhaseName.ACCELERATION,
    PhaseName.CONTACT,
    PhaseName.EXTENSION,
    PhaseName.FINISH,
]


class Landmark(BaseModel):
    x: float
    y: float
    z: float = 0.0
    visibility: float = 1.0


class FramePose(BaseModel):
    frame_index: int
    timestamp_ms: float
    landmarks: dict[str, Landmark]


class PhaseWindow(BaseModel):
    name: PhaseName
    start_frame: int
    end_frame: int
    contact_frame: int | None = None


class PhaseScore(BaseModel):
    name: PhaseName
    score: float = Field(ge=0, le=100)
    weight: float = 1.0
    feedback: str
    ideal_comparison: str
    observations: list[str] = Field(default_factory=list)


class QualityIssue(BaseModel):
    code: str
    message: str
    tip: str


class MultiHitCandidate(BaseModel):
    index: int
    score: float | None = None
    status: Literal["ok", "insufficient_quality"]
    kept: bool = False


class MultiHitInfo(BaseModel):
    enabled: bool = True
    detected: int
    kept_index: int | None = None
    kept_score: float | None = None
    kept_window_ms: list[float] = Field(default_factory=list)
    candidates: list[MultiHitCandidate] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    stroke: Stroke
    status: Literal["ok", "insufficient_quality"] = "ok"
    overall_score: float = Field(ge=0, le=100)
    grade: str
    confidence: float = Field(ge=0, le=1)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    top_fix: str = ""
    phases: list[PhaseScore] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)
    quality_issues: list[QualityIssue] = Field(default_factory=list)
    contact_estimated: bool = True
    frame_count: int = 0
    fps: float = 0.0
    multi_hit: MultiHitInfo | None = None
