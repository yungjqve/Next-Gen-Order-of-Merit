from __future__ import annotations

import re
import unicodedata
from typing import Optional


def normalize_name(name: str) -> str:
    n = unicodedata.normalize("NFKD", name)
    n = "".join(ch for ch in n if not unicodedata.combining(ch))
    n = re.sub(r"\s+", " ", n).strip().lower()
    return n


def safe_int(value: str) -> Optional[int]:
    m = re.search(r"-?\d+", value.replace(",", ""))
    if not m:
        return None
    try:
        return int(m.group(0))
    except ValueError:
        return None


def format_total(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return f"{int(round(value)):,}".replace(",", "")
    return f"{value:.2f}"
