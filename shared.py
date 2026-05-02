from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Province:
    id: int
    name: str
    owner: str
    troops: int
    industry: int
    manpower: int
    neighbors: List[int]


@dataclass
class Nation:
    name: str
    industry: int
    manpower: int
    supply: int
    research: int = 0
    techs: List[str] = field(default_factory=list)
    diplomacy: Dict[str, str] = field(default_factory=dict)
    diplomacy_stance: str = "neutral"
