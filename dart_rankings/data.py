from __future__ import annotations

import copy
import logging
import os
import threading
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

from .ddv_lookup import refresh_assignments
from .fetcher import fetch_ranking_payload
from .parser import parse_players
from .qualifiers import pick_qualifiers

logger = logging.getLogger(__name__)

MAIN_URL = os.environ.get(
    "MAIN_URL", "https://tv.dartconnect.com/rankings/pdc-next-gen-2026"
)
YOUTH_URL = os.environ.get(
    "YOUTH_URL", "https://tv.dartconnect.com/rankings/pdc-next-gen-youth-2026"
)
MAIN_QUAL = int(os.environ.get("MAIN_QUAL", "16"))
YOUTH_QUAL = int(os.environ.get("YOUTH_QUAL", "4"))

_lock = threading.Lock()
_store: dict | None = None
_scheduler: BackgroundScheduler | None = None


def refresh() -> bool:
    """Fetch fresh data from DartConnect API and update the in-memory cache."""
    global _store
    cookie = os.environ.get("DARTCONNECT_COOKIE", "").strip() or None

    try:
        logger.info("Refreshing rankings data...")
        main_payload = fetch_ranking_payload(MAIN_URL, cookie_header=cookie)
        youth_payload = fetch_ranking_payload(YOUTH_URL, cookie_header=cookie)

        main_players = parse_players(main_payload)
        youth_players = parse_players(youth_payload)

        if not main_players or not youth_players:
            logger.error("Empty player data received")
            return False

        main_q, youth_q, all_q = pick_qualifiers(
            main_players, youth_players, MAIN_QUAL, YOUTH_QUAL,
        )

        with _lock:
            _store = {
                "main_players": main_players,
                "youth_players": youth_players,
                "main_q": main_q,
                "youth_q": youth_q,
                "all_q": all_q,
                "last_updated": datetime.now(),
            }

        logger.info(
            "Data refreshed: %d main, %d youth players",
            len(main_players),
            len(youth_players),
        )

        # Auto-assign Verbände from DDV APIs in background (many API calls)
        all_players = main_players + youth_players
        t = threading.Thread(
            target=_run_ddv_lookup, args=(all_players,), daemon=True,
        )
        t.start()

        return True
    except Exception:
        logger.exception("Failed to refresh rankings data")
        return False


def _run_ddv_lookup(players: list) -> None:
    """Run DDV Verbände lookup in background thread."""
    try:
        refresh_assignments(players)
    except Exception:
        logger.exception("DDV Verbände lookup failed (non-fatal)")


def _weekly_ddv_rescan() -> None:
    """Re-check all unassigned players against DDV APIs (Sunday 22:00)."""
    with _lock:
        if _store is None:
            return
        players = _store["main_players"] + _store["youth_players"]
    _run_ddv_lookup(players)


def get_store() -> dict | None:
    """Return a deep copy of the cached data, or None if not yet loaded."""
    with _lock:
        if _store is None:
            return None
        return copy.deepcopy(_store)


def init_scheduler() -> None:
    """Start the APScheduler background job for daily 22:00 Europe/Berlin refresh."""
    global _scheduler
    if _scheduler is not None:
        return

    _scheduler = BackgroundScheduler(timezone="Europe/Berlin")
    _scheduler.add_job(refresh, "cron", hour=22, minute=0, id="daily_refresh")
    _scheduler.add_job(_weekly_ddv_rescan, "cron", day_of_week="sun", hour=22, minute=0, id="weekly_ddv_rescan")
    _scheduler.start()
    logger.info("Scheduler started: daily refresh at 22:00, DDV rescan Sundays 22:00 Europe/Berlin")
