from __future__ import annotations

import json
import threading
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_DATA_FILE = _DATA_DIR / "verbande.json"
_lock = threading.Lock()


def _load() -> dict:
    if not _DATA_FILE.exists():
        return {"verbande": [], "assignments": {}}
    with open(_DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict) -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_verbande_list() -> list[str]:
    with _lock:
        return _load().get("verbande", [])


def get_assignments() -> dict[str, str]:
    with _lock:
        return _load().get("assignments", {})


def add_verband(name: str) -> bool:
    name = name.strip()
    if not name:
        return False
    with _lock:
        data = _load()
        if name in data.get("verbande", []):
            return False
        data.setdefault("verbande", []).append(name)
        data["verbande"].sort()
        _save(data)
        return True


def remove_verband(name: str) -> bool:
    with _lock:
        data = _load()
        if name not in data.get("verbande", []):
            return False
        data["verbande"].remove(name)
        data["assignments"] = {
            k: v for k, v in data.get("assignments", {}).items() if v != name
        }
        _save(data)
        return True


def assign_player(player_id: str, verband: str) -> None:
    with _lock:
        data = _load()
        pid = str(player_id)
        if verband:
            data.setdefault("assignments", {})[pid] = verband
        else:
            data.get("assignments", {}).pop(pid, None)
        _save(data)
