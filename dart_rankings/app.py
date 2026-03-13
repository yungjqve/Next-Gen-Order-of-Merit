from __future__ import annotations

import logging
import os
import re

from collections import OrderedDict
from functools import wraps

from flask import Flask, render_template, request, jsonify, Response, abort, make_response

from .data import get_store, init_scheduler, refresh
from .fetcher import fetch_player_events
from .parser import INTERESTING_PLAYERS
from .report import (
    _row_class, _get_marker, _format_eur, _format_stat_value,
    _country_flag, _format_best_round, _format_pct,
)
from .utils import normalize_name
from . import verbande as vb

logger = logging.getLogger(__name__)


def create_app() -> Flask:
    app = Flask(__name__)

    # Register Jinja2 template helpers
    app.jinja_env.globals.update(
        row_class=_row_class,
        get_marker=_get_marker,
        format_eur=_format_eur,
        format_stat_value=_format_stat_value,
        country_flag=_country_flag,
        format_best_round=_format_best_round,
        format_pct=_format_pct,
    )

    # Load data on startup and start the daily refresh scheduler
    refresh()
    init_scheduler()

    @app.route("/")
    def main_view():
        return _render_view("main")

    @app.route("/youth/")
    def youth_view():
        return _render_view("youth")

    @app.route("/interesting/")
    def interesting_view():
        return _render_view("interesting")

    # ── SEO ──

    @app.route("/robots.txt")
    def robots_txt():
        lines = [
            "User-agent: *",
            "Allow: /",
            "Disallow: /admin",
            "Disallow: /api/",
            "",
            "Sitemap: https://next.jqve.dev/sitemap.xml",
        ]
        resp = make_response("\n".join(lines))
        resp.headers["Content-Type"] = "text/plain"
        return resp

    @app.route("/sitemap.xml")
    def sitemap_xml():
        store = get_store()
        updated = store["last_updated"].strftime("%Y-%m-%d") if store else "2026-01-01"

        urls = [
            ("https://next.jqve.dev/", "daily", "1.0"),
            ("https://next.jqve.dev/youth/", "daily", "0.9"),
            ("https://next.jqve.dev/interesting/", "daily", "0.8"),
        ]

        # Add player pages
        if store:
            seen = set()
            for p in store["main_players"] + store["youth_players"]:
                pid = p.api_stats.get("id")
                if pid and pid not in seen:
                    seen.add(pid)
                    urls.append((f"https://next.jqve.dev/player/{pid}", "weekly", "0.6"))

        xml = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
        for loc, freq, priority in urls:
            xml.append("  <url>")
            xml.append(f"    <loc>{loc}</loc>")
            xml.append(f"    <lastmod>{updated}</lastmod>")
            xml.append(f"    <changefreq>{freq}</changefreq>")
            xml.append(f"    <priority>{priority}</priority>")
            xml.append("  </url>")
        xml.append("</urlset>")

        resp = make_response("\n".join(xml))
        resp.headers["Content-Type"] = "application/xml"
        return resp

    # ── Admin (basic auth) ──

    ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
    ADMIN_PASS = os.environ.get("ADMIN_PASS", "")

    def require_admin(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            auth = request.authorization
            if not auth or auth.username != ADMIN_USER or auth.password != ADMIN_PASS:
                return Response(
                    "Unauthorized", 401,
                    {"WWW-Authenticate": 'Basic realm="Admin"'},
                )
            return f(*args, **kwargs)
        return decorated

    @app.route("/admin")
    @require_admin
    def admin_page():
        store = get_store()
        if store is None:
            return render_template("loading.html"), 503

        # Merge main + youth, deduplicate by id
        seen_ids: set[str] = set()
        all_players = []
        for p in store["main_players"] + store["youth_players"]:
            pid = str(p.api_stats.get("id", ""))
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                all_players.append(p)

        return render_template(
            "admin.html",
            players=all_players,
            verbande=vb.get_verbande_list(),
            assignments=vb.get_assignments(),
            view="admin",
            last_updated=store["last_updated"],
        )

    @app.route("/api/verbande", methods=["POST"])
    @require_admin
    def api_verbande():
        data = request.get_json(silent=True) or {}
        action = data.get("action")
        name = (data.get("name") or "").strip()

        if action == "add":
            if not name:
                return jsonify(ok=False, error="Name is required"), 400
            added = vb.add_verband(name)
            if not added:
                return jsonify(ok=False, error="Already exists"), 409
            return jsonify(ok=True, verbande=vb.get_verbande_list())

        if action == "remove":
            if not name:
                return jsonify(ok=False, error="Name is required"), 400
            removed = vb.remove_verband(name)
            if not removed:
                return jsonify(ok=False, error="Not found"), 404
            return jsonify(ok=True, verbande=vb.get_verbande_list())

        return jsonify(ok=False, error="Invalid action"), 400

    @app.route("/api/verbande/assign", methods=["POST"])
    @require_admin
    def api_assign():
        data = request.get_json(silent=True) or {}
        player_id = str(data.get("player_id", ""))
        verband = (data.get("verband") or "").strip()

        if not player_id:
            return jsonify(ok=False, error="player_id is required"), 400

        vb.assign_player(player_id, verband)
        return jsonify(ok=True)

    # ── Player profile ──

    @app.route("/player/<int:player_id>")
    def player_page(player_id: int):
        store = get_store()
        if store is None:
            return render_template("loading.html"), 503

        # Find player in cached data
        player = None
        for p in store["main_players"] + store["youth_players"]:
            if p.api_stats.get("id") == player_id:
                player = p
                break
        if player is None:
            abort(404)

        # Fetch per-tournament breakdown from API
        cookie = os.environ.get("DARTCONNECT_COOKIE", "").strip() or None
        try:
            events = fetch_player_events("pdc-next-gen-2026", player_id, cookie_header=cookie)
        except Exception:
            logger.exception("Failed to fetch player events for %d", player_id)
            events = []

        # Group events: tournament → event number → phases
        tournaments = _group_events(events)

        assignments = vb.get_assignments()
        player_verband = assignments.get(str(player_id), "")

        return render_template(
            "player.html",
            player=player,
            events=events,
            tournaments=tournaments,
            player_verband=player_verband,
            view="player",
            last_updated=store["last_updated"],
        )

    return app


def _render_view(view: str) -> str:
    store = get_store()
    if store is None:
        return render_template("loading.html"), 503

    main_players = store["main_players"]
    youth_players = store["youth_players"]

    if view == "interesting":
        players = [p for p in main_players if normalize_name(p.name) in INTERESTING_PLAYERS]
        title = "Interesting Order"
        table_id = "interesting-table"
        seo = {
            "title": "Interesting Players - Next Gen Order of Merit - PDC Europe Darts",
            "description": "Curated selection of interesting players in the PDC Europe Next Gen Order of Merit 2026. Stats, rankings, and tournament results.",
            "canonical": "https://next.jqve.dev/interesting/",
        }
    elif view == "youth":
        players = youth_players
        title = "Youth Order of Merit"
        table_id = "youth-table"
        seo = {
            "title": "Youth Order of Merit - Next Gen - PDC Europe Darts",
            "description": f"PDC Europe Next Gen Youth Order of Merit 2026. Rankings and stats for {len(youth_players)} youth dart players.",
            "canonical": "https://next.jqve.dev/youth/",
        }
    else:
        players = main_players
        title = "Main Order of Merit"
        table_id = "main-table"
        seo = {
            "title": "Next Gen Order of Merit 2026 - PDC Europe Dart Rankings",
            "description": f"Live PDC Europe Next Gen Order of Merit 2026. Full rankings, stats, and prize money for {len(main_players)} dart players.",
            "canonical": "https://next.jqve.dev/",
        }

    return render_template(
        "rankings.html",
        title=title,
        table_id=table_id,
        is_youth=(view == "youth"),
        is_interesting=(view == "interesting"),
        view=view,
        players=players,
        seo=seo,
        main_q=store["main_q"],
        youth_q=store["youth_q"],
        all_q=store["all_q"],
        last_updated=store["last_updated"],
        verbande_list=vb.get_verbande_list(),
        assignments=vb.get_assignments(),
    )


_EVENT_NUM_RE = re.compile(r"^(Event\s+\d+)")
_PHASE_SUFFIXES = ["Group Stage", "League Phase", "Knockout", "KO"]


def _parse_event_label(label: str) -> tuple[str, str, str]:
    """Parse 'Event 03 - FA Cup Knockout' → ('Event 03', 'FA Cup', 'Knockout').

    Returns (event_key, event_name, phase).
    """
    m = _EVENT_NUM_RE.match(label)
    event_key = m.group(1) if m else label
    rest = label[m.end():].lstrip(" -") if m else label

    # Try to split off phase suffix via " - " separator first
    # e.g. "League Phase - KO" → name="League Phase", phase="KO"
    phase = ""
    if " - " in rest:
        parts = rest.rsplit(" - ", 1)
        if parts[1].strip() in _PHASE_SUFFIXES:
            phase = parts[1].strip()
            rest = parts[0].strip()

    # Then try trailing suffixes like "FA Cup Knockout" → "FA Cup" + "Knockout"
    # But only if stripping wouldn't leave the name empty
    if not phase:
        for suffix in _PHASE_SUFFIXES:
            if rest.endswith(suffix):
                candidate = rest[: -len(suffix)].rstrip(" -")
                if candidate:  # don't strip if it would empty the name
                    phase = suffix
                    rest = candidate
                break

    return event_key, rest or event_key, phase


def _group_events(events: list[dict]) -> list[dict]:
    """Group flat event list into tournament → events → phases hierarchy.

    Returns: [
        {
            "name": "PDC Europe NEXT GEN 2026 - Weekend 02",
            "date": "2026-02-14",
            "events": [
                {
                    "key": "Event 03",
                    "name": "FA Cup",
                    "is_winner": True,
                    "phases": [
                        {"phase": "Group Stage", "data": {...}},
                        {"phase": "Knockout", "data": {...}},
                    ],
                    "totals": {...},
                },
            ],
        },
    ]
    """
    # Step 1: group by tournament
    tournament_map: dict[str, list[dict]] = OrderedDict()
    for ev in events:
        key = ev.get("tournament_label", "Unknown")
        tournament_map.setdefault(key, []).append(ev)

    result = []
    for t_name, t_events in tournament_map.items():
        date = t_events[0].get("tournament_start_date", "")

        # Step 2: group by event number within tournament
        event_map: dict[str, list[tuple[str, dict]]] = OrderedDict()
        for ev in t_events:
            event_key, event_name, phase = _parse_event_label(ev.get("event_label", ""))
            event_map.setdefault(event_key, []).append((event_name, phase, ev))

        grouped_events = []
        for event_key, phases_list in event_map.items():
            # Sort phases: Group Stage / League Phase first, then Knockout / KO
            phase_order = {"Group Stage": 0, "League Phase": 0, "": 1, "Knockout": 2, "KO": 2}
            phases_list.sort(key=lambda x: phase_order.get(x[1], 1))

            event_name = phases_list[0][0]
            is_winner = any(ev.get("event_winner") for _, _, ev in phases_list)

            phases = []
            for _, phase, data in phases_list:
                phases.append({"phase": phase or event_name, "data": data})

            # Compute totals across phases
            totals = _sum_phases([d for _, _, d in phases_list])

            grouped_events.append({
                "key": event_key,
                "name": event_name or event_key,
                "is_winner": is_winner,
                "best_round_label": phases_list[-1][2].get("best_round_label", ""),
                "phases": phases,
                "totals": totals,
                "single": len(phases) == 1,
            })

        # Sort events by event number descending (highest first)
        grouped_events.sort(key=lambda e: e["key"], reverse=True)
        result.append({"name": t_name, "date": date, "events": grouped_events})

    return result


def _sum_phases(phases: list[dict]) -> dict:
    """Sum numeric stats across multiple phases of the same event."""
    int_keys = [
        "match_wins", "played_matches", "leg_wins", "leg_lost", "leg_diff",
        "played_legs", "legs_withdarts", "legs_withdarts_wins",
        "legs_againstdarts", "legs_againstdarts_wins",
        "total_180s", "total_177s", "total_174s", "total_171s",
        "total_nine_darters", "total_ten_darters", "total_eleven_darters",
        "total_twelve_darters", "total_finish_101_130", "total_finish_131_160",
        "total_finish_161_170", "money", "money_extra", "money_winnings", "points",
    ]
    totals: dict = {}
    for k in int_keys:
        totals[k] = sum(int(p.get(k, 0) or 0) for p in phases)

    # Weighted average PPR by played_legs
    total_legs = totals["played_legs"]
    if total_legs > 0:
        totals["ppr"] = sum(float(p.get("ppr", 0) or 0) * int(p.get("played_legs", 0) or 0) for p in phases) / total_legs
    else:
        totals["ppr"] = 0

    # Derived percentages
    if totals["played_matches"] > 0:
        totals["match_win_percentage"] = totals["match_wins"] / totals["played_matches"] * 100
    else:
        totals["match_win_percentage"] = 0

    if total_legs > 0:
        totals["leg_win_percentage"] = totals["leg_wins"] / total_legs * 100
    else:
        totals["leg_win_percentage"] = 0

    if totals["legs_againstdarts"] > 0:
        totals["leg_againdarts_win_percentage"] = totals["legs_againstdarts_wins"] / totals["legs_againstdarts"] * 100
    else:
        totals["leg_againdarts_win_percentage"] = 0

    return totals
