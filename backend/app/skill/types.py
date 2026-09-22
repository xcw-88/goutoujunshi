from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


RiskLevel = Literal["normal", "sensitive", "high"]


@dataclass(frozen=True, slots=True)
class SkillDocument:
    path: str
    title: str
    content: str


@dataclass(frozen=True, slots=True)
class RouteDecision:
    intent: str
    risk: RiskLevel
    references: tuple[str, ...]

