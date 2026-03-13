from __future__ import annotations

from .models import Player
from .utils import normalize_name, safe_int


SPECIAL_MARKERS: dict[str, str] = {
    normalize_name("Domenik Thrun"): "⭐",
    normalize_name("Maximilian Niemecek"): "⭐",
    normalize_name("Finn Mocha"): "🧑‍🦱",
    normalize_name("Felix Kuehn"): "🔥",
    normalize_name("Tom Melzak"): "🔥",
    normalize_name("Patrick Reisenegger"): "🇦🇹",
}

INTERESTING_PLAYERS: set[str] = {
    normalize_name("Maximilian Niemecek"),
    normalize_name("Domenik Thrun"),
    normalize_name("Tom Melzak"),
    normalize_name("Sebastian Hahn"),
    normalize_name("Erik Rollinger"),
    normalize_name("Finn Mocha"),
    normalize_name("Felix Kuehn"),
    normalize_name("René Steinhauer"),
}


def parse_players(payload: dict) -> list[Player]:
    players_raw = payload.get("players", [])
    players: list[Player] = []

    for i, row in enumerate(players_raw, start=1):
        first_name = str(row.get("first_name", "")).strip()
        last_name = str(row.get("last_name", "")).strip()
        full_name = f"{first_name} {last_name}".strip() or "Unknown"

        # API money values appear to be integer minor-units.
        money_num = float(row.get("money", 0) or 0) / 100.0
        money_bonus_num = float(row.get("money_extra", 0) or 0) / 100.0
        money_round_num = max(money_num - money_bonus_num, 0.0)
        notables = safe_int(str(row.get("points", "0")))
        total_9d = safe_int(str(row.get("total_nine_darters", "0"))) or 0
        total_10d = safe_int(str(row.get("total_ten_darters", "0"))) or 0
        total_11d = safe_int(str(row.get("total_eleven_darters", "0"))) or 0
        total_12d = safe_int(str(row.get("total_twelve_darters", "0"))) or 0
        finish_161_170 = safe_int(str(row.get("total_finish_161_170", "0"))) or 0
        finish_131_160 = safe_int(str(row.get("total_finish_131_160", "0"))) or 0
        finish_101_130 = safe_int(str(row.get("total_finish_101_130", "0"))) or 0
        total_180s = safe_int(str(row.get("total_180s", "0"))) or 0
        total_177s = safe_int(str(row.get("total_177s", "0"))) or 0
        total_174s = safe_int(str(row.get("total_174s", "0"))) or 0
        total_171s = safe_int(str(row.get("total_171s", "0"))) or 0
        total = money_num + float(notables or 0)

        players.append(
            Player(
                rank=i,
                name=full_name,
                notables=notables,
                total_180s=total_180s,
                total_177s=total_177s,
                total_174s=total_174s,
                total_171s=total_171s,
                total_9d=total_9d,
                total_10d=total_10d,
                total_11d=total_11d,
                total_12d=total_12d,
                finish_161_170=finish_161_170,
                finish_131_160=finish_131_160,
                finish_101_130=finish_101_130,
                money_raw=str(row.get("money", "0")),
                money_num=money_num,
                money_round_num=money_round_num,
                money_bonus_num=money_bonus_num,
                total=total,
                raw_cells=[],
                api_stats={k: v for k, v in row.items()},
            )
        )

    return players
