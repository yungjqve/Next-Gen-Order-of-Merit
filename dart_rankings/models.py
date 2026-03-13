from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Player:
    rank: int
    name: str
    notables: Optional[int]
    total_180s: int
    total_177s: int
    total_174s: int
    total_171s: int
    total_9d: int
    total_10d: int
    total_11d: int
    total_12d: int
    finish_161_170: int
    finish_131_160: int
    finish_101_130: int
    money_raw: str
    money_num: float
    money_round_num: float
    money_bonus_num: float
    total: float
    raw_cells: list[str]
    api_stats: dict[str, object]
    qual_main: bool = False
    qual_youth: bool = False
    is_youth: bool = False
