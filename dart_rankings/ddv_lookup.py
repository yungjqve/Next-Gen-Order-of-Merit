"""Automated Verbände lookup via the DDV (3k-darts) API.

For each player, searches all known Landesverbände by last name,
then confirms the match by first name. Results are persisted via
the verbande module.
"""
from __future__ import annotations

import logging
import unicodedata
from typing import NamedTuple

import requests

from . import verbande as vb

logger = logging.getLogger(__name__)

DDV_BASE = "https://backend-ddv.3k-darts.com/2k-backend-ddv/api/v1/frontend/mandant"
DDV_TIMEOUT = 10


class VerbandConfig(NamedTuple):
    short: str        # abbreviation shown in filter
    full: str         # full name
    mandant_id: int
    season_id: int


VERBANDE: list[VerbandConfig] = [
    VerbandConfig("BWDV",  "Baden-Württembergischer Dart Verband",       576, 23),
    VerbandConfig("BDV",   "Bayerischer Dartverband",                    577, 24),
    VerbandConfig("DVB",   "Dartverband Berlin e.V.",                    579, 27),
    VerbandConfig("DVMV",  "Dartverband Mecklenburg-Vorpommern e.V.",    567, 21),
    VerbandConfig("HBDV",  "Hansestadt Bremen Dart Verband e.V.",        565, 26),
    VerbandConfig("HDV",   "Hessischer Dart Verband e.V.",               573, 14),
    VerbandConfig("LDVH",  "Landesdartverband Hamburg e.V.",              571, 17),
    VerbandConfig("NWDV",  "Nordrhein Westfälischer Dartverband e.V.",   566, 10),
    VerbandConfig("RPDV",  "Rheinland Pfälzischer Dartverband",          578, 25),
    VerbandConfig("SADV",  "Saarländischer Dartverband e.V.",            568, 15),
    VerbandConfig("STDV",  "Sachsen-Anhaltinischer Dart Verband",       1895, 19),
    VerbandConfig("SDV",   "Sächsischer Dartverband e.V.",               569, 18),
    VerbandConfig("SHDV",  "Schleswig-Holsteinischer Dartverband e.V.",  563, 16),
]


def _normalize(s: str) -> str:
    """Lowercase, strip accents, collapse whitespace for fuzzy comparison."""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower().strip()


def _search_verband(cfg: VerbandConfig, last_name: str) -> list[dict]:
    """Search a single Verband for members with the given last name."""
    url = f"{DDV_BASE}/{cfg.mandant_id}/search"
    payload = {"type": "PLAYER", "seasonId": cfg.season_id, "name": last_name}
    try:
        resp = requests.post(url, json=payload, timeout=DDV_TIMEOUT)
        if resp.status_code != 200:
            return []
        data = resp.json()
        return data.get("members", [])
    except Exception:
        logger.debug("DDV search failed for %s / %s", cfg.short, last_name, exc_info=True)
        return []


def _find_match(members: list[dict], first_name: str, last_name: str) -> bool:
    """Check if any member matches by first+last name (accent-insensitive)."""
    target_first = _normalize(first_name)
    target_last = _normalize(last_name)
    for member in members:
        player = member.get("player", {})
        m_first = _normalize(player.get("firstname", ""))
        m_last = _normalize(player.get("name", ""))
        if m_first == target_first and m_last == target_last:
            return True
    return False


def lookup_player_verband(first_name: str, last_name: str) -> str | None:
    """Search all Verbände for a player. Returns the short name or None."""
    if not last_name:
        return None
    for cfg in VERBANDE:
        members = _search_verband(cfg, last_name)
        if members and _find_match(members, first_name, last_name):
            return cfg.short
    return None


def ensure_verbande_list() -> None:
    """Make sure all known Verbände abbreviations exist in the persisted list."""
    existing = set(vb.get_verbande_list())
    for cfg in VERBANDE:
        if cfg.short not in existing:
            vb.add_verband(cfg.short)


def refresh_assignments(players: list) -> dict[str, str]:
    """Look up all players and update Verband assignments.

    Only updates players that don't have an assignment yet, to avoid
    overriding manual admin assignments and to reduce API calls.
    Returns the full assignments dict after update.
    """
    ensure_verbande_list()
    current = vb.get_assignments()
    valid_shorts = {cfg.short for cfg in VERBANDE}

    seen_ids: set[str] = set()
    to_lookup: list[tuple[str, str, str]] = []  # (player_id, first, last)

    for p in players:
        pid = str(p.api_stats.get("id", ""))
        if not pid or pid in seen_ids:
            continue
        seen_ids.add(pid)
        # Skip if already assigned
        if pid in current and current[pid] in valid_shorts:
            continue
        first = str(p.api_stats.get("first_name", "")).strip()
        last = str(p.api_stats.get("last_name", "")).strip()
        if last:
            to_lookup.append((pid, first, last))

    if not to_lookup:
        logger.info("DDV lookup: no new players to look up")
        return vb.get_assignments()

    logger.info("DDV lookup: searching %d players across %d Verbände", len(to_lookup), len(VERBANDE))
    found = 0
    for pid, first, last in to_lookup:
        result = lookup_player_verband(first, last)
        if result:
            vb.assign_player(pid, result)
            found += 1
            logger.debug("DDV lookup: %s %s -> %s", first, last, result)

    logger.info("DDV lookup: found Verband for %d / %d players", found, len(to_lookup))
    return vb.get_assignments()
