from __future__ import annotations

from jinja2 import Environment, PackageLoader, select_autoescape

from .models import Player
from .parser import INTERESTING_PLAYERS, SPECIAL_MARKERS
from .utils import normalize_name


def _create_env() -> Environment:
    """Create Jinja2 environment with templates from this package."""
    env = Environment(
        loader=PackageLoader("dart_rankings", "templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )
    return env


def _row_class(player: Player) -> str:
    """Generate CSS classes for a player row."""
    classes: list[str] = []
    if player.qual_main:
        classes.append("qual-main")
    if player.qual_youth:
        classes.append("qual-youth")
    if normalize_name(player.name) in SPECIAL_MARKERS:
        classes.append("special")
    return " ".join(classes)


def _get_marker(name: str) -> str:
    """Get special marker emoji for a player name."""
    return SPECIAL_MARKERS.get(normalize_name(name), "")


def _format_eur(amount: float) -> str:
    """Format a number as EUR currency."""
    return f"\u20ac{int(round(amount)):,}"


def _format_stat_key(key: str) -> str:
    """Format an API stat key for display."""
    aliases = {
        "ppr": "PPR",
        "id": "ID",
        "org_player_id": "Org Player ID",
        "iso2_country": "Country (2)",
        "iso3_country": "Country (3)",
        "total_180s": "180s",
        "total_177s": "177s",
        "total_174s": "174s",
        "total_171s": "171s",
        "total_nine_darters": "9-Darters",
        "total_ten_darters": "10-Darters",
        "total_eleven_darters": "11-Darters",
        "total_twelve_darters": "12-Darters",
        "total_finish_161_170": "Finish 161-170",
        "total_finish_131_160": "Finish 131-160",
        "total_finish_101_130": "Finish 101-130",
    }
    if key in aliases:
        return aliases[key]
    return key.replace("_", " ").title()


def _format_stat_value(value: object) -> str:
    """Format an API stat value for display."""
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, float):
        if abs(value - round(value)) < 1e-9:
            return str(int(round(value)))
        return f"{value:.4f}".rstrip("0").rstrip(".")
    return str(value)


def _country_flag(iso2: str) -> str:
    """Convert ISO 3166-1 alpha-2 code to flag emoji. e.g. 'DE' -> '🇩🇪'"""
    if not iso2 or len(iso2) != 2:
        return ""
    return chr(0x1F1E6 + ord(iso2[0].upper()) - ord("A")) + chr(
        0x1F1E6 + ord(iso2[1].upper()) - ord("A")
    )


_BEST_ROUND_LABELS: dict[int, str] = {
    1: "Winner",
    2: "Final",
    4: "Semi-Final",
    8: "Quarter-Final",
    16: "Last 16",
    32: "Last 32",
    64: "Last 64",
    128: "Last 128",
    256: "Last 256",
    512: "Last 512",
}


def _format_best_round(value: object) -> str:
    """Format best_round number to human-readable tournament stage."""
    if value is None:
        return "-"
    return _BEST_ROUND_LABELS.get(int(value), f"R{value}")


def _format_pct(numerator: object, denominator: object) -> str:
    """Calculate and format a percentage from numerator/denominator."""
    num = float(numerator or 0)
    denom = float(denominator or 0)
    if denom == 0:
        return "-"
    return f"{num / denom * 100:.1f}"


def build_html(
    main: list[Player],
    youth: list[Player],
    main_q: list[Player],
    youth_q: list[Player],
    all_q: list[Player],
    main_url: str,
    youth_url: str,
    view: str = "main",
    mobile: bool = False,
) -> str:
    """Build HTML report using Jinja2 templates."""
    env = _create_env()
    template = env.get_template("rankings.html")

    is_youth = view == "youth"
    is_interesting = view == "interesting"

    if is_interesting:
        # Filter main players to only interesting ones
        players = [p for p in main if normalize_name(p.name) in INTERESTING_PLAYERS]
        title = "Interesting Order"
        table_id = "interesting-table"
        mobile_path = "/interesting/mobile/"
        mobile_link = "/interesting/mobile/"
        desktop_link = "/interesting/"
    elif is_youth:
        players = youth
        title = "Youth Order of Merit"
        table_id = "youth-table"
        mobile_path = "/youth/mobile/"
        mobile_link = "/youth/mobile/"
        desktop_link = "/youth/"
    else:
        players = main
        title = "Main Order of Merit"
        table_id = "main-table"
        mobile_path = "/mobile/"
        mobile_link = "/mobile/"
        desktop_link = "/"

    return template.render(
        # Page metadata
        title=title,
        table_id=table_id,
        is_youth=is_youth,
        is_interesting=is_interesting,
        mobile=mobile,
        view=view,
        # Navigation links
        mobile_path=mobile_path,
        mobile_link=mobile_link,
        desktop_link=desktop_link,
        enable_redirect=not mobile,
        # Data
        players=players,
        main_q=main_q,
        youth_q=youth_q,
        all_q=all_q,
        # Helper functions
        row_class=_row_class,
        get_marker=_get_marker,
        format_eur=_format_eur,
        format_stat_key=_format_stat_key,
        format_stat_value=_format_stat_value,
    )
